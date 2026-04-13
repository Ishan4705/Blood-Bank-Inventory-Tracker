from __future__ import annotations

from flask import Blueprint, jsonify

from scripts.db_utils import db_connection


api = Blueprint("api", __name__)


@api.get("/health")
def health() -> tuple[dict, int]:
    return {"status": "ok"}, 200


@api.get("/inventory")
def inventory() -> tuple[object, int]:
    try:
        with db_connection(dict_cursor=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT hospital_id, blood_group, available_units, reserved_units, expired_units, low_stock_threshold, updated_at
                    FROM inventory
                    ORDER BY blood_group, hospital_id;
                    """
                )
                rows = cursor.fetchall()
        return jsonify(rows), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to load inventory: {exc}"}), 500


@api.get("/summary/latest")
def latest_summary() -> tuple[object, int]:
    try:
        with db_connection(dict_cursor=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT summary_date, blood_group, total_units_available, total_units_donated,
                           total_units_requested, total_units_expired, generated_at
                    FROM daily_summary
                    ORDER BY summary_date DESC, blood_group ASC
                    LIMIT 8;
                    """
                )
                rows = cursor.fetchall()
        return jsonify(rows), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to load summary: {exc}"}), 500
