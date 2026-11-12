"""Case events — publisher port and its RabbitMQ adapter.

Creating a case publishes its id; the worker consumes and runs the agent. The API
depends on the `CaseEventPublisher` protocol so it never imports aio-pika.
"""

from __future__ import annotations

from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection

from app.workers.retry import RETRY_TTL_MS

CASE_QUEUE = "cases.process"
RETRY_EXCHANGE = "cases.retry.ex"
RETRY_QUEUE = "cases.retry"
DEAD_QUEUE = "cases.dead"


async def declare_topology(channel: AbstractChannel) -> AbstractQueue:
    """Declare the retry/dead-letter topology and return the main queue.

    main `cases.process` --(nack)--> `cases.retry.ex` --> `cases.retry` (TTL)
      --(expire)--> back to `cases.process`.  Exhausted retries are published to
    the durable `cases.dead` holding queue by the consumer.

    Note: `cases.process` carries dead-letter arguments, so an existing queue
    declared without them must be recreated (`docker compose down` then `up`).
    """
    retry_exchange = await channel.declare_exchange(
        RETRY_EXCHANGE, aio_pika.ExchangeType.FANOUT, durable=True
    )
    retry_queue = await channel.declare_queue(
        RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_TTL_MS,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": CASE_QUEUE,
        },
    )
    await retry_queue.bind(retry_exchange)
    await channel.declare_queue(DEAD_QUEUE, durable=True)
    return await channel.declare_queue(
        CASE_QUEUE,
        durable=True,
        arguments={"x-dead-letter-exchange": RETRY_EXCHANGE},
    )


class CaseEventPublisher(Protocol):
    async def publish_case(self, case_id: str) -> None:
        """Publish a case id for asynchronous processing."""
        ...


class RabbitPublisher:
    """Publishes case ids to a durable RabbitMQ queue."""

    def __init__(self, connection: AbstractRobustConnection, channel: AbstractChannel) -> None:
        self._connection = connection
        self._channel = channel

    @classmethod
    async def connect(cls, url: str) -> RabbitPublisher:
        connection = await aio_pika.connect_robust(url)
        channel = await connection.channel()
        await declare_topology(channel)
        return cls(connection, channel)

    async def publish_case(self, case_id: str) -> None:
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=case_id.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=CASE_QUEUE,
        )

    async def close(self) -> None:
        await self._connection.close()
