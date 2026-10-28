from match_intelligence.application.teamspotting_analysis import (
    TeamSpottingAnalysis,
    TeamSpottingSettings,
)


class Publisher:
    def __init__(self) -> None:
        self.items = []

    async def publish_many(self, observations):
        self.items.extend(observations)
        return len(observations)


def test_disabled_settings_do_not_require_a_model() -> None:
    settings = TeamSpottingSettings(None, None, None, "synthetic-videos", None)
    assert settings.configured is False


def test_predictions_become_synchronized_temporal_observations() -> None:
    predictions = (
        {
            "prediction_id": "soccernet-0001",
            "video_time_ms": 4200,
            "label": "pass",
            "team": "left",
            "confidence": 0.87,
        },
    )

    observations = TeamSpottingAnalysis._observations("match-1", predictions)

    assert len(observations) == 1
    assert observations[0].source == "soccernet"
    assert observations[0].kind == "temporal_action"
    assert observations[0].timestamp_ms == 4200
    assert observations[0].payload["match_id"] == "match-1"
    assert observations[0].payload["label"] == "pass"
    assert observations[0].payload["event_type"] == "pass"
    assert observations[0].payload["outcome"] == "unknown"
    assert observations[0].payload["evidence_status"] == "mapped_candidate"
    assert observations[0].payload["player_id"] is None
