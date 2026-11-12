"""RabbitMQ consumer: pulls case ids and runs them through `process_case`.

One session and one agent run per message, with prefetch=1 so a crash only affects
the in-flight case. On failure the message is retried with backoff (via the
dead-letter topology) up to `MAX_ATTEMPTS`, then dead-lettered and the case marked
failed. An un-decodable (poison) message is dead-lettered on the first delivery.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from app.agent.tools.base import ToolContext
from app.agent.tools.patient_repo import FilePatientRepository
from app.agent.tools.stores import PgPolicyStore
from app.config import settings
from app.db.base import SessionFactory
from app.ingestion.embeddings import VoyageEmbedder
from app.llm.anthropic import AnthropicClient
from app.messaging.events import CASE_QUEUE, DEAD_QUEUE, declare_topology
from app.workers.processor import mark_failed, process_case, redact_error
from app.workers.retry import current_attempt, retry_decision

logger = logging.getLogger(__name__)


async def _publish_dead(channel: AbstractChannel, body: bytes) -> None:
    await channel.default_exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=DEAD_QUEUE,
    )


async def _run_case(case_id: UUID, attempt: int) -> None:
    async with SessionFactory() as session:
        ctx = ToolContext(
            patients=FilePatientRepository(),
            policy_store=PgPolicyStore(session),
            embedder=VoyageEmbedder(input_type="query"),
        )
        result = await process_case(
            case_id=case_id, session=session, llm=AnthropicClient(), ctx=ctx, attempt=attempt
        )
    if result is None:
        logger.info("case %s already terminal — skipped", case_id)
    else:
        logger.info("case %s -> %s", case_id, result.state)


async def _handle(message: AbstractIncomingMessage, channel: AbstractChannel) -> None:
    try:
        case_id = UUID(message.body.decode())
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("undecodable message — dead-lettering: %s", exc)
        await _publish_dead(channel, message.body)
        await message.ack()
        return

    attempt = current_attempt(message.headers)
    try:
        await _run_case(case_id, attempt)
    except Exception as exc:
        # Worker boundary: route the failure, don't swallow it.
        if retry_decision(attempt) == "retry":
            logger.warning("case %s attempt %d failed — retrying: %s", case_id, attempt, exc)
            await message.reject(requeue=False)  # -> retry exchange -> delayed requeue
        else:
            logger.error("case %s attempt %d failed — dead-lettering: %s", case_id, attempt, exc)
            async with SessionFactory() as session:
                await mark_failed(
                    session=session, case_id=case_id, attempt=attempt, error=redact_error(exc)
                )
            await _publish_dead(channel, message.body)
            await message.ack()
        return

    await message.ack()


async def run_worker() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    main_queue = await declare_topology(channel)

    async def on_message(message: AbstractIncomingMessage) -> None:
        await _handle(message, channel)

    await main_queue.consume(on_message)
    logger.info("worker started, consuming %s", CASE_QUEUE)
    await asyncio.Future()


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
