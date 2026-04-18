from __future__ import annotations

import os

import pandas as pd
import streamlit as st

try:
    from scripts.db_utils import db_connection
except ModuleNotFoundError:
    from db_utils import db_connection


st.set_page_config(page_title="Blood Bank Inventory Tracker", layout="wide")


def query_dataframe(sql: str) -> pd.DataFrame:
    with db_connection(dict_cursor=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    return pd.DataFrame(rows)


def load_inventory() -> pd.DataFrame:
    return query_dataframe(
        """
        SELECT hospital_id, blood_group, available_units, reserved_units, expired_units, low_stock_threshold, updated_at
        FROM inventory
        ORDER BY blood_group, hospital_id;
        """
    )


def load_low_stock(threshold: int) -> pd.DataFrame:
    return query_dataframe(
        f"""
        SELECT hospital_id, blood_group, available_units, low_stock_threshold, updated_at
        FROM inventory
        WHERE available_units <= {threshold}
        ORDER BY available_units ASC, blood_group ASC;
        """
    )


def render_metrics(inventory_df: pd.DataFrame) -> None:
    total_units = int(inventory_df["available_units"].sum()) if not inventory_df.empty else 0
    total_hospitals = int(inventory_df["hospital_id"].nunique()) if not inventory_df.empty else 0
    total_low_stock = int((inventory_df["available_units"] <= inventory_df["low_stock_threshold"]).sum()) if not inventory_df.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Blood Units Available", total_units)
    col2.metric("Hospitals Monitored", total_hospitals)
    col3.metric("Low Stock Locations", total_low_stock)


def render_bar_chart(inventory_df: pd.DataFrame) -> None:
    grouped = inventory_df.groupby("blood_group", as_index=True)["available_units"].sum().sort_values(ascending=False)
    st.bar_chart(grouped)


def main() -> None:
    st.title("Blood Bank Inventory Tracker")
    st.caption("Real-time inventory view backed by PostgreSQL and Kafka ingestion.")

    threshold = st.sidebar.number_input("Low stock threshold", min_value=1, value=int(os.getenv("LOW_STOCK_THRESHOLD", "10")))
    refresh = st.sidebar.button("Refresh data")

    try:
        inventory_df = load_inventory()
        low_stock_df = load_low_stock(int(threshold))
    except Exception as exc:
        st.error(f"Unable to load dashboard data: {exc}")
        return

    render_metrics(inventory_df)

    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Blood Group Distribution")
        if inventory_df.empty:
            st.info("No inventory data available yet.")
        else:
            render_bar_chart(inventory_df)

    with right:
        st.subheader("Low Stock Alerts")
        if low_stock_df.empty:
            st.success("No blood groups are below the selected threshold.")
        else:
            st.dataframe(low_stock_df, width="stretch")

    st.subheader("Live Inventory")
    st.dataframe(inventory_df, width="stretch")

    if refresh:
        st.rerun()


if __name__ == "__main__":
    main()
