# 🩸 Blood Bank Inventory Tracker

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-4.2-black?logo=apachekafka)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue?logo=postgresql)
![PySpark](https://img.shields.io/badge/PySpark-3.5-orange?logo=apachespark)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)
![Flask](https://img.shields.io/badge/Flask-REST%20API-lightgrey?logo=flask)
![License](https://img.shields.io/badge/License-MIT-green)

A full-stack **Data Engineering** project that manages blood stock across hospitals and blood banks in real time. The system simulates donations and requests, streams events through Apache Kafka, processes and stores them in PostgreSQL, runs daily aggregations with PySpark (with a Pandas fallback), exposes a Flask REST API, and visualises everything on a live Streamlit dashboard.

---

## Problem Statement

Blood banks often face issues such as shortage of rare blood groups, expired units, delayed updates, and inefficient stock tracking. Manual record systems make it difficult to monitor availability across multiple centres.

A modern healthcare system requires a centralised and data-driven solution that can track blood inventory in real time, reduce wastage, and ensure fast availability during emergencies.

---

## Solution

The Blood Bank Inventory Tracker simulates and manages blood units across **10 hospitals** (`HOSP-001` – `HOSP-010`) and all **8 standard blood groups**. Data continuously flows through a complete Data Engineering pipeline:

```
Data Generator → Kafka Producer → Kafka Topics → Kafka Consumer → PostgreSQL → PySpark / Pandas → Daily Summary
                                                                        ↓
                                                                  Flask REST API
                                                                        ↓
                                                                 Streamlit Dashboard
```

### Key Functionalities

- Real-time blood stock monitoring per hospital and blood group
- Low stock alerts with configurable thresholds
- Donation and blood request event processing
- Shortage detection (partial fulfilment tracking)
- Daily inventory summaries via PySpark batch jobs (with automatic Pandas fallback)
- Interactive Streamlit dashboard with live PostgreSQL reads
- REST API for programmatic access to inventory and summaries

---

## Architecture

### Step 1 — Data Generation

`scripts/data_generator.py` uses **Faker** to produce synthetic blood donation and request events in JSONL format. It generates data for 10 hospitals, 8 blood groups, and supports configurable event counts via CLI flags (`--donations`, `--requests`). Output is written to the `data/` directory.

### Step 2 — Real-time Ingestion

`scripts/kafka_producer.py` publishes generated events to two Kafka topics:
- `blood_donations` — donation events (donor ID, blood group, units, hospital, timestamp)
- `blood_requests` — request events (request ID, patient ID, blood group, units, hospital, urgency, timestamp)

The producer uses `acks=all` with 5 retries for delivery guarantees.

### Step 3 — Stream Processing

`scripts/kafka_consumer.py` subscribes to both topics and processes each event in real time:
- **Donations:** Upserts inventory rows (incrementing available units) and logs a `donation` transaction.
- **Requests:** Checks available stock with `SELECT … FOR UPDATE` (row-level locking), calculates shortage/fulfilled units, decrements inventory, and logs a `request` transaction with status `fulfilled` or `partial`.

Low stock detection is built into the consumer via the `LOW_STOCK_THRESHOLD` environment variable.

### Step 4 — Batch Processing

`scripts/spark_processor.py` computes a daily summary by reading `inventory` and `transactions` tables:
- **Primary engine:** PySpark reads via JDBC, aggregates donations/requests/available/expired units per blood group, and writes to `daily_summary`.
- **Fallback engine:** If Spark is unavailable, the script automatically falls back to an equivalent Pandas aggregation using `psycopg2`.

On Windows, the script auto-detects bundled Hadoop binaries from `tools/hadoop/bin/winutils.exe`.

### Step 5 — Storage

PostgreSQL 17 stores all data across three tables:

| Table | Purpose |
|---|---|
| `inventory` | Current stock per hospital × blood group (composite PK) |
| `transactions` | Audit log of every donation / request / expiry event (UUID PK) |
| `daily_summary` | Aggregated daily stats per blood group (date × blood group PK) |

Schema is defined in `db_setup.sql` and uses `pgcrypto` for UUID generation.

### Step 6 — REST API

`backend/app.py` runs a **Flask** server exposing:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/inventory` | Full inventory (ordered by blood group, hospital) |
| `GET` | `/api/summary/latest` | Latest 8 daily summary rows |

### Step 7 — Visualisation

`scripts/dashboard.py` is a **Streamlit** application that reads directly from PostgreSQL and displays:
- KPI metrics (total units, hospitals monitored, low stock locations)
- Bar chart of blood group distribution
- Low stock alerts table (filterable by configurable threshold)
- Full live inventory table
- Manual refresh button

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Simulation | Python + Faker | Generate synthetic donors and blood requests |
| Data Ingestion | Apache Kafka 4.2 | Real-time event streaming via two topics |
| Stream Processing | kafka-python | Consume and process events in real time |
| Batch Processing | PySpark 3.5 / Pandas | Daily aggregation with automatic fallback |
| Data Storage | PostgreSQL 17 | Store inventory, transactions, and daily summaries |
| Backend API | Flask 3.x | REST API for inventory and summary data |
| Dashboard | Streamlit | Interactive real-time visualisation |
| Configuration | python-dotenv | Environment-based configuration |
| Language | Python 3.12 | Core development language |

---

## Project Structure

```
blood-bank-inventory-tracker/
├── backend/
│   ├── __init__.py
│   ├── app.py                  # Flask app factory and entry point
│   └── routes.py               # /api/health, /api/inventory, /api/summary/latest
├── scripts/
│   ├── __init__.py
│   ├── data_generator.py       # Synthetic event generation (Faker + JSONL)
│   ├── kafka_producer.py       # Publish events to Kafka topics
│   ├── kafka_consumer.py       # Consume events, upsert inventory, log transactions
│   ├── db_utils.py             # DB connection manager, upsert/insert helpers
│   ├── spark_processor.py      # PySpark daily summary (Pandas fallback)
│   └── dashboard.py            # Streamlit dashboard
├── data/
│   ├── blood_donations.jsonl   # Generated donation events
│   └── blood_requests.jsonl    # Generated request events
├── tools/
│   ├── kafka/                  # Bundled Kafka 4.2 (Scala 2.13) binaries
│   ├── postgres/               # Bundled PostgreSQL 17.4 binaries (Windows)
│   └── hadoop/
│       └── bin/                # winutils.exe for PySpark on Windows
├── db_setup.sql                # PostgreSQL schema (inventory, transactions, daily_summary)
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment variables
├── .gitignore
├── LICENSE                     # MIT License
└── Readme.md
```

---

## Database Schema

The schema is defined in [`db_setup.sql`](db_setup.sql) and creates three tables:

### `inventory`
Tracks current stock levels per hospital and blood group.

| Column | Type | Notes |
|---|---|---|
| `hospital_id` | `VARCHAR(50)` | Composite PK with `blood_group` |
| `blood_group` | `VARCHAR(5)` | Composite PK with `hospital_id` |
| `available_units` | `INTEGER` | Current available stock (≥ 0) |
| `reserved_units` | `INTEGER` | Reserved stock (≥ 0) |
| `expired_units` | `INTEGER` | Expired units count (≥ 0) |
| `low_stock_threshold` | `INTEGER` | Alert threshold (default 10) |
| `updated_at` | `TIMESTAMPTZ` | Last modification timestamp |

### `transactions`
Immutable audit log of all events.

| Column | Type | Notes |
|---|---|---|
| `transaction_id` | `UUID` | PK, auto-generated via `pgcrypto` |
| `event_type` | `VARCHAR(20)` | `donation`, `request`, or `expiry` |
| `donor_id` | `VARCHAR(50)` | Nullable (set for donations) |
| `request_id` | `VARCHAR(50)` | Nullable (set for requests) |
| `blood_group` | `VARCHAR(5)` | Blood group involved |
| `units` | `INTEGER` | Number of units (> 0) |
| `hospital_id` | `VARCHAR(50)` | Hospital identifier |
| `status` | `VARCHAR(20)` | `received`, `fulfilled`, or `partial` |
| `shortage_units` | `INTEGER` | Unfulfilled units (default 0) |
| `event_payload` | `JSONB` | Full original event payload |
| `event_timestamp` | `TIMESTAMPTZ` | When the event occurred |
| `created_at` | `TIMESTAMPTZ` | Row insertion timestamp |

### `daily_summary`
Aggregated daily statistics per blood group.

| Column | Type | Notes |
|---|---|---|
| `summary_date` | `DATE` | Composite PK with `blood_group` |
| `blood_group` | `VARCHAR(5)` | Composite PK with `summary_date` |
| `total_units_available` | `INTEGER` | Sum of available units |
| `total_units_donated` | `INTEGER` | Total donated |
| `total_units_requested` | `INTEGER` | Total requested |
| `total_units_expired` | `INTEGER` | Total expired |
| `generated_at` | `TIMESTAMPTZ` | When the summary was computed |

---

## Setup

### Prerequisites

- **Python 3.12+**
- **PostgreSQL 17** — bundled binaries are available in `tools/postgres/` for Windows, or use an existing installation
- **Apache Kafka 4.2** — bundled in `tools/kafka/` for local development
- **Java 17+** — required to run Kafka and PySpark

### 1. Clone the repository

```bash
git clone https://github.com/Ishan4705/Blood-Bank-Inventory-Tracker.git
cd Blood-Bank-Inventory-Tracker
```

### 2. Create and activate the virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # macOS / Linux
```

Edit `.env` with your PostgreSQL and Kafka connection details.

### 5. Initialise the database

Apply the schema to your PostgreSQL instance:

```bash
psql -U postgres -d blood_bank -f db_setup.sql
```

### 6. Start Kafka

```bash
# Git Bash / bash (recommended on this project)
cd tools/kafka/kafka_2.13-4.2.0
./bin/kafka-server-start.sh config/server.properties

# Windows Command Prompt / PowerShell alternative
bin\windows\kafka-server-start.bat config\server.properties
```

### 7. Run the pipeline

Run each component in a separate terminal:

```bash
# Step 1 — Generate synthetic data
python -m scripts.data_generator --donations 50 --requests 50

# Step 2 — Publish events to Kafka
python -m scripts.kafka_producer --donations 50 --requests 50

# Step 3 — Consume events and update inventory
python -m scripts.kafka_consumer

# Step 4 — Run daily aggregation (PySpark with Pandas fallback)
python -m scripts.spark_processor

# Step 5 — Start the Flask API (default: http://localhost:5000)
python -m backend.app

# Step 6 — Launch the Streamlit dashboard (default: http://localhost:8501)
streamlit run scripts/dashboard.py
```
---

## Environment Variables

All configuration is managed via `.env` (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `blood_bank` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_JDBC_DRIVER` | `org.postgresql.Driver` | JDBC driver class for PySpark |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `KAFKA_DONATION_TOPIC` | `blood_donations` | Topic for donation events |
| `KAFKA_REQUEST_TOPIC` | `blood_requests` | Topic for request events |
| `KAFKA_TOPICS` | `blood_donations,blood_requests` | Comma-separated topics for the consumer |
| `KAFKA_CONSUMER_GROUP` | `blood-bank-inventory-consumer` | Kafka consumer group ID |
| `LOW_STOCK_THRESHOLD` | `10` | Unit count that triggers low stock alerts |
| `SPARK_JARS_PACKAGES` | `org.postgresql:postgresql:42.7.4` | Maven coordinates for Spark JDBC driver |
| `FLASK_HOST` | `0.0.0.0` | Flask bind address |
| `FLASK_PORT` | `5000` | Flask port |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode (`1` / `true` / `yes`) |
| `STREAMLIT_SERVER_PORT` | `8501` | Streamlit server port |

---

## API Endpoints

| Method | Endpoint | Response |
|---|---|---|
| `GET` | `/api/health` | `{"status": "ok"}` |
| `GET` | `/api/inventory` | JSON array of all inventory rows |
| `GET` | `/api/summary/latest` | JSON array of latest 8 daily summary rows |

---

## Notes

- The Kafka consumer performs inventory upserts with `ON CONFLICT` handling and uses `SELECT … FOR UPDATE` row-level locking to prevent race conditions on blood request processing.
- Request events track both `fulfilled` and `partial` statuses along with `shortage_units` for auditability.
- The Spark job reads from PostgreSQL via JDBC and writes aggregated rows into `daily_summary` with upsert semantics. If PySpark fails (e.g. missing Java), it automatically falls back to an equivalent Pandas aggregation.
- On Windows, PySpark requires `winutils.exe` — the script auto-configures `HADOOP_HOME` from the bundled `tools/hadoop/bin/` directory.
- The Streamlit dashboard reads live inventory data directly from PostgreSQL and supports configurable low stock thresholds via a sidebar widget.
- All transaction payloads are stored as JSONB for full event traceability.

---

## License

This project is licensed under the [MIT License](LICENSE).