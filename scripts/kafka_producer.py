from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Iterable

from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

try:
    from scripts.data_generator import generate_events
except ModuleNotFoundError:
    from data_generator import generate_events


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DONATION_TOPIC = os.getenv("KAFKA_DONATION_TOPIC", "blood_donations")
REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "blood_requests")


def build_producer() -> KafkaProducer:
    try:
        return KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
            acks="all",
            retries=5,
            linger_ms=10,
        )
    except NoBrokersAvailable as exc:
        LOGGER.error("Unable to connect to Kafka at %s: %s", KAFKA_BOOTSTRAP_SERVERS, exc)
        raise


def publish_batch(producer: KafkaProducer, topic: str, records: Iterable[dict]) -> None:
    for record in records:
        try:
            producer.send(topic, value=record)
        except KafkaError as exc:
            LOGGER.exception("Failed to send record to %s: %s", topic, exc)
    producer.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish blood bank events to Kafka")
    parser.add_argument("--donations", type=int, default=50)
    parser.add_argument("--requests", type=int, default=50)
    args = parser.parse_args()

    events = generate_events(args.donations, args.requests)

    try:
        producer = build_producer()
    except NoBrokersAvailable:
        return

    publish_batch(producer, DONATION_TOPIC, events["blood_donations"])
    publish_batch(producer, REQUEST_TOPIC, events["blood_requests"])
    producer.close()
    LOGGER.info("Published %s donation and %s request events", args.donations, args.requests)


if __name__ == "__main__":
    main()
