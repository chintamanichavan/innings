"""The Kafka side of the stream: where the broker is, the topics, and how a message is written.

Every message is JSON, keyed by its match. Kafka keeps messages with the same key in order,
so one match's balls are never shuffled while many matches flow side by side.
"""
from __future__ import annotations

import json
import os

from confluent_kafka import (
    OFFSET_BEGINNING,
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient, NewTopic

BALLS = "balls"      # what happened on the field
SCORED = "scored"    # the same, with the score and the win chance worked out
PARTITIONS = 6       # the most scorers that can share the work
KEEP_MS = 60 * 60 * 1000   # the broker forgets messages after an hour; a match can always be replayed
LOCAL_BROKER = "127.0.0.1:19092"


def brokers() -> str:
    return os.environ.get("INNINGS_KAFKA", LOCAL_BROKER)


def encode(message: dict) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode()


def decode(payload: bytes) -> dict:
    return json.loads(payload)


def ensure_topics(*names: str) -> None:
    """Create the topics that do not exist yet."""
    admin = AdminClient({"bootstrap.servers": brokers()})
    missing = set(names) - set(admin.list_topics(timeout=10).topics)
    if not missing:
        return
    made = admin.create_topics([
        NewTopic(name, num_partitions=PARTITIONS, replication_factor=1,
                 config={"retention.ms": str(KEEP_MS)}) for name in missing])
    for waiting in made.values():
        try:
            waiting.result()
        except KafkaException as problem:
            if problem.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:   # another program got there first
                raise


def delete_topics(*names: str) -> None:
    admin = AdminClient({"bootstrap.servers": brokers()})
    for waiting in admin.delete_topics(list(names)).values():
        waiting.result()


def producer() -> Producer:
    """Sends messages. Idempotence means a retry can neither repeat a message nor reorder two."""
    return Producer({"bootstrap.servers": brokers(), "enable.idempotence": True, "linger.ms": 5,
                     "compression.type": "lz4", "queue.buffering.max.messages": 500_000})


def send(to: Producer, topic: str, message: dict) -> None:
    """Queue one message, waiting for room if the producer's buffer is full."""
    payload = encode(message)
    while True:
        try:
            to.produce(topic, payload, key=message["match_id"])
            return
        except BufferError:
            to.poll(0.5)


def send_bytes(to: Producer, topic: str, key: bytes, payload: bytes) -> None:
    """Queue one message that is already bytes, waiting for room if the buffer is full."""
    while True:
        try:
            to.produce(topic, payload, key=key)
            return
        except BufferError:
            to.poll(0.5)


def reader_of(topic: str, partitions: list[int]) -> Consumer:
    """Reads the named partitions of a topic from their start, sharing with nobody.

    A batch job knows who should read what, so it says so. No group has to form first, and
    Kafka never moves a partition to another reader half-way through.
    """
    reader = consumer(f"{topic}-{'-'.join(map(str, partitions))}", from_start=True)
    reader.assign([TopicPartition(topic, partition, OFFSET_BEGINNING) for partition in partitions])
    return reader


def consumer(group: str, from_start: bool = False) -> Consumer:
    """Reads messages as one member of `group`. Kafka shares a topic's partitions among a group."""
    return Consumer({"bootstrap.servers": brokers(), "group.id": group,
                     "auto.offset.reset": "earliest" if from_start else "latest",
                     "fetch.wait.max.ms": 20})


def ready(from_: Consumer, most: int, wait: float) -> list[Message]:
    """The messages that are ready, up to `most`. Waits up to `wait` seconds if none are.

    It never waits for a batch to fill: a lone ball goes straight through, and a flood of them
    comes out in big batches.
    """
    first = from_.poll(wait)
    if first is None:
        return []
    return [message for message in (first, *from_.consume(most - 1, 0)) if not message.error()]


def read(from_: Consumer, most: int, wait: float) -> list[dict]:
    return [decode(message.value()) for message in ready(from_, most, wait)]
