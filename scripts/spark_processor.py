from __future__ import annotations

import argparse
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_date, lit, sum as spark_sum

try:
    from scripts.db_utils import db_connection, get_db_config
except ModuleNotFoundError:
    from db_utils import db_connection, get_db_config


load_dotenv()


def configure_windows_hadoop_home() -> None:
    if os.name != "nt":
        return

    if os.getenv("HADOOP_HOME"):
        return

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_hadoop_home = os.path.join(repo_root, "tools", "hadoop")
    winutils_path = os.path.join(bundled_hadoop_home, "bin", "winutils.exe")

    if os.path.exists(winutils_path):
        os.environ["HADOOP_HOME"] = bundled_hadoop_home
        os.environ["hadoop.home.dir"] = bundled_hadoop_home


def build_spark_session() -> SparkSession:
    configure_windows_hadoop_home()
    jdbc_package = os.getenv("SPARK_JARS_PACKAGES", "org.postgresql:postgresql:42.7.4")
    return (
        SparkSession.builder.appName("BloodBankDailySummary")
        .config("spark.jars.packages", jdbc_package)
        .getOrCreate()
    )


def jdbc_properties() -> dict:
    config = get_db_config()
    return {
        "user": config.user,
        "password": config.password,
        "driver": os.getenv("POSTGRES_JDBC_DRIVER", "org.postgresql.Driver"),
    }


def read_table(spark: SparkSession, table_name: str):
    config = get_db_config()
    return (
        spark.read.format("jdbc")
        .option("url", f"jdbc:postgresql://{config.host}:{config.port}/{config.dbname}")
        .option("dbtable", table_name)
        .options(**jdbc_properties())
        .load()
    )


def compute_daily_summary(spark: SparkSession):
    inventory = read_table(spark, "inventory")
    transactions = read_table(spark, "transactions")

    available = (
        inventory.groupBy("blood_group")
        .agg(
            spark_sum(col("available_units")).alias("total_units_available"),
            spark_sum(col("expired_units")).alias("total_units_expired"),
        )
        .withColumn("summary_date", current_date())
    )

    donations = (
        transactions.filter(col("event_type") == "donation")
        .groupBy("blood_group")
        .agg(spark_sum(col("units")).alias("total_units_donated"))
    )

    requests = (
        transactions.filter(col("event_type") == "request")
        .groupBy("blood_group")
        .agg(spark_sum(col("units")).alias("total_units_requested"))
    )

    summary = (
        available.join(donations, on="blood_group", how="left")
        .join(requests, on="blood_group", how="left")
        .fillna(0, subset=["total_units_donated", "total_units_requested"])
        .select(
            "summary_date",
            "blood_group",
            "total_units_available",
            "total_units_donated",
            "total_units_requested",
            "total_units_expired",
        )
    )

    return summary


def compute_daily_summary_pandas() -> list[dict]:
    with db_connection(dict_cursor=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT blood_group, available_units, expired_units
                FROM inventory
                """
            )
            inventory_df = pd.DataFrame(cursor.fetchall())

            cursor.execute(
                """
                SELECT event_type, blood_group, units
                FROM transactions
                """
            )
            transactions_df = pd.DataFrame(cursor.fetchall())

    if inventory_df.empty and transactions_df.empty:
        return []

    available = (
        inventory_df.groupby("blood_group", as_index=False)
        .agg(
            total_units_available=("available_units", "sum"),
            total_units_expired=("expired_units", "sum"),
        )
        if not inventory_df.empty
        else pd.DataFrame(columns=["blood_group", "total_units_available", "total_units_expired"])
    )

    donations = (
        transactions_df[transactions_df["event_type"] == "donation"]
        .groupby("blood_group", as_index=False)
        .agg(total_units_donated=("units", "sum"))
        if not transactions_df.empty
        else pd.DataFrame(columns=["blood_group", "total_units_donated"])
    )

    requests = (
        transactions_df[transactions_df["event_type"] == "request"]
        .groupby("blood_group", as_index=False)
        .agg(total_units_requested=("units", "sum"))
        if not transactions_df.empty
        else pd.DataFrame(columns=["blood_group", "total_units_requested"])
    )

    summary = available.merge(donations, on="blood_group", how="outer").merge(requests, on="blood_group", how="outer")
    summary = summary.fillna(0)
    summary["summary_date"] = str(date.today())

    return summary.to_dict(orient="records")


def write_summary_rows(rows: list[dict]) -> None:
    if not rows:
        return

    with db_connection() as connection:
        with connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO daily_summary (
                        summary_date,
                        blood_group,
                        total_units_available,
                        total_units_donated,
                        total_units_requested,
                        total_units_expired,
                        generated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (summary_date, blood_group)
                    DO UPDATE SET
                        total_units_available = EXCLUDED.total_units_available,
                        total_units_donated = EXCLUDED.total_units_donated,
                        total_units_requested = EXCLUDED.total_units_requested,
                        total_units_expired = EXCLUDED.total_units_expired,
                        generated_at = NOW();
                    """,
                    (
                        row["summary_date"],
                        row["blood_group"],
                        int(row.get("total_units_available", 0) or 0),
                        int(row.get("total_units_donated", 0) or 0),
                        int(row.get("total_units_requested", 0) or 0),
                        int(row.get("total_units_expired", 0) or 0),
                    ),
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily summary from PostgreSQL data")
    parser.add_argument("--date", default=str(date.today()), help="Target summary date")
    _ = parser.parse_args()

    spark = None
    rows: list[dict] = []
    try:
        spark = build_spark_session()
        summary_df = compute_daily_summary(spark)
        rows = [row.asDict() for row in summary_df.collect()]
    except Exception as exc:
        print(f"Spark execution failed ({exc}). Falling back to pandas aggregation.")
        rows = compute_daily_summary_pandas()
    finally:
        if spark is not None:
            spark.stop()

    write_summary_rows(rows)


if __name__ == "__main__":
    main()
