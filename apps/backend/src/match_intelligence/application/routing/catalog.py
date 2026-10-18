"""Small versioned play catalogue based on observable signals."""

from __future__ import annotations

from .contracts import PlayContext, RoutingEvent


class PlayCatalog:
    version = "1"

    def match(self, events: list[RoutingEvent]) -> PlayContext:
        ordered = sorted(events, key=lambda item: (item.period, item.clock_ms, item.event_id))
        if not ordered:
            return PlayContext(score=0)

        latest = ordered[-1]
        if latest.type == "shot" and latest.start and latest.start.x >= 75:
            return PlayContext(
                pattern_key="shot_from_danger_zone",
                match_status="confirmed",
                score=1,
                signals=["shot", "start_x_at_least_75"],
                source_event_ids=[latest.event_id],
            )

        recoveries = [item for item in ordered if item.type == "recovery" and item.outcome == "success"]
        passes = [item for item in ordered if item.type == "pass" and item.outcome == "success"]
        same_team = len({item.team_id for item in [*recoveries[-1:], *passes[-2:]]}) == 1
        if recoveries and len(passes) >= 2 and same_team:
            start = recoveries[-1].start or passes[-2].start
            end = passes[-1].end
            if start and end and end.x - start.x >= 30 and end.x >= 70:
                sources = [recoveries[-1].event_id, passes[-2].event_id, passes[-1].event_id]
                return PlayContext(
                    pattern_key="recovery_and_fast_progression",
                    match_status="confirmed",
                    score=1,
                    signals=["successful_recovery", "two_successful_passes", "progression_at_least_30", "reached_attacking_zone"],
                    source_event_ids=list(dict.fromkeys(sources)),
                )

        if recoveries and passes:
            return PlayContext(
                pattern_key="recovery_and_fast_progression",
                match_status="partial",
                score=0.5,
                signals=["successful_recovery", "successful_pass"],
                missing_signals=["second_successful_pass", "progression_at_least_30", "reached_attacking_zone"],
                source_event_ids=[recoveries[-1].event_id, passes[-1].event_id],
            )

        return PlayContext(score=0, source_event_ids=[item.event_id for item in ordered])
