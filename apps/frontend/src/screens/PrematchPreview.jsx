import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'
import { navigate, paths } from '../app/router.js'
import { usePreferences } from '../app/preferences.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { TeamBadge } from '../components/ui/TeamBadge.jsx'
import { TacticalSimulationPitch } from '../components/match/TacticalSimulationPitch.jsx'

function FormationPicker({ team, selectedId, onSelect, copy }) {
  return (
    <section className="preview-team-options">
      <header>
        <TeamBadge team={{ team_id: team.team_id, name: team.team_name }} />
        <div>
          <span>{team.role}</span>
          <h3>{team.team_name}</h3>
        </div>
      </header>
      <p>{copy.usualFormations}</p>
      <div className="formation-options">
        {team.formations.map((formation) => (
          <button
            aria-pressed={selectedId === formation.formation_id}
            className={selectedId === formation.formation_id ? 'selected' : ''}
            key={formation.formation_id}
            onClick={() => onSelect(formation.formation_id)}
            type="button"
          >
            <strong>{formation.name}</strong>
            <small>{formation.summary}</small>
          </button>
        ))}
      </div>
    </section>
  )
}

function TacticSelector({ team, simulations, selectedId, onSelect, onPlay, playingId, copy }) {
  const selected = simulations.find((item) => item.simulation_id === selectedId) ?? simulations[0]
  if (!selected) return null
  return (
    <article className={`tactic-selector ${playingId === selected.simulation_id ? 'active' : ''}`}>
      <header>
        <TeamBadge team={{ team_id: team.team_id, name: team.team_name }} />
        <div>
          <span>{team.role}</span>
          <h3>{team.team_name}</h3>
        </div>
      </header>
      <label htmlFor={`tactic-${team.team_id}`}>{copy.chooseTeamTactic}</label>
      <select
        id={`tactic-${team.team_id}`}
        onChange={(event) => onSelect(event.target.value)}
        value={selected.simulation_id}
      >
        {simulations.map((simulation) => (
          <option key={simulation.simulation_id} value={simulation.simulation_id}>{simulation.title}</option>
        ))}
      </select>
      <p>{selected.summary}</p>
      <Button onClick={() => onPlay(selected.simulation_id)}>
        <Icon name={playingId === selected.simulation_id ? 'replay' : 'play'} size={16} />
        {playingId === selected.simulation_id ? copy.replay : copy.play}
      </Button>
    </article>
  )
}

const normalize = (value) => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

function TeamInformation({ information, home, away, copy }) {
  const [expandedTeamId, setExpandedTeamId] = useState(null)
  const [query, setQuery] = useState('')
  const teams = [home, away]
  const expanded = information.teams.find((team) => team.team_id === expandedTeamId)
  const expandedMeta = teams.find((team) => team.team_id === expandedTeamId)
  const needle = normalize(query.trim())
  const matches = (value) => !needle || normalize(JSON.stringify(value)).includes(needle)

  function toggle(teamId) {
    setExpandedTeamId((current) => current === teamId ? null : teamId)
    setQuery('')
  }

  return (
    <section className="preview-section prematch-information">
      <div className="preview-section-heading">
        <div>
          <span>{copy.informationKicker}</span>
          <h2>{information.headline}</h2>
          <p>{information.overview}</p>
        </div>
        <span className="local-data-chip">{copy.localData}</span>
      </div>

      <div className="match-fact-strip">
        {information.match_facts.map((fact) => (
          <div key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></div>
        ))}
      </div>

      <div className="team-overview-grid">
        {information.teams.map((teamInfo) => {
          const team = teams.find((item) => item.team_id === teamInfo.team_id)
          if (!team) return null
          const isOpen = expandedTeamId === team.team_id
          return (
            <article className={isOpen ? 'active' : ''} key={team.team_id}>
              <TeamBadge team={{ team_id: team.team_id, name: team.team_name }} />
              <span>{team.role}</span>
              <h3>{team.team_name}</h3>
              <p>{copy.teamInfoIntro}</p>
              <small>{teamInfo.overview}</small>
              <Button onClick={() => toggle(team.team_id)}>
                {isOpen ? copy.closeInformation : copy.expandInformation}
                <Icon name={isOpen ? 'back' : 'arrow'} size={15} />
              </Button>
            </article>
          )
        })}
      </div>

      {expanded && expandedMeta && (
        <div className="team-information-detail">
          <label className="prematch-search">
            <Icon name="search" size={18} />
            <span className="sr-only">{copy.searchInformation}</span>
            <input
              onChange={(event) => setQuery(event.target.value)}
              placeholder={copy.searchInformation}
              value={query}
            />
          </label>
          <header>
            <TeamBadge team={{ team_id: expandedMeta.team_id, name: expandedMeta.team_name }} />
            <div><span>{copy.fullReport}</span><h3>{expandedMeta.team_name}</h3></div>
          </header>

          <div className="information-sections">
            {matches([expanded.form_summary, expanded.recent_results]) && (
              <section className="information-block form-block">
                <span>{copy.form}</span><h4>{copy.recentForm}</h4><p>{expanded.form_summary}</p>
                <div className="recent-results">
                  {expanded.recent_results.map((result) => (
                    <article key={`${result.opponent}-${result.score}`}>
                      <i className={`result-${normalize(result.result)}`}>{result.result.slice(0, 1)}</i>
                      <div><strong>{result.score} · {result.opponent}</strong><small>{result.note}</small></div>
                    </article>
                  ))}
                </div>
              </section>
            )}
            {matches(expanded.availability) && (
              <section className="information-block">
                <span>{copy.squad}</span><h4>{copy.availability}</h4>
                <div className="availability-list">
                  {expanded.availability.map((item) => (
                    <article key={item.player}><div><strong>{item.player}</strong><small>{item.reason}</small></div><b>{item.status}</b></article>
                  ))}
                </div>
              </section>
            )}
            {matches(expanded.key_players) && (
              <section className="information-block">
                <span>{copy.spotlight}</span><h4>{copy.keyPlayers}</h4>
                <div className="key-player-list">
                  {expanded.key_players.map((item) => (
                    <article key={item.player}><strong>{item.player}</strong><em>{item.role}</em><p>{item.reason}</p></article>
                  ))}
                </div>
              </section>
            )}
            {matches(expanded.tactical_keys) && (
              <section className="information-block">
                <span>{copy.gamePlan}</span><h4>{copy.tacticalKeys}</h4>
                <ol>{expanded.tactical_keys.map((item) => <li key={item}>{item}</li>)}</ol>
              </section>
            )}
            {matches(expanded.probable_lineup) && (
              <section className="information-block lineup-report">
                <span>{copy.lineup}</span><h4>{copy.probableLineup}</h4>
                <p>{expanded.probable_lineup.join(' · ')}</p>
              </section>
            )}
          </div>
          {query && !matches(expanded) && <p className="no-information-results">{copy.noInformationResults}</p>}
        </div>
      )}
    </section>
  )
}

