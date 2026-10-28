"""Prueba autorizada: UI local, MP4 de Blob, inferencia y colas reales de Azure.

No enciende ni apaga recursos. Publica eventos reales de la demo al reproducir;
requiere backend/frontend configurados. No recibe ni registra API keys.
"""

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx
from playwright.async_api import async_playwright


async def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"scope": "real_browser_blob_mp4_remote_gpu_models_azure_queues",
              "started_at": datetime.now(UTC).isoformat(), "status": "running", "checks": []}
    errors, failed_http, model_responses = [], [], []
    browser = page = None
    last_position = 0
    async with httpx.AsyncClient(base_url=args.backend, timeout=20) as client:
        async def status():
            response = await client.get("/api/v1/integration/status")
            response.raise_for_status()
            return response.json()

        try:
            deadline = time.monotonic() + args.prepare_timeout
            while True:
                current = await status()
                prep = current["runtime"]["model_preparation"]
                print(json.dumps({"preparation": prep["status"],
                                  "roboflow": current["runtime"]["live_capture"]["model_ready"],
                                  "teamspotting": current["runtime"]["teamspotting"]["status"]}), flush=True)
                if prep["status"] == "ready":
                    break
                if prep["status"] in {"failed", "interrupted"}:
                    raise RuntimeError(prep.get("error"))
                if time.monotonic() >= deadline:
                    raise TimeoutError("Preparación no terminó dentro del plazo")
                await asyncio.sleep(15)
            report["before"] = current
            runtime = current["runtime"]
            assert runtime["live_capture"]["model_ready"]
            assert runtime["teamspotting"]["device"] and runtime["teamspotting"]["runs"] >= 1
            assert runtime["gamestate"]["status"] == "retired"
            assert runtime["vision_observations"]["transport"] == "azure_event_hubs"
            assert not runtime["live_capture"]["playing"], "Ya hay otra reproducción activa"
            report["checks"].append("Ambos modelos reales preparados sobre el MP4 verificado; GameState retirado")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(executable_path=args.chrome, headless=True,
                    args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
                page = await browser.new_page(viewport={"width": 1440, "height": 1100})
                page.on("pageerror", lambda error: errors.append(str(error)))

                async def response_seen(response):
                    path = urlsplit(response.url).path
                    if "/api/" in path and response.status >= 400:
                        failed_http.append({"path": path, "status": response.status})
                    if path.endswith("/live/capture/frame") and response.ok:
                        model_responses.append(await response.json())

                page.on("response", response_seen)
                await page.add_init_script("localStorage.setItem('itg:preferences', JSON.stringify({language:'es',theme:'dark',mode:'analyst',level:'normal',favoriteTeamId:'',favoritePlayerId:'',liveComments:true,onboarded:true}))")
                await page.goto(f"{args.frontend}/#/match/{args.match_id}")
                await page.locator("video").wait_for()
                await page.wait_for_function("document.querySelector('video').readyState >= 2")
                await page.get_by_text("Canal conectado", exact=True).wait_for()
                report["checks"].append("WebSocket de visión conectado a través del proxy del frontend")
                assert (await status())["runtime"]["live_capture"]["frames_received"] == runtime["live_capture"]["frames_received"]
                report["checks"].append("Abrir el partido no captura antes de Play")
                await page.locator(".play-main").click()
                await page.wait_for_function("document.querySelector('video').currentTime > 8", timeout=90000)
                await page.locator(".play-main").click()
                await asyncio.sleep(2)
                paused = await status()
                received = paused["runtime"]["live_capture"]["frames_received"]
                position = await page.locator("video").evaluate("v => v.currentTime")
                last_position = position
                await asyncio.sleep(2)
                assert (await status())["runtime"]["live_capture"]["frames_received"] == received
                assert abs(await page.locator("video").evaluate("v => v.currentTime") - position) < 0.1
                assert not paused["runtime"]["live_capture"]["playing"]
                report["checks"].append("Pausa detiene reloj y nuevas capturas contra Roboflow remoto")
                await page.screenshot(path=str(args.output / "partido-pausa-azure.png"), full_page=True)
                await page.locator(".play-main").click()
                # Reanudar consulta salud remota; el clic no implica que
                # video.play() haya terminado ya, especialmente en Azure.
                await page.wait_for_function("v => !document.querySelector('video').paused && document.querySelector('video').currentTime > v",
                                             arg=position + 0.2, timeout=90000)
                playback_deadline = time.monotonic() + 360
                shot_saved = False
                while True:
                    video = await page.locator("video").evaluate("v => ({time:v.currentTime,duration:v.duration,paused:v.paused,ended:v.ended})")
                    last_position = video["time"]
                    latest = await status()
                    print(json.dumps({"video": video, "frames": latest["runtime"]["live_capture"]["frames_processed"],
                                      "routed": latest["runtime"]["simulator"]["events_routed"],
                                      "failures": latest["runtime"]["live_capture"]["failures"]}), flush=True)
                    if not shot_saved and video["time"] >= 84:
                        await page.screenshot(path=str(args.output / "partido-tiros-azure.png"), full_page=True)
                        shot_saved = True
                    if video["ended"]:
                        break
                    if video["paused"]:
                        raise RuntimeError("La UI pausó el vídeo por un error; revise el reporte HTTP")
                    if time.monotonic() > playback_deadline:
                        raise TimeoutError("La reproducción no terminó dentro del plazo")
                    await asyncio.sleep(10)
                await asyncio.sleep(5)
                final = await status()
                routing = (await client.get("/api/v1/agent-routing/status")).json()
                report.update(after=final, routing=routing, capture_responses=model_responses)
                assert final["runtime"]["live_capture"]["frames_processed"] > 0
                accepted = [item for item in model_responses if item.get("accepted")]
                assert accepted and all(item["models"] == 3 for item in accepted)
                assert final["runtime"]["live_capture"]["failures"] == 0
                assert final["runtime"]["teamspotting"]["runs"] == runtime["teamspotting"]["runs"]
                assert final["runtime"]["vision_observations"]["producer_published"] > 0
                assert final["runtime"]["vision_observations"]["consumer_accepted"] > 0
                assert final["runtime"]["simulator"]["events_pending_delivery"] == 0
                assert routing["transport"] == "azure" and routing["metrics_published"] > 0 and routing["important_published"] > 0
                assert not errors, errors
                assert not failed_http, failed_http
                report["checks"].extend([
                    "MP4 completo reproducido a velocidad normal",
                    "Roboflow remoto procesó capturas sin fallos",
                    "TeamSpotting no repitió inferencia al reanudar",
                    "Event Hubs publicó y su consumidor aceptó observaciones",
                    "Métricas y jugadas importantes entregadas a sus transportes Azure",
                    "Sin errores JavaScript ni HTTP de la API durante la reproducción",
                ])
                await page.screenshot(path=str(args.output / "partido-final-azure.png"), full_page=True)
                report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", error=f"{type(error).__name__}: {error}")
            if page is not None and not page.is_closed():
                await page.screenshot(path=str(args.output / "partido-error-azure.png"), full_page=True)
            raise
        finally:
            # El contexto Playwright puede estar cerrado tras una excepción.
            # Detener el backend sin ocultar el resultado por ese cierre.
            try:
                await client.post("/api/v1/integration/live/playback/pause", json={
                    "match_id": args.match_id,
                    "video_time_ms": round(last_position * 1000),
                })
            except Exception as error:
                report["cleanup_error"] = type(error).__name__
            if browser is not None and browser.is_connected():
                await browser.close()
            report.update(finished_at=datetime.now(UTC).isoformat(), page_errors=errors, failed_http=failed_http)
            (args.output / "azure-browser-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"status": report["status"], "checks": report["checks"], "error": report.get("error")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend", default="http://127.0.0.1:5173")
    parser.add_argument("--match-id", default="synthetic-live-001")
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--prepare-timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
