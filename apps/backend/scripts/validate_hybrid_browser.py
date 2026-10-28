"""Comprueba MP4 real y UI real contra proveedores HTTP dobles; sin Azure/GPU."""

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
from playwright.async_api import async_playwright


async def run(args):
    repository = Path(__file__).resolve().parents[3]
    args.output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PRIME_BROWSER_REPLAY_DIR": str(args.replay_dir.resolve())}
    log = (args.output / "browser-server.log").open("w")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "browser_hybrid_server:app",
                               "--app-dir", "apps/backend/tests", "--host", "127.0.0.1", "--port", "8127"],
                              cwd=repository, env=env, stdout=log, stderr=subprocess.STDOUT)
    errors, checks, simulation_requests = [], [], []
    try:
        async with httpx.AsyncClient() as client:
            for attempt in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Servidor de prueba falló; consulte browser-server.log")
                try:
                    response = await client.get("http://127.0.0.1:8127/api/v1/health")
                    if response.status_code == 200:
                        break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(0.2)
            else:
                raise RuntimeError("El servidor local no inició")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                                       args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: simulation_requests.append(request.url) if request.url.endswith("/simulation") else None)
            await page.add_init_script("if (!localStorage.getItem('itg:preferences')) localStorage.setItem('itg:preferences', JSON.stringify({language:'es',theme:'dark',mode:'analyst',level:'normal',favoriteTeamId:'',favoritePlayerId:'',liveComments:true,onboarded:true}))")
            await page.goto("http://127.0.0.1:8127/#/match/synthetic-live-001")
            await page.locator("video").wait_for()
            await page.wait_for_function("document.querySelector('video').readyState >= 2")
            initial = await page.request.get("http://127.0.0.1:8127/__test__/status")
            assert (await initial.json())["providers"]["player"] == 0
            checks.append("No captura antes de Play")
            await page.get_by_role("button", name="Iniciar partido en vivo", exact=True).click()
            await page.wait_for_function("document.querySelector('video').currentTime > 2")
            await page.wait_for_function("document.querySelectorAll('.vision-box').length > 0")
            assert await page.get_by_text("Datos del simulador MESSI", exact=False).count() > 0
            checks.append("Play reproduce MP4, JPEG a Roboflow y eventos MESSI legibles")
            before = await page.locator("video").evaluate("video => { window.__testedVideo = video; return video.currentTime }")
            await page.get_by_role("tab", name="Estadísticas", exact=True).click()
            await page.wait_for_timeout(500)
            await page.get_by_role("tab", name="Partido", exact=True).click()
            same = await page.locator("video").evaluate("video => video === window.__testedVideo && video.currentTime > " + str(before))
            assert same
            checks.append("Cambiar pestaña conserva el mismo vídeo y reloj")
            await page.locator(".play-main").click()
            await page.wait_for_timeout(1000)
            status = await (await page.request.get("http://127.0.0.1:8127/__test__/status")).json()
            count = status["providers"]["player"]
            position = await page.locator("video").evaluate("video => video.currentTime")
            await page.wait_for_timeout(1500)
            paused = await (await page.request.get("http://127.0.0.1:8127/__test__/status")).json()
            assert paused["providers"]["player"] == count
            assert abs(await page.locator("video").evaluate("video => video.currentTime") - position) < 0.1
            assert not paused["capture"]["playing"]
            checks.append("Pausa detiene fotogramas y reloj")
            await page.screenshot(path=str(args.output / "partido-pausa.png"), full_page=True)
            assert status["providers"]["teamspotting"] == 1
            assert status["providers"]["player"] == status["providers"]["ball"] == status["providers"]["pitch"] > 0
            checks.append("Tres roles Roboflow llamados; TeamSpotting una sola inferencia")
            # Saltar cerca de los dos primeros tiros reales del simulador.
            await page.locator(".timeline").evaluate("node => {const r=node.getBoundingClientRect(); node.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:r.left+r.width*(81.8/180),clientY:r.top+2}))}")
            await page.wait_for_function("Math.abs(document.querySelector('video').currentTime - 81.8) < 0.3")
            await page.wait_for_timeout(500)
            await page.locator(".play-main").click()
            await page.wait_for_function("document.querySelector('video').currentTime > 83.5")
            await page.locator(".play-main").click()
            await page.get_by_text("Jugador 9 remata", exact=False).first.wait_for()
            shots = await (await page.request.get("http://127.0.0.1:8127/__test__/status")).json()
            assert shots["routing"]["important_published"] >= 1
            checks.append("Salto y reanudación muestran tiros del MP4 y entregan ruta importante")
            await page.screenshot(path=str(args.output / "partido-tiros.png"), full_page=True)
            await page.get_by_role("tab", name="Resumen", exact=True).click()
            await page.wait_for_timeout(500)
            await page.get_by_role("tab", name="Vista táctica", exact=True).click()
            await page.wait_for_timeout(500)
            await page.get_by_role("tab", name="Partido", exact=True).click()
            old_runs = shots["providers"]["teamspotting"]
            await page.get_by_role("button", name="Repetir", exact=True).click()
            await page.wait_for_function("document.querySelector('video').currentTime > 0.5 && document.querySelector('video').currentTime < 5")
            await page.locator(".play-main").click()
            replayed = await (await page.request.get("http://127.0.0.1:8127/__test__/status")).json()
            assert replayed["providers"]["teamspotting"] == old_runs
            assert replayed["routing"]["important_published"] == shots["routing"]["important_published"]
            checks.append("Reinicio reutiliza TeamSpotting y no duplica jugadas en colas")
            # Cambiar idioma conserva el texto de procedencia en lugar de
            # renderizar undefined por una traducción ubicada en otra sección.
            await page.evaluate("localStorage.setItem('itg:preferences', JSON.stringify({...JSON.parse(localStorage.getItem('itg:preferences')),language:'en'}))")
            await page.reload()
            await page.locator("video").wait_for()
            await page.locator(".play-main").click()
            await page.wait_for_function("document.querySelector('video').currentTime > 1")
            await page.get_by_text("MESSI simulator data", exact=False).first.wait_for()
            await page.locator(".play-main").click()
            checks.append("Interfaz inglesa reproduce y muestra procedencia sin errores")
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.screenshot(path=str(args.output / "partido-mobile.png"), full_page=True)
            overflow = await page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
            assert not overflow, "La interfaz móvil desborda horizontalmente"
            checks.append("Vista móvil de 390 px sin desbordamiento horizontal")
            assert simulation_requests == [], simulation_requests
            checks.append("Iniciar MP4 no ejecuta el guion de simulación de Ariel")
            await page.evaluate("localStorage.setItem('itg:preferences', JSON.stringify({...JSON.parse(localStorage.getItem('itg:preferences')),favoriteTeamId:'aurora-fc',favoritePlayerId:'aurora-8',mode:'player'}))")
            await page.reload()
            await page.locator("video").wait_for()
            await page.locator(".play-main").click()
            await page.wait_for_function("document.querySelector('video').currentTime > 0.5")
            await page.locator(".play-main").click()
            checks.append("Preferencias guardadas de otro partido no bloquean MESSI")
            await page.goto("http://127.0.0.1:8127/#/match/synthetic-acceptance-001")
            await page.locator(".live-tracking-pitch").wait_for()
            assert await page.locator("video").count() == 0
            checks.append("El escenario original conserva su cancha, sin superponerle el MP4")
            assert not errors, errors
            await browser.close()
            report = {"status": "passed", "tested_at": datetime.now(UTC).isoformat(),
                      "scope": "real_browser_real_mp4_http_model_test_doubles_memory_queues", "checks": checks,
                      "page_errors": errors, "runtime": replayed, "simulation_requests": simulation_requests}
            (args.output / "browser-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
