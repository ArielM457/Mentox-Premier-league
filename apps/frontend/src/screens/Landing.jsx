import { ThemeToggle } from '../components/ui/ThemeToggle.jsx'
import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { MODE_ART } from '../data/branding.js'
import { Brand } from '../components/ui/Brand.jsx'
import { Button } from '../components/ui/Button.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'

const POINT_ICONS = ['match', 'spark', 'replay']

export function Landing() {
  const { t, preferences } = usePreferences()
  const copy = t.landing
  const [selectedPoint, setSelectedPoint] = useState(0)
  const [examplePlaying, setExamplePlaying] = useState(true)
  const start = () => navigate(preferences.onboarded ? paths.discover() : paths.onboarding())

  return (
    <main className="landing">
      <header className="landing-header">
        <Brand />
        <div className="landing-actions">
          <ThemeToggle /><LanguageSwitch variant="landing" />
          <Button onClick={start}>
            {copy.start} <Icon name="arrow" size={17} />
          </Button>
        </div>
      </header>

      <section className="hero" id="home">
        <div className="hero-copy">
          <span className="eyebrow">
            <span className="live-dot" /> {copy.eyebrow}
          </span>
          <h1>
            {copy.titleA} <strong>{copy.titleB}</strong>
          </h1>
          <p>{copy.intro}</p>
          <Button variant="lime" onClick={start}>
            {copy.start} <Icon name="arrow" size={19} />
          </Button>
        </div>
        <div className="hero-art">
          <img alt="" className="hero-main-illustration" src="/images/stadium.webp" />
          <span className="hero-live-chip">
            <i /> {copy.sampleLabel} · 0:32
          </span>
          <p className="hero-image-caption">{copy.caption}</p>
        </div>
      </section>

      <section className="home-discover">
        <div className="home-section-heading">
          <span className="section-kicker">{copy.discoverKicker}</span>
          <h2>
            {copy.discoverA} <strong>{copy.discoverB}</strong>
          </h2>
        </div>
        <div className="discover-showcase">
          <div className="discover-illustration">
            <img alt="" src="/images/player.webp" />
          </div>
          <div className="discover-points">
            {copy.points.map(([title, description], index) => (
              <button className={selectedPoint === index ? 'active' : ''} key={title} onClick={() => { setSelectedPoint(index); start() }} type="button">
                <span className="point-number">0{index + 1}</span>
                <span className="point-icon">
                  <Icon name={POINT_ICONS[index]} />
                </span>
                <div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </div>
                <Icon name="arrow" size={18} />
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="home-example">
        <div className="example-copy">
          <span className="section-kicker">{copy.exampleKicker}</span>
          <h2>{copy.exampleTitle}</h2>
          <p>{copy.exampleCopy}</p>
          <span className="ai-explanation-label">
            <Icon name="spark" size={17} /> {t.assistant.title}
          </span>
        </div>
        <div className={`example-card ${examplePlaying ? 'is-active' : ''}`}>
          <div className="sample-pitch">
            <span className="sample-player player-one" />
            <span className="sample-player player-two" />
            <span className="sample-player player-three" />
            <span className="sample-player player-target" />
            <span className="sample-pass" />
            <span className="sample-ball">
              <Icon name="ball" size={16} />
            </span>
            <button
              aria-label={examplePlaying ? t.match.pause : t.match.play}
              className="sample-play"
              onClick={() => setExamplePlaying(!examplePlaying)}
              type="button"
            >
              <Icon name={examplePlaying ? 'pause' : 'play'} />
            </button>
          </div>
          <strong>{copy.evidence}</strong>
          <div className="evidence-stats">
            {copy.evidenceStats.map(([value, label]) => (
              <span key={label}>
                <b>{value}</b>
                <small>{label}</small>
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="home-modes">
        <div className="home-section-heading">
          <span className="section-kicker">{copy.modesKicker}</span>
          <h2>
            {copy.modesA}
            <br />
            <strong>{copy.modesB}</strong>
          </h2>
        </div>
        <div className="home-mode-grid">
          {['casual', 'analyst', 'player'].map((mode, index) => (
            <article className={`mode-preview mode-preview-${index + 1}`} key={mode}>
              <div className="mode-preview-art">
                <img alt="" src={MODE_ART[mode].image} />
                <span>0{index + 1}</span>
              </div>
              <div className="mode-preview-copy">
                <h3>{t.modes[mode].name}</h3>
                <p>{t.modes[mode].description}</p>
                <small>
                  {copy.available}
                  <Icon name="arrow" size={15} />
                </small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="home-closing">
        <div className="closing-copy">
          <span className="closing-kicker">
            <Icon name="spark" size={16} /> {t.brand}
          </span>
          <h2>
            {copy.closingA} <strong>{copy.closingB}</strong>
          </h2>
          <p>{copy.closingCopy(t.modes[preferences.mode].name)}</p>
          <div className="closing-tags">
            {copy.tags.map((tag, index) => (
              <span key={tag}>
                <Icon name={POINT_ICONS[index]} size={15} /> {tag}
              </span>
            ))}
          </div>
          <Button variant="lime" onClick={start}>
            {copy.explore} <Icon name="arrow" size={19} />
          </Button>
        </div>
        <div className="closing-art">
          <span className="closing-orbit orbit-one" />
          <span className="closing-orbit orbit-two" />
          <img alt="" src="/images/fans.webp" />
        </div>
      </section>

      <footer>
        <Brand />
        <span>{copy.footer}</span>
      </footer>
    </main>
  )
}
