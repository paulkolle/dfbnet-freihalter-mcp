from dfbnet_freihalter_mcp.config import DfbnetConfig
from dfbnet_freihalter_mcp.client import DfbnetClient
from dfbnet_freihalter_mcp.dates import date_range_payload


def make_client():
    return DfbnetClient(
        DfbnetConfig(
            referee_id="REF123",
            env_file="/tmp/no-env",
            storage_state_path="/tmp/storage.json",
            token_state_path="/tmp/token.json",
        )
    )


def test_date_range_payload_uses_single_interval_for_multiple_days_in_summer():
    payload = date_range_payload("2026-06-11", "2026-06-13")

    assert payload == {
        "from": "2026-06-10T22:00:00.000Z",
        "until": "2026-06-13T21:59:00.000Z",
        "reason": "PREVENTED",
        "comment": None,
    }


def test_date_range_payload_handles_winter_offset():
    payload = date_range_payload("2026-12-24", "2026-12-26")

    assert payload["from"] == "2026-12-23T23:00:00.000Z"
    assert payload["until"] == "2026-12-26T22:59:00.000Z"


def test_date_range_payload_rejects_end_before_start():
    try:
        date_range_payload("2026-06-13", "2026-06-11")
    except ValueError as exc:
        assert "end_date" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_dry_run_date_range_uses_single_post_url_and_payload():
    result = make_client().dry_run_date_range_exemption("2026-06-11", "2026-06-13")

    assert result["url"] == "https://api.dfbnet.org/api/referee/referee/REF123/exemption"
    assert result["payload"] == {
        "from": "2026-06-10T22:00:00.000Z",
        "until": "2026-06-13T21:59:00.000Z",
        "reason": "PREVENTED",
        "comment": None,
    }


def test_delete_exemption_url_contains_referee_and_exemption_id():
    result = make_client().dry_run_delete_exemption("EXEMPTION123")

    assert result["method"] == "POST"
    assert result["url"] == "https://api.dfbnet.org/api/referee/referee/REF123/delete-exemption"
    assert result["payload"] == {"ids": ["EXEMPTION123"]}
    assert result["exemption_id"] == "EXEMPTION123"
