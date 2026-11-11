"""RabbitMQ consumer: pulls case ids and runs them through `process_case`.

One session and one agent run per message, with prefetch=1 so a crash only affects
the in-flight case. Retries and a dead-letter queue are added in the reliability
change (plan Week 5).
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.agent.tools.base import ToolContext
from app.agent.tools.patient_repo import FilePatientRepository
from app.agent.tools.stores import PgPolicyStore
from app.config import settings
from app.db.base import SessionFactory
from app.ingestion.embeddings import VoyageEmbedder
from app.llm.anthropic import AnthropicClient
from app.messaging.events import CASE_QUEUE
from app.workers.processor import process_case

logger = logging.getLogger(__name__)


async def _handle(message: AbstractIncomingMessage) -> None:
    async with message.process():
        case_id = UUID(message.body.decode())
        logger.info("processing case %s", case_id)
        async with SessionFactory() as session:
            ctx = ToolContext(
                patients=FilePatientRepository(),
                policy_store=PgPolicyStore(session),
                embedder=VoyageEmbedder(input_type="query"),
            )
            result = await process_case(
                case_id=case_id, session=session, llm=AnthropicClient(), ctx=ctx
            )
        logger.info("case %s -> %s (%s)", case_id, result.state, result.reason)


async def run_worker() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(CASE_QUEUE, durable=True)
    await queue.consume(_handle)
    logger.info("worker started, consuming %s", CASE_QUEUE)
    await asyncio.Future()


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
