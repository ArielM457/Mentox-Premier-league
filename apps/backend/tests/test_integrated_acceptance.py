import asyncio
import importlib.util
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPOSITORY_ROOT / "apps/backend/scripts/run_integrated_acceptance.py"
SPEC = importlib.util.spec_from_file_location("run_integrated_acceptance", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_local_acceptance_preserves_deduplication() -> None:
    result = asyncio.run(MODULE.verify_local_transport())

    assert result["status"] == "passed"
    assert result["published"] == result["accepted"] + 1
    assert result["duplicates"] == 1


def test_controlled_azure_failure_keeps_local_mode_available() -> None:
    result = asyncio.run(MODULE.verify_controlled_failure())

    assert result == {
        "status": "passed",
        "failure_type": "ConnectionError",
        "failure_recorded": True,
        "event_unchanged": True,
        "local_mode_after_failure": "passed",
    }


def test_real_artifacts_share_media_and_remain_candidates() -> None:
    result = MODULE.verify_model_artifacts(REPOSITORY_ROOT)
    roboflow = json.loads(
        (
            REPOSITORY_ROOT
            / "experiments/roboflow-sports/output-real/roboflow-sports-predictions.json"
        ).read_text(encoding="utf-8")
    )
    soccernet = json.loads(
        (
            REPOSITORY_ROOT
            / "experiments/soccernet-teamspotting/output-real/soccernet-predictions.json"
        ).read_text(encoding="utf-8")
    )

    assert len(result["media_sha256"]) == 64
    assert result["roboflow"]["predictions"] == len(roboflow["predictions"])
    assert result["roboflow"]["predictions"] > 0
    assert result["soccernet"]["predictions"] == len(soccernet["predictions"])
    assert result["soccernet"]["predictions"] > 0
    assert result["fusion"]["candidates"] >= 0
    assert result["fusion"]["match_events_published"] == 0
    assert result["backend_pipeline"]["artifact_integrity"] == "passed"
