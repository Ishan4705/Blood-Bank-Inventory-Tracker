from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, RealDictCursor


load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname: str = os.getenv("POSTGRES_DB", "blood_bank")
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )


def get_db_config() -> DatabaseConfig:
    return DatabaseConfig()


@contextmanager
def db_connection(dict_cursor: bool = False) -> Iterator[psycopg2.extensions.connection]:
    config = get_db_config()
    cursor_factory = RealDictCursor if dict_cursor else None
    connection = psycopg2.connect(config.dsn, cursor_factory=cursor_factory)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def upsert_inventory(cursor, hospital_id: str, blood_group: str, delta_units: int, threshold: int = 10) -> None:
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
        VALUES (%s, %s, GREATEST(%s, 0), 0, 0, %s, NOW())
        ON CONFLICT (hospital_id, blood_group)
        DO UPDATE SET
            available_units = GREATEST(inventory.available_units + EXCLUDED.available_units, 0),
            low_stock_threshold = EXCLUDED.low_stock_threshold,
            updated_at = NOW();
        """,
        (hospital_id, blood_group, delta_units, threshold),
    )


def insert_transaction(cursor, payload: dict, event_type: str, status: str, shortage_units: int = 0) -> None:
    cursor.execute(
        """
        INSERT INTO transactions (
            event_type,
            donor_id,
            request_id,
            blood_group,
            units,
            hospital_id,
            status,
            shortage_units,
            event_payload,
            event_timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            event_type,
            payload.get("donor_id"),
            payload.get("request_id"),
            payload.get("blood_group"),
            int(payload.get("units", 0)),
            payload.get("hospital_id"),
            status,
            shortage_units,
            Json(payload),
            payload.get("timestamp"),
        ),
    )
