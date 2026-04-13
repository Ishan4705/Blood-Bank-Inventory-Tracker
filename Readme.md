# 🩸 Blood Bank Inventory Tracker

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-4.2-black?logo=apachekafka)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue?logo=postgresql)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)
![Status](https://img.shields.io/badge/Status-Complete-green)

A full-stack Data Engineering project that manages blood stock across hospitals and blood banks in real time. The system tracks donations, monitors inventory levels, detects shortages, generates alerts, and provides a live dashboard for administrators.

---

## Problem Statement

Blood banks often face issues such as shortage of rare blood groups, expired units, delayed updates, and inefficient stock tracking. Manual record systems make it difficult to monitor availability across multiple centers.

A modern healthcare system requires a centralized and data-driven solution that can track blood inventory in real time, reduce wastage, and ensure fast availability during emergencies.

---

## Solution

The Blood Bank Inventory Tracker simulates and manages blood units across multiple blood banks. Donation and usage data continuously flows through a complete Data Engineering pipeline:

**Blood Donation Data → Kafka → Processing Engine → PostgreSQL → Dashboard**

### Key Functionalities:
- Real-time blood stock monitoring
- Low stock alerts for critical blood groups
- Expiry date tracking for stored units
- Donation and request management
- Daily inventory summaries
- Interactive analytics dashboard

---

## Architecture

The project follows a complete end-to-end Data Engineering pipeline.

### Step 1 — Data Generation
A Python simulator generates blood donations, requests, and usage records for different blood groups.

### Step 2 — Real-time Ingestion
Apache Kafka receives incoming donation and request events through topics.

### Step 3 — Stream Processing
Kafka Consumer processes messages in real time, updates stock levels, and detects shortages.

### Step 4 — Batch Processing
PySpark / Pandas performs daily aggregations such as total donations, requests fulfilled, expired units, and blood group demand trends.

### Step 5 — Storage
PostgreSQL stores all donations, requests, inventory logs, and summary reports.

### Step 6 — Visualization
Streamlit dashboard displays live stock status, alerts, charts, and trends.

> **Pipeline Flow:**  
> `Data Generator` → `Apache Kafka` → `Kafka Consumer` → `PostgreSQL` → `PySpark Processor` → `Streamlit Dashboard`

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Simulation | Python + Faker | Simulate donors and blood requests |
| Data Ingestion | Apache Kafka 4.2 | Real-time event streaming |
| Data Processing | PySpark / Pandas | Data transformation and analytics |
| Data Storage | PostgreSQL 17 | Store inventory and transaction records |
| Backend API | Flask / FastAPI | CRUD APIs for blood inventory |
| Frontend | Streamlit / React | Dashboard and user interface |
| Orchestration | Python Scripts | Automate pipeline execution |
| Language | Python 3.12 | Core development language |

---

## Project Structure

```bash
blood-bank-inventory-tracker/
├── backend/
│   ├── app.py
│   └── routes.py
├── data/
├── scripts/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── data_generator.py
│   ├── db_utils.py
│   ├── kafka_consumer.py
│   ├── kafka_producer.py
│   └── spark_processor.py
├── db_setup.sql
├── .gitignore
├── requirements.txt
└── Readme.md
```

---

## Setup

1. Create and activate the virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply the PostgreSQL schema from `db_setup.sql`.

4. Start Kafka and PostgreSQL, then run the components in this order:

```bash
python scripts/data_generator.py
python scripts/kafka_producer.py
python scripts/kafka_consumer.py
python scripts/spark_processor.py
python -m backend.app
streamlit run scripts/dashboard.py
```

---

## Environment Variables

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_DONATION_TOPIC`, `KAFKA_REQUEST_TOPIC`, `KAFKA_TOPICS`
- `LOW_STOCK_THRESHOLD`, `FLASK_HOST`, `FLASK_PORT`

---

## Notes

- The Kafka consumer performs inventory upserts and logs all transactions.
- The Spark job reads from PostgreSQL and writes aggregated rows into `daily_summary`.
- The Streamlit dashboard reads live inventory data directly from PostgreSQL.