"""Narración provisional con plantillas para desarrollar la API sin esperar a Persona 3.

No usa modelos de lenguaje. Produce textos distintos por idioma, modo y nivel
sin cambiar los hechos. Se reemplaza por el flujo CrewAI real mediante
``NarrativePort``.
"""

import re
import unicodedata
import zlib
from collections.abc import Sequence

from match_intelligence.application.ports import VerificationOutcome, VerificationResult
from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import (
    ContentKind,
    DetailLevel,
    EditorialStatus,
    InsightCandidate,
    Language,
    MatchSnapshot,
    MetricValue,
    NarrativeDraft,
    VerificationStatus,
    ViewerMode,
    ViewerPreferences,
)


def _clock(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fact(candidate: InsightCandidate, key: str) -> float | None:
    for fact in candidate.facts:
        if fact.key == key:
            return fact.value
    return None


def _num(value: float | None) -> str:
    if value is None:
        return "?"
    return str(int(value)) if float(value).is_integer() else str(value)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


class ProvisionalNarrative:
    """Plantillas en español e inglés.

    ``inject_error_in`` permite provocar a propósito un error controlado (por
    ejemplo, nombrar a otro goleador) para demostrar el flujo de reporte y
    verificación (RF-39) durante la demo.
    """

    def __init__(self, *, inject_error_in: str | None = None) -> None:
        self._inject_error_in = inject_error_in

    # ----- nombres -----------------------------------------------------
    @staticmethod
    def _player(metadata: MatchMetadata, player_id: str | None) -> str:
        for player in metadata.players:
            if player.player_id == player_id:
                return player.name
        return player_id or "?"

    @staticmethod
    def _team(metadata: MatchMetadata, team_id: str | None) -> str:
        for team in (metadata.home_team, metadata.away_team):
            if team.team_id == team_id:
                return team.name
        return team_id or "?"

    def _wrong_teammate(self, metadata: MatchMetadata, candidate: InsightCandidate) -> str:
        for player in metadata.players:
            if player.team_id == candidate.team_id and player.player_id not in candidate.player_ids:
                return player.name
        return "?"

    # ----- narración en directo ----------------------------------------
    def live(
        self,
        metadata: MatchMetadata,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        lang = preferences.language
        team = self._team(metadata, candidate.team_id)
        main_id = candidate.player_ids[0] if candidate.player_ids else None
        player = self._player(metadata, main_id)
        if self._inject_error_in == candidate.kind:
            player = self._wrong_teammate(metadata, candidate)
        minute = _clock(candidate.clock_ms)
        es = lang is Language.ES
        analyst = preferences.mode is ViewerMode.ANALYST
        kind = candidate.kind

        if kind == "goal":
            passes = _num(_fact(candidate, "passes_in_build_up"))
            since = _fact(candidate, "seconds_since_recovery")
            headline = (
                f"¡Gol de {team}! Marca {player}" if es else f"Goal for {team}! {player} scores"
            )
            if analyst:
                headline = (
                    f"Gol de {player} ({team}) tras {passes} pases"
                    if es
                    else f"{player} ({team}) scores after {passes} passes"
                )
            why = (
                f"La jugada empezó con una recuperación y llegó al gol en {_num(since)} segundos."
                if es and since is not None
                else f"The move started with a recovery and reached goal in {_num(since)} seconds."
                if since is not None
                else ("Cambia el marcador." if es else "It changes the score.")
            )
        elif kind == "shot":
            headline = f"Remate de {player}" if es else f"Shot by {player}"
            why = (
                f"{team} genera una ocasión clara." if es else f"{team} creates a clear chance."
            )
        elif kind == "recovery":
            headline = (
                f"{player} recupera el balón para {team}"
                if es
                else f"{player} wins the ball back for {team}"
            )
            why = (
                "Una recuperación en campo rival abre la puerta a una transición rápida."
                if es
                else "Winning it back high up the pitch opens a fast transition."
            )
        elif kind == "turnover":
            headline = f"{player} roba el balón" if es else f"{player} wins the tackle"
            why = (
                f"{team} corta la circulación del rival y cambia la posesión."
                if es
                else f"{team} breaks the opponent's build-up and changes possession."
            )
        elif kind == "progressive_pass":
            gain = _num(_fact(candidate, "forward_progress"))
            headline = (
                f"Pase vertical de {player}" if es else f"Forward pass by {player}"
            )
            why = (
                f"{team} avanza {gain} unidades de campo con un solo pase."
                if es
                else f"{team} moves {gain} pitch units forward with a single pass."
            )
        elif kind == "pressure":
            headline = f"{team} presiona arriba" if es else f"{team} press high"
            why = (
                f"{player} obliga al rival a jugar con prisa."
                if es
                else f"{player} forces the opponent to rush."
            )
        else:
            headline = kind
            why = ""

        explanation = self._by_level(preferences, candidate, why, minute)
        return NarrativeDraft(
            draft_id=f"draft-{candidate.candidate_id}-{lang.value}-{preferences.mode.value}-{preferences.level.value}",
            candidate_id=candidate.candidate_id,
            match_id=metadata.match_id,
            language=lang,
            mode=preferences.mode,
            level=preferences.level,
            content_kind=ContentKind.LIVE,
            headline=headline,
            explanation=explanation,
            applied_preferences=self._applied(preferences, candidate),
            source_event_ids=candidate.source_event_ids,
            verification_status=VerificationStatus.APPROVED,
            editorial_status=None,
        )

    def _by_level(
        self,
        preferences: ViewerPreferences,
        candidate: InsightCandidate,
        why: str,
        minute: str,
    ) -> str:
        es = preferences.language is Language.ES
        level = preferences.level
        if preferences.mode is ViewerMode.ANALYST and level is DetailLevel.SIMPLE:
            level = DetailLevel.NORMAL
        if level is DetailLevel.SIMPLE:
            return why.split(".")[0] + "." if why else ""
        text = f"[{minute}] {why}"
        if level is DetailLevel.ADVANCED or preferences.mode is ViewerMode.ANALYST:
            facts = ", ".join(
                f"{f.key}={_num(f.value)}{'' if f.unit == 'count' else ' ' + f.unit}"
                for f in candidate.facts
            )
            label = "Datos" if es else "Data"
            text += f" {label}: {facts}. "
            text += ("Eventos: " if es else "Events: ") + ", ".join(candidate.source_event_ids) + "."
            if candidate.evidence_limits:
                text += (" Límite: " if es else " Limit: ") + "; ".join(candidate.evidence_limits) + "."
        return text.strip()

    @staticmethod
    def _applied(preferences: ViewerPreferences, candidate: InsightCandidate) -> list[str]:
        applied = [f"language:{preferences.language.value}", f"mode:{preferences.mode.value}", f"level:{preferences.level.value}"]
        if preferences.favorite_team_id and candidate.team_id == preferences.favorite_team_id:
            applied.append(f"favorite_team:{preferences.favorite_team_id}")
        if preferences.favorite_player_id and preferences.favorite_player_id in candidate.player_ids:
            applied.append(f"favorite_player:{preferences.favorite_player_id}")
        return applied

    # ----- modo jugador --------------------------------------------------
    def player_quiet(
        self,
        metadata: MatchMetadata,
        player_id: str,
        *,
        since_clock_ms: int,
        until_clock_ms: int,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        es = preferences.language is Language.ES
        name = self._player(metadata, player_id)
        seconds = (until_clock_ms - since_clock_ms) // 1000
        return NarrativeDraft(
            draft_id=f"draft-quiet-{player_id}-{until_clock_ms}-{preferences.language.value}",
            candidate_id=None,
            match_id=metadata.match_id,
            language=preferences.language,
            mode=preferences.mode,
            level=preferences.level,
            content_kind=ContentKind.LIVE,
            headline=f"Sin novedades de {name}" if es else f"No news on {name}",
            explanation=(
                f"{name} no ha intervenido en los últimos {seconds} segundos."
                if es
                else f"{name} has not been involved in the last {seconds} seconds."
            ),
            applied_preferences=[f"favorite_player:{player_id}", "mode:player"],
            source_event_ids=[],
            verification_status=VerificationStatus.APPROVED,
        )

    # ----- preguntas -------------------------------------------------------
    def answer(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        snapshot: MatchSnapshot,
        question: str,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        es = preferences.language is Language.ES
        q = _normalize(question)
        words = set(re.findall(r"\w+", q))
        seen = [e for e in events if (e.video_time_ms or e.clock_ms) <= snapshot.video_time_ms]

        player = next(
            (
                p for p in metadata.players
                if _normalize(p.name) in q or _normalize(p.name.split()[-1]) in words
            ),
            None,
        )
        team = next(
            (
                t for t in (metadata.home_team, metadata.away_team)
                if _normalize(t.name) in q or _normalize(t.name.split()[0]) in words
            ),
            None,
        )

        metric = None
        for keys, name in (
            (("gol", "goal", "marcador", "score", "resultado"), EventType.SHOT),
            (("tiro", "remate", "shot", "disparo"), EventType.SHOT),
            (("pase", "pass"), EventType.PASS),
            (("recuper", "recover"), EventType.RECOVERY),
            (("presion", "press"), EventType.PRESSURE),
            (("entrada", "tackle", "robo"), EventType.TACKLE),
        ):
            if any(k in q for k in keys):
                metric = (keys[0], name)
                break

        def draft(headline: str, explanation: str, sources: list[str]) -> NarrativeDraft:
            return NarrativeDraft(
                draft_id=f"answer-{zlib.crc32(f'{question}|{snapshot.video_time_ms}'.encode()):08x}",
                candidate_id=None,
                match_id=metadata.match_id,
                language=preferences.language,
                mode=preferences.mode,
                level=preferences.level,
                content_kind=ContentKind.ANSWER,
                headline=headline,
                explanation=explanation,
                applied_preferences=[f"language:{preferences.language.value}"],
                source_event_ids=sources,
                verification_status=VerificationStatus.APPROVED,
            )

        if metric is None and any(k in q for k in ("posesion", "possession")):
            team_name = self._team(metadata, snapshot.possession_team_id)
            return draft(
                (f"Ahora tiene el balón {team_name}" if es else f"{team_name} has the ball now"),
                (
                    "Los eventos sintéticos no traen duración de posesión, así que no puedo dar un porcentaje."
                    if es
                    else "The synthetic events carry no possession duration, so I cannot give a percentage."
                ),
                snapshot.recent_event_ids[-1:],
            )

        if metric is None:
            return draft(
                "No puedo responder con los datos disponibles" if es else "I cannot answer with the available data",
                (
                    "Puedo responder sobre goles, tiros, pases, recuperaciones, presiones, entradas y posesión, por equipo, jugador o tramo."
                    if es
                    else "I can answer about goals, shots, passes, recoveries, pressures, tackles and possession, by team, player or period."
                ),
                [],
            )

        key, event_type = metric
        is_goal = key == "gol"

        def matches(e: MatchEvent) -> bool:
            if e.type is not event_type:
                return False
            if is_goal and e.outcome is not EventOutcome.GOAL:
                return False
            if player and e.player_id != player.player_id:
                return False
            if team and e.team_id != team.team_id:
                return False
            return True

        label_es = {"gol": "goles", "tiro": "tiros", "pase": "pases", "recuper": "recuperaciones", "presion": "presiones", "entrada": "entradas ganadas"}[key]
        label_en = {"gol": "goals", "tiro": "shots", "pase": "passes", "recuper": "recoveries", "presion": "pressures", "entrada": "tackles won"}[key]
        label = label_es if es else label_en

        if any(k in q for k in ("tramo", "mitad", "half", "compar", "periodo", "period")) and seen:
            middle = seen[0].clock_ms + (seen[-1].clock_ms - seen[0].clock_ms) // 2
            first = [e for e in seen if matches(e) and e.clock_ms <= middle]
            second = [e for e in seen if matches(e) and e.clock_ms > middle]
            subject = (player.name if player else team.name if team else ("ambos equipos" if es else "both teams"))
            return draft(
                (f"{subject}: {len(first)} {label} en el primer tramo y {len(second)} en el segundo"
                 if es else f"{subject}: {len(first)} {label} in the first stretch and {len(second)} in the second"),
                (f"Tramos divididos en el reloj {_clock(middle)} del tiempo jugado hasta ahora."
                 if es else f"Stretches split at {_clock(middle)} of the time played so far."),
                [e.event_id for e in first + second],
            )

        found = [e for e in seen if matches(e)]
        if player:
            subject = player.name
        elif team:
            subject = team.name
        else:
            parts = []
            for t in (metadata.home_team, metadata.away_team):
                count = sum(1 for e in found if e.team_id == t.team_id)
                parts.append(f"{t.name} {count}")
            return draft(
                (f"{label.capitalize()}: " if es else f"{label.capitalize()}: ") + ", ".join(parts),
                (f"Contados hasta el minuto {_clock(snapshot.clock_ms)}." if es else f"Counted up to {_clock(snapshot.clock_ms)}."),
                [e.event_id for e in found],
            )

        extra = ""
        if event_type is EventType.PASS and found:
            ok = sum(1 for e in found if e.outcome is EventOutcome.SUCCESS)
            extra = (f" {ok} completados." if es else f" {ok} completed.")
        explanation = (
            f"Contados hasta el minuto {_clock(snapshot.clock_ms)}.{extra}"
            if es
            else f"Counted up to {_clock(snapshot.clock_ms)}.{extra}"
        )
        if not found and player:
            explanation += (
                f" {player.name} todavía no registra esta acción."
                if es
                else f" {player.name} has not recorded this action yet."
            )
        return draft(f"{subject}: {len(found)} {label}", explanation, [e.event_id for e in found])

    # ----- resumen -------------------------------------------------------
    def summary(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidates: Sequence[InsightCandidate],
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        es = preferences.language is Language.ES
        home, away = metadata.home_team, metadata.away_team
        score = f"{home.name} {snapshot.score.get(home.team_id, 0)} - {snapshot.score.get(away.team_id, 0)} {away.name}"

        def metric(key: str, team_id: str) -> MetricValue | None:
            return next((m for m in snapshot.metrics if m.key == key and m.team_id == team_id), None)

        lines: list[str] = []
        sources: set[str] = set()
        for team in (home, away):
            shots = metric("shots", team.team_id)
            accuracy = metric("pass_accuracy", team.team_id)
            acc = f"{_num(accuracy.value)}%" if accuracy and accuracy.available else ("sin datos" if es else "no data")
            lines.append(
                f"{team.name}: {_num(shots.value if shots else None)} {'tiros' if es else 'shots'}, "
                f"{'precisión de pase' if es else 'pass accuracy'} {acc}."
            )
            for m in (shots, accuracy):
                if m:
                    sources.update(m.source_event_ids)

        key_moments = sorted(candidates, key=lambda c: (-c.priority, c.clock_ms))[:3]
        key_moments.sort(key=lambda c: c.clock_ms)
        moments = []
        for c in key_moments:
            live = self.live(metadata, c, preferences.model_copy(update={"level": DetailLevel.SIMPLE, "mode": ViewerMode.CASUAL}))
            moments.append(f"{_clock(c.clock_ms)} {live.headline}")
            sources.update(c.source_event_ids)

        focus = ""
        applied = [f"language:{preferences.language.value}", f"mode:{preferences.mode.value}"]
        if preferences.favorite_player_id:
            name = self._player(metadata, preferences.favorite_player_id)
            involved = [c for c in candidates if preferences.favorite_player_id in c.player_ids]
            applied.append(f"favorite_player:{preferences.favorite_player_id}")
            if involved:
                kinds = ", ".join(sorted({c.kind for c in involved}))
                focus = (
                    f" Enfoque en {name}: participó en {len(involved)} momentos destacados ({kinds})."
                    if es else f" Focus on {name}: involved in {len(involved)} key moments ({kinds})."
                )
            else:
                focus = (
                    f" Enfoque en {name}: no participó en los momentos destacados."
                    if es else f" Focus on {name}: not involved in the key moments."
                )
        elif preferences.favorite_team_id:
            team_name = self._team(metadata, preferences.favorite_team_id)
            mine = [c for c in candidates if c.team_id == preferences.favorite_team_id]
            applied.append(f"favorite_team:{preferences.favorite_team_id}")
            focus = (
                f" Enfoque en {team_name}: {len(mine)} momentos destacados propios."
                if es else f" Focus on {team_name}: {len(mine)} key moments of their own."
            )

        title = ("Resumen: " if es else "Summary: ") + score
        body = " ".join(lines)
        body += (" Momentos: " if es else " Moments: ") + "; ".join(moments) + "." + focus
        suffix = "-".join(
            filter(None, [preferences.language.value, preferences.mode.value, preferences.favorite_team_id, preferences.favorite_player_id])
        )
        return NarrativeDraft(
            draft_id=f"summary-{metadata.match_id}-{suffix}",
            candidate_id=None,
            match_id=metadata.match_id,
            language=preferences.language,
            mode=preferences.mode,
            level=preferences.level,
            content_kind=ContentKind.FINAL,
            headline=title,
            explanation=body.strip(),
            applied_preferences=applied,
            source_event_ids=sorted(sources),
            verification_status=VerificationStatus.APPROVED,
            editorial_status=EditorialStatus.PENDING,
        )

    # ----- verificación ------------------------------------------------------
    def verify(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        draft: NarrativeDraft,
    ) -> VerificationResult:
        by_id = {e.event_id: e for e in events}
        issues: list[str] = []
        missing = [eid for eid in draft.source_event_ids if eid not in by_id]
        if missing:
            issues.append(f"Eventos de origen inexistentes: {', '.join(missing)}")

        source_players = {by_id[eid].player_id for eid in draft.source_event_ids if eid in by_id}
        text = f"{draft.headline} {draft.explanation}"
        if draft.content_kind is not ContentKind.FINAL:
            for player in metadata.players:
                if re.search(rf"\b{re.escape(player.name)}\b", text) and player.player_id not in source_players:
                    if draft.applied_preferences and f"favorite_player:{player.player_id}" in draft.applied_preferences:
                        continue
                    issues.append(
                        f"{player.name} no aparece en los eventos de origen {', '.join(draft.source_event_ids)}"
                    )

        if issues:
            return VerificationResult(VerificationOutcome.WITHDRAWN, issues)
        return VerificationResult(VerificationOutcome.CONFIRMED, [])
