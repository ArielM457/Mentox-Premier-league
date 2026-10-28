import { useCallback, useEffect, useRef, useState } from 'react'

function readPlayback(key, duration) {
  try {
    const saved = JSON.parse(localStorage.getItem(`itg:playback:${key}`) || sessionStorage.getItem(`itg:playback:${key}`) || '{}')
    const time = Math.min(duration, Math.max(0, Number(saved.time) || 0))
    return { time, liveEdge: Math.min(duration, Math.max(time, Number(saved.liveEdge) || 0)), speed: [1, 2, 4, 8].includes(saved.speed) ? saved.speed : 1 }
  } catch { return { time: 0, liveEdge: 0, speed: 1 } }
}

function activeVideo(ref) { return ref?.current?.src ? ref.current : null }

// Resume at the saved position, paused, so leaving a screen never advances it invisibly.
export function useMatchClock(durationMs, videoRef, matchId) {
  const [initial] = useState(() => readPlayback(matchId, durationMs))
  const [time, setTime] = useState(initial.time)
  const [liveEdge, setLiveEdge] = useState(initial.liveEdge)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeedState] = useState(initial.speed)
  const anchor = useRef({ wall: 0, video: initial.time })
  const timeRef = useRef(initial.time)
  const liveEdgeRef = useRef(initial.liveEdge)
  const speedRef = useRef(initial.speed)
  const update = useCallback((value) => {
    timeRef.current = value
    setTime(value)
    if (value > liveEdgeRef.current) {
      liveEdgeRef.current = value
      setLiveEdge(value)
    }
  }, [])
  const persist = useCallback(() => {
    try { localStorage.setItem(`itg:playback:${matchId}`, JSON.stringify({ time: timeRef.current, liveEdge: liveEdgeRef.current, speed: speedRef.current })) } catch { /* Session remains usable without storage. */ }
  }, [matchId])

  useEffect(() => {
    const id = setInterval(persist, 1000)
    window.addEventListener('pagehide', persist)
    return () => { clearInterval(id); persist(); window.removeEventListener('pagehide', persist) }
  }, [persist])

  useEffect(() => {
    if (!playing) return undefined
    anchor.current = { wall: performance.now(), video: timeRef.current }
    const id = setInterval(() => {
      const video = activeVideo(videoRef)
      let next = video ? video.currentTime * 1000 : anchor.current.video + (performance.now() - anchor.current.wall) * speed
      if (next >= durationMs) { next = durationMs; setPlaying(false); video?.pause() }
      update(next)
    }, 100)
    return () => clearInterval(id)
  }, [playing, speed, durationMs, update, videoRef])

  const play = useCallback(() => {
    if (timeRef.current >= durationMs) update(0)
    const video = activeVideo(videoRef)
    if (video) { video.currentTime = timeRef.current / 1000; video.play().catch(() => setPlaying(false)) }
    setPlaying(true)
  }, [durationMs, update, videoRef])
  const pause = useCallback(() => { activeVideo(videoRef)?.pause(); setPlaying(false); persist() }, [videoRef, persist])
  const seek = useCallback((value) => {
    const next = Math.min(Math.max(0, value), durationMs)
    const video = activeVideo(videoRef)
    if (video) video.currentTime = next / 1000
    anchor.current = { wall: performance.now(), video: next }
    update(next)
    persist()
  }, [durationMs, update, videoRef, persist])
  const setSpeed = useCallback((value) => {
    const video = activeVideo(videoRef)
    if (video) video.playbackRate = value
    anchor.current = { wall: performance.now(), video: timeRef.current }
    speedRef.current = value
    setSpeedState(value)
    persist()
  }, [videoRef, persist])
  return { time, liveEdge, playing, speed, play, pause, seek, setSpeed, timeRef }
}
