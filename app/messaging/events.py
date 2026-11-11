"""Case events — publisher port and its RabbitMQ adapter.

Creating a case publishes its id; the worker consumes and runs the agent. The API
depends on the `CaseEventPublisher` protocol so it never imports aio-pika.
"""

from __future__ import annotations

from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

CASE_QUEUE = "cases.process"


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
        await channel.declare_queue(CASE_QUEUE, durable=True)
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
