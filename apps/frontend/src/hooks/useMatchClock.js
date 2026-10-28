import { useCallback, useEffect, useRef, useState } from 'react'

const TICK_MS = 100

// Devuelve el <video> solo si tiene un archivo cargado.
function activeVideo(ref) {
  return ref?.current?.src ? ref.current : null
}

// Reloj del vídeo. Sin archivo de vídeo usa una línea de tiempo simulada; con
// un <video> conectado, el tiempo sale de currentTime para que mande el vídeo.
export function useMatchClock(durationMs, videoRef) {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeedState] = useState(1)
  const anchor = useRef({ wall: 0, video: 0 })
  const timeRef = useRef(0)

  const update = useCallback((value) => {
    timeRef.current = value
    setTime(value)
  }, [])

  useEffect(() => {
    if (!playing) return undefined
    anchor.current = { wall: performance.now(), video: timeRef.current }
    const id = setInterval(() => {
      const video = activeVideo(videoRef)
      let next = video
        ? video.currentTime * 1000
        : anchor.current.video + (performance.now() - anchor.current.wall) * speed
      if (next >= durationMs) {
        next = durationMs
        setPlaying(false)
        video?.pause()
      }
      update(next)
    }, TICK_MS)
    return () => clearInterval(id)
  }, [playing, speed, durationMs, update, videoRef])

  const play = useCallback(async () => {
    if (timeRef.current >= durationMs) update(0)
    const video = activeVideo(videoRef)
    if (video) {
      video.currentTime = timeRef.current / 1000
      try {
        await video.play()
      } catch (error) {
        setPlaying(false)
        throw error
      }
    }
    setPlaying(true)
  }, [durationMs, update, videoRef])

  const pause = useCallback(() => {
    const video = activeVideo(videoRef)
    video?.pause()
    if (video) update(Math.min(durationMs, Math.round(video.currentTime * 1000)))
    setPlaying(false)
  }, [videoRef, durationMs, update])

  const seek = useCallback((value) => {
    const next = Math.min(Math.max(0, value), durationMs)
    const video = activeVideo(videoRef)
    if (video) video.currentTime = next / 1000
    anchor.current = { wall: performance.now(), video: next }
    update(next)
  }, [durationMs, update, videoRef])

  const setSpeed = useCallback((value) => {
    const video = activeVideo(videoRef)
    if (video) video.playbackRate = value
    anchor.current = { wall: performance.now(), video: timeRef.current }
    setSpeedState(value)
  }, [videoRef])

  return { time, playing, speed, play, pause, seek, setSpeed, timeRef }
}