export function PrematchPreview({ matchId }) {
  const { t } = usePreferences()
  const copy = t.preview
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [homeFormation, setHomeFormation] = useState(null)
  const [awayFormation, setAwayFormation] = useState(null)
  const [playingId, setPlayingId] = useState(null)
  const [frameIndex, setFrameIndex] = useState(0)
  const [runToken, setRunToken] = useState(0)
  const [selectedTactics, setSelectedTactics] = useState({})

  useEffect(() => {
    let alive = true
    api.preview(matchId)
      .then((data) => {
        if (!alive) return
        setPreview(data)
        setHomeFormation(data.home.formations[0].formation_id)
        setAwayFormation(data.away.formations[0].formation_id)
        setSelectedTactics({
          [data.home.team_id]: data.simulations.find((item) => item.team_id === data.home.team_id)?.simulation_id,
          [data.away.team_id]: data.simulations.find((item) => item.team_id === data.away.team_id)?.simulation_id,
        })
      })
      .catch((reason) => alive && setError(reason.message))
    return () => { alive = false }
  }, [matchId])

  const activeSimulation = preview?.simulations.find((item) => item.simulation_id === playingId) ?? null

  useEffect(() => {
    if (!activeSimulation) return undefined
    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= activeSimulation.frames.length - 1) {
          window.clearInterval(timer)
          return current
        }
        return current + 1
      })
    }, 950)
    return () => window.clearInterval(timer)
  }, [activeSimulation, runToken])

  const selectedHome = useMemo(
    () => preview?.home.formations.find((item) => item.formation_id === homeFormation),
    [preview, homeFormation],
  )
  const selectedAway = useMemo(
    () => preview?.away.formations.find((item) => item.formation_id === awayFormation),
    [preview, awayFormation],
  )
  const frame = activeSimulation?.frames[frameIndex] ?? null
  const previousFrame = activeSimulation && frameIndex > 0 ? activeSimulation.frames[frameIndex - 1] : null

  function play(simulationId) {
    setFrameIndex(0)
    setPlayingId(simulationId)
    setRunToken((current) => current + 1)
  }

  return (
    <AppShell active="matches">
      <section className="prematch-page">
        <button className="preview-back" onClick={() => navigate(paths.discover())} type="button">
          <Icon name="back" size={17} /> {copy.back}
        </button>
        <ErrorNotice message={error} onRetry={() => window.location.reload()} retryLabel={t.common.retry} />
        {!preview && !error && <div className="preview-loading">{t.common.loading}</div>}

        {preview && selectedHome && selectedAway && (
          <>
            <section className="preview-hero" style={{ '--home-color': preview.home.color, '--away-color': preview.away.color }}>
              <div className="preview-hero-team home-side">
                <TeamBadge team={{ team_id: preview.home.team_id, name: preview.home.team_name }} />
                <span>{copy.home}</span>
                <h1>{preview.home.team_name}</h1>
              </div>
              <img alt={copy.duelAlt(preview.home.team_name, preview.away.team_name)} src="/images/duel.webp" />
              <div className="preview-hero-team away-side">
                <TeamBadge team={{ team_id: preview.away.team_id, name: preview.away.team_name }} />
                <span>{copy.away}</span>
                <h1>{preview.away.team_name}</h1>
              </div>
              <div className="preview-hero-title">
                <span>{copy.kicker}</span>
                <h2>{copy.title}</h2>
              </div>
            </section>

            <section className="preview-section lineups-section">
              <div className="preview-section-heading">
                <div>
                  <span>{copy.lineupsKicker}</span>
                  <h2>{copy.lineupsTitle}</h2>
                  <p>{copy.lineupsCopy}</p>
                </div>
                <span className="agent-chip"><Icon name="spark" size={15} /> {copy.agentGenerated}</span>
              </div>
              <div className="lineup-workspace">
                <FormationPicker team={preview.home} selectedId={homeFormation} onSelect={setHomeFormation} copy={copy} />
                <TacticalSimulationPitch
                  awayPlayers={selectedAway.players}
                  homeId={preview.home.team_id}
                  homePlayers={selectedHome.players}
                  label={copy.pitchLabel}
                />
                <FormationPicker team={preview.away} selectedId={awayFormation} onSelect={setAwayFormation} copy={copy} />
              </div>
            </section>

            <section className="preview-section simulation-section">
              <div className="preview-section-heading">
                <div>
                  <span>{copy.simulationKicker}</span>
                  <h2>{copy.simulationTitle}</h2>
                  <p>{copy.simulationCopy}</p>
                </div>
              </div>
              <div className="simulation-workspace">
                <div className="simulation-list">
                  {[preview.home, preview.away].map((team) => (
                    <TacticSelector
                      copy={copy}
                      key={team.team_id}
                      onPlay={play}
                      onSelect={(simulationId) => setSelectedTactics((current) => ({ ...current, [team.team_id]: simulationId }))}
                      playingId={playingId}
                      selectedId={selectedTactics[team.team_id]}
                      simulations={preview.simulations.filter((item) => item.team_id === team.team_id)}
                      team={team}
                    />
                  ))}
                </div>
                <div className="simulation-stage">
                  <TacticalSimulationPitch
                    awayPlayers={selectedAway.players}
                    frame={frame}
                    homeId={preview.home.team_id}
                    homePlayers={selectedHome.players}
                    label={copy.simulationPitchLabel}
                    previousFrame={previousFrame}
                  />
                  <div className="simulation-status">
                    <span>{frame ? `${frameIndex + 1}/${activeSimulation.frames.length}` : copy.ready}</span>
                    <strong>{frame?.phase ?? copy.chooseTactic}</strong>
                    <p>{frameIndex === activeSimulation?.frames.length - 1 ? activeSimulation.result : frame?.action ?? copy.simulationReadyCopy}</p>
                  </div>
                </div>
              </div>
            </section>

            <TeamInformation information={preview.information} home={preview.home} away={preview.away} copy={copy} />
          </>
        )}
      </section>
    </AppShell>
  )
}
