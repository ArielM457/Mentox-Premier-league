"""Pruebas de la API sin CUDA: el ejecutor externo se sustituye por un doble."""

import asyncio
import importlib.util
import io
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.datastructures import Headers


@pytest.fixture
def service(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    spec = importlib.util.spec_from_file_location("gamestate_service_under_test", Path(__file__).with_name("app.py"))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "API_KEY", "test-secret")
    monkeypatch.setattr(module, "inspect_video", lambda _: {"fps": 15, "frames": 150, "duration_ms": 10000})
    return module


async def submit(service):
    service.app.state.analysis_lock = asyncio.Lock()
    upload = UploadFile(io.BytesIO(b"mp4"), filename="match.mp4", headers=Headers({"content-type": "video/mp4"}))
    return await service.create_analysis(BackgroundTasks(), upload)


def test_authentication_and_analysis_paths_are_validated(service):
    service.require_api_key("test-secret")
    with pytest.raises(HTTPException) as invalid:
        service.require_api_key("incorrect")
    assert invalid.value.status_code == 401
    with pytest.raises(HTTPException) as invalid_path:
        service.read_metadata("../../status")
    assert invalid_path.value.status_code == 404


def test_analysis_failure_is_observable_and_releases_capacity(service, monkeypatch):
    async def scenario():
        created = await submit(service)
        assert created["status"] == "queued"
        with pytest.raises(HTTPException) as busy:
            await submit(service)
        assert busy.value.status_code == 429

        class Process:
            returncode = 7

            async def wait(self):
                return 7

        async def spawn(*args, **kwargs):
            assert service.read_metadata(created["analysis_id"])["status"] == "running"
            return Process()

        monkeypatch.setattr(service.asyncio, "create_subprocess_exec", spawn)
        await service.execute_analysis(created["analysis_id"])
        metadata = service.read_metadata(created["analysis_id"])
        assert metadata["status"] == "failed"
        assert "código 7" in metadata["error"]
        assert not (service.ROOT / created["analysis_id"] / "input.mp4").exists()
        assert service.app.state.accepting_analysis is False

    asyncio.run(scenario())


def test_timeout_kills_the_process_group_and_records_failure(service, monkeypatch):
    async def scenario():
        created = await submit(service)

        class Process:
            pid = 42
            returncode = None

            async def wait(self):
                if self.returncode is None:
                    await asyncio.Event().wait()
                return self.returncode

        process = Process()
        killed = []

        async def spawn(*args, **kwargs):
            assert kwargs["start_new_session"] is True
            return process

        def killpg(pid, sig):
            killed.append(pid)
            process.returncode = -9

        monkeypatch.setattr(service, "ANALYSIS_TIMEOUT_SECONDS", 0.01)
        monkeypatch.setattr(service.asyncio, "create_subprocess_exec", spawn)
        monkeypatch.setattr(service.os, "killpg", killpg)
        await service.execute_analysis(created["analysis_id"])
        assert killed == [42]
        assert service.read_metadata(created["analysis_id"])["status"] == "failed"
        assert service.app.state.accepting_analysis is False

    asyncio.run(scenario())


def test_successful_empty_result_is_not_an_error(service, monkeypatch):
    async def scenario():
        created = await submit(service)
        directory = service.ROOT / created["analysis_id"] / "output"
        directory.mkdir()
        (directory / "gamestate-observations.jsonl").write_text("")

        class Process:
            returncode = 0

            async def wait(self):
                return 0

        async def spawn(*args, **kwargs):
            return Process()

        monkeypatch.setattr(service.asyncio, "create_subprocess_exec", spawn)
        await service.execute_analysis(created["analysis_id"])
        metadata = service.read_metadata(created["analysis_id"])
        assert metadata["status"] == "succeeded"
        assert metadata["observations"] == 0
        assert service.app.state.accepting_analysis is False

    asyncio.run(scenario())
