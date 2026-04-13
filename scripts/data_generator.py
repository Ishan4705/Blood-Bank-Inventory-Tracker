from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from faker import Faker


FAKER = Faker()
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
HOSPITAL_IDS = [f"HOSP-{index:03d}" for index in range(1, 11)]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_donation_event() -> dict:
    return {
        "donor_id": f"DON-{FAKER.unique.random_int(min=100000, max=999999)}",
        "blood_group": random.choice(BLOOD_GROUPS),
        "units": random.randint(1, 4),
        "hospital_id": random.choice(HOSPITAL_IDS),
        "timestamp": utc_now_iso(),
    }


def generate_request_event() -> dict:
    return {
        "request_id": f"REQ-{FAKER.unique.random_int(min=100000, max=999999)}",
        "patient_id": f"PAT-{FAKER.unique.random_int(min=100000, max=999999)}",
        "blood_group": random.choice(BLOOD_GROUPS),
        "units": random.randint(1, 5),
        "hospital_id": random.choice(HOSPITAL_IDS),
        "urgency": random.choice(["routine", "urgent", "critical"]),
        "timestamp": utc_now_iso(),
    }


def generate_events(donation_count: int, request_count: int) -> dict[str, List[dict]]:
    donations = [generate_donation_event() for _ in range(donation_count)]
    requests = [generate_request_event() for _ in range(request_count)]
    return {"blood_donations": donations, "blood_requests": requests}


def write_jsonl(records: Iterable[dict], file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic blood bank events")
    parser.add_argument("--donations", type=int, default=50, help="Number of donation events")
    parser.add_argument("--requests", type=int, default=50, help="Number of request events")
    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Output directory")
    args = parser.parse_args()

    Faker.seed(42)
    random.seed(42)

    events = generate_events(args.donations, args.requests)
    write_jsonl(events["blood_donations"], args.output_dir / "blood_donations.jsonl")
    write_jsonl(events["blood_requests"], args.output_dir / "blood_requests.jsonl")
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir.resolve())}, indent=2))


if __name__ == "__main__":
    main()
