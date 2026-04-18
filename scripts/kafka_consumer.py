from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable

try:
    from scripts.db_utils import db_connection, insert_transaction, upsert_inventory
except ModuleNotFoundError:
    from db_utils import db_connection, insert_transaction, upsert_inventory


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DONATION_TOPIC = os.getenv("KAFKA_DONATION_TOPIC", "blood_donations")
KAFKA_TOPICS = [t.strip() for t in os.getenv("KAFKA_TOPICS", "blood_donations,blood_requests").split(",")]
LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", "10"))


def build_consumer() -> KafkaConsumer:
    try:
        return KafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=os.getenv("KAFKA_CONSUMER_GROUP", "blood-bank-inventory-consumer"),
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
    except NoBrokersAvailable as exc:
        LOGGER.error("Unable to connect to Kafka at %s: %s", KAFKA_BOOTSTRAP_SERVERS, exc)
        raise


def process_event(event: dict, cursor, topic_name: str) -> None:
    blood_group = event["blood_group"]
    hospital_id = event["hospital_id"]
    units = int(event.get("units", 0))

    if topic_name == DONATION_TOPIC:
        upsert_inventory(cursor, hospital_id, blood_group, units, LOW_STOCK_THRESHOLD)
        insert_transaction(cursor, event, "donation", "received")
        return

    cursor.execute(
        """
        SELECT available_units
        FROM inventory
        WHERE hospital_id = %s AND blood_group = %s
        FOR UPDATE
        """,
        (hospital_id, blood_group),
    )
    row = cursor.fetchone()
    available_units = int(row[0]) if row else 0
    shortage_units = max(units - available_units, 0)
    fulfilled_units = min(units, available_units)
    status = "fulfilled" if shortage_units == 0 else "partial"

    if row:
        cursor.execute(
            """
            UPDATE inventory
            SET available_units = GREATEST(available_units - %s, 0),
                updated_at = NOW()
            WHERE hospital_id = %s AND blood_group = %s
            """,
            (units, hospital_id, blood_group),
        )
    else:
        cursor.execute(
            """
            INSERT INTO inventory (
                hospital_id,
                blood_group,
                available_units,
                reserved_units,
                expired_units,
                low_stock_threshold,
                updated_at
            )
            VALUES (%s, %s, 0, 0, 0, %s, NOW())
            ON CONFLICT (hospital_id, blood_group)
            DO NOTHING
            """,
            (hospital_id, blood_group, LOW_STOCK_THRESHOLD),
        )

    transaction_payload = dict(event)
    transaction_payload["fulfilled_units"] = fulfilled_units
    insert_transaction(cursor, transaction_payload, "request", status, shortage_units)


def main() -> None:
    try:
        consumer = build_consumer()
    except NoBrokersAvailable:
        return

    LOGGER.info("Listening for events on topics: %s", ", ".join(KAFKA_TOPICS))
    while True:
        try:
            for message in consumer:
                event = message.value
                with db_connection() as connection:
                    with connection.cursor() as cursor:
                        process_event(event, cursor, message.topic)
        except KafkaError as exc:
            LOGGER.exception("Kafka consumer error: %s", exc)
        except Exception as exc:
            LOGGER.exception("Database processing error: %s", exc)


if __name__ == "__main__":
    main()
