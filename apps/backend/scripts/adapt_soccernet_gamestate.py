"""Convierte el JSONL de SoccerNet GameState a contratos de The Prime Moment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from match_intelligence.adapters.sources.soccernet_gamestate import convert_gamestate_rows


def _rows(path: Path):
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"La línea {line_number} no es un objeto JSON")
            yield value


def _write_jsonl(path: Path, values) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for value in values:
            output.write(value.model_dump_json() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--observations-output", type=Path, required=True)
    parser.add_argument("--tracking-output", type=Path, required=True)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--period", type=int, default=1)
    parser.add_argument("--pitch-length-m", type=float, default=105.0)
    parser.add_argument("--pitch-width-m", type=float, default=68.0)
    parser.add_argument("--left-team-id")
    parser.add_argument("--right-team-id")
    args = parser.parse_args()

    team_by_side = {
        side: team_id for side, team_id in {
            "left": args.left_team_id,
            "right": args.right_team_id,
        }.items() if team_id
    }
    result = convert_gamestate_rows(
        _rows(args.input),
        match_id=args.match_id,
        fps=args.fps,
        period=args.period,
        pitch_length_m=args.pitch_length_m,
        pitch_width_m=args.pitch_width_m,
        team_by_side=team_by_side,
    )
    _write_jsonl(args.observations_output, result.observations)
    _write_jsonl(args.tracking_output, result.frames)
    print(json.dumps({
        "observations": len(result.observations),
        "tracking_frames": len(result.frames),
        "ignored_rows": result.ignored_rows,
        "rows_without_pitch_position": result.rows_without_pitch_position,
        "observations_output": str(args.observations_output),
        "tracking_output": str(args.tracking_output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
