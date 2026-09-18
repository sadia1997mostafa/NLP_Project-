"""Opt-in live integration check using local Prothom models and manual queries."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.server import create_app
from src.models.inference import model_cache_info
from src.pipeline.service import model_ready


QUERIES = (
    ("NID", "How can I correct my NID card?"),
    ("BIRTH_REGISTRATION", "How do I apply for birth registration?"),
    ("PASSPORT", "How do I apply for an e-passport?"),
    ("TAX", "How can I file my tax return online?"),
    ("POLICE_GD", "How do I file an online GD?"),
    ("DRIVING_LICENCE", "How do I get a driving licence?"),
)


def main() -> None:
    if not model_ready():
        raise SystemExit("Missing models/final artifacts")
    with TestClient(create_app()) as client:
        for expected_service, query in QUERIES:
            response = client.post("/api/analyze", json={"text": query})
            response.raise_for_status()
            result = response.json()
            understanding = result["understanding"]
            retrieval = result["retrieval"]
            assert understanding["service"] == expected_service, expected_service
            assert retrieval["status"] == "found", expected_service
            assert retrieval["record"] is None, expected_service
            assert result["response"]["state"] == "clarification", expected_service
            print(f"{expected_service}: {retrieval['match_level']}")

        for query, expected_topic in (
            ("NID date of birth correction documents ki lagbe?", "NID_CORRECTION_DOB"),
            ("birth registration verify korbo kivabe?", "BR_VERIFICATION_RECORD"),
        ):
            response = client.post("/api/analyze", json={"text": query})
            response.raise_for_status()
            result = response.json()
            assert result["understanding"]["query_topic_id"] == expected_topic
            assert result["retrieval"]["match_level"] == "query_topic"
            assert result["response"]["state"] == "clarification"
            assert result["retrieval"]["record"] is None
            chosen = client.post("/api/guidance", json={
                "service": result["understanding"]["service"],
                "parent_topic_id": result["understanding"]["parent_topic_id"],
                "query_topic_id": expected_topic,
            })
            chosen.raise_for_status()
            selected = chosen.json()
            assert selected["response"]["state"] == "answer"
            assert selected["response"]["source"]["url"] == selected["retrieval"]["record"]["source_url"]
            print(f"Expanded corpus user-confirmed route: {expected_topic}")

        for query, expected_topic in (
            ("passport status check korbo kivabe?", "PASSPORT_APPLICATION_STATUS"),
            ("driving licence learner documents ki lagbe?", "DRIVING_LICENCE_LEARNER_DOCUMENTS"),
        ):
            response = client.post("/api/analyze", json={"text": query})
            response.raise_for_status()
            result = response.json()
            assert result["response"]["state"] == "clarification"
            assert result["response"]["source"] is None
            print(f"Expected {expected_topic}; model chose {result['understanding']['query_topic_id']}")

        sensitive = client.post(
            "/api/analyze", json={"text": "My NID 1234567890 is lost. What should I do?"}
        )
        sensitive.raise_for_status()
        assert sensitive.json()["privacy_present"]
        assert "1234567890" not in sensitive.text
        print("Privacy masking: passed")

        unrelated = client.post("/api/analyze", json={"text": "What is the weather on Mars?"})
        unrelated.raise_for_status()
        assert unrelated.json()["response"]["state"] == "clarification"
        assert unrelated.json()["response"]["source"] is None
        print("Unrelated query clarification: passed")

        query = "general diary file korar steps ki?"
        start = time.perf_counter()
        first = client.post("/api/analyze", json={"text": query})
        first_seconds = time.perf_counter() - start
        before = model_cache_info()["hits"]
        start = time.perf_counter()
        second = client.post("/api/analyze", json={"text": query})
        second_seconds = time.perf_counter() - start
        assert first.status_code == second.status_code == 200
        assert model_cache_info()["hits"] > before
        print(f"Repeated inference: {first_seconds:.2f}s then {second_seconds:.2f}s; cache reused")


if __name__ == "__main__":
    main()
