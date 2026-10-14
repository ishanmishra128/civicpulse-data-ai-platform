import json
from datetime import datetime, timezone

import pytest

from ingestion import incremental_extract, load_to_postgres


# Timestamp parsing tests

def test_parse_timestamp_with_utc_z():
    result = load_to_postgres.parse_timestamp("2026-10-13T12:30:00Z")
    assert result == datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc)


def test_parse_timestamp_with_timezone_offset():
    result = load_to_postgres.parse_timestamp("2026-10-13T12:30:00+00:00")
    assert result == datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc)


def test_parse_timestamp_returns_none_for_missing_value():
    assert load_to_postgres.parse_timestamp(None) is None
    assert load_to_postgres.parse_timestamp("") is None


def test_parse_timestamp_rejects_invalid_value():
    with pytest.raises(ValueError):
        load_to_postgres.parse_timestamp("not-a-timestamp")


# API extraction tests

class FakeResponse:
    def __init__(self, records):
        self.records = records

    def raise_for_status(self):
        pass

    def json(self):
        return self.records


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({
            "url": url,
            "params": params,
            "timeout": timeout,
        })
        return FakeResponse(next(self.responses))


def test_extractor_paginates_and_writes_records(monkeypatch, tmp_path):
    first_page = [
        {"unique_key": "100", "created_date": "2026-10-13T10:00:00Z"},
        {"unique_key": "101", "created_date": "2026-10-13T11:00:00Z"},
    ]
    second_page = [
        {"unique_key": "102", "created_date": "2026-10-13T12:00:00Z"}
    ]

    fake_session = FakeSession([first_page, second_page])
    output_file = tmp_path / "incremental.jsonl"

    monkeypatch.setattr(incremental_extract, "create_session", lambda: fake_session)
    monkeypatch.setattr(incremental_extract, "OUTPUT_FILE", output_file)
    monkeypatch.setattr(incremental_extract, "PAGE_SIZE", 2)
    monkeypatch.setattr(incremental_extract.time, "sleep", lambda _: None)

    incremental_extract.main()

    records = [
        json.loads(line)
        for line in output_file.read_text(encoding="utf-8").splitlines()
    ]

    assert len(records) == 3
    assert [record["unique_key"] for record in records] == ["100", "101", "102"]
    assert len(fake_session.calls) == 2
    assert fake_session.calls[0]["params"]["$offset"] == 0
    assert fake_session.calls[1]["params"]["$offset"] == 2
    assert "created_date >=" in fake_session.calls[0]["params"]["$where"]
    assert "closed_date >=" in fake_session.calls[0]["params"]["$where"]


def test_extractor_rejects_non_list_api_response(monkeypatch, tmp_path):
    fake_session = FakeSession([{"unexpected": "object"}])

    monkeypatch.setattr(incremental_extract, "create_session", lambda: fake_session)
    monkeypatch.setattr(
        incremental_extract, "OUTPUT_FILE", tmp_path / "incremental.jsonl"
    )

    with pytest.raises(ValueError, match="JSON array"):
        incremental_extract.main()


def test_extractor_rejects_record_missing_required_fields(monkeypatch, tmp_path):
    fake_session = FakeSession([[{"created_date": "2026-10-13T10:00:00Z"}]])

    monkeypatch.setattr(incremental_extract, "create_session", lambda: fake_session)
    monkeypatch.setattr(
        incremental_extract, "OUTPUT_FILE", tmp_path / "incremental.jsonl"
    )

    with pytest.raises(ValueError, match="missing required fields"):
        incremental_extract.main()
