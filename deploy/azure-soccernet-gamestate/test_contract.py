from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_runner_keeps_identity_as_observation() -> None:
    exporter = (ROOT / "export_tracker_state.py").read_text(encoding="utf-8")
    assert '"jersey_number"' in exporter
    assert '"track_id"' in exporter
    assert '"player_id"' not in exporter


def test_api_is_async_and_protects_results() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'status_code=status.HTTP_202_ACCEPTED' in source
    assert 'Depends(require_api_key)' in source
    assert 'app.state.analysis_lock' in source


def test_image_preloads_every_runtime_checkpoint() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    preloader = (ROOT / "preload_models.py").read_text(encoding="utf-8")
    api = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "python /opt/prime/preload_models.py" in dockerfile
    for expected in (
        "yolo11m.pt",
        "prtreid-soccernet-baseline.pth.tar",
        "hrnetv2_w32_imagenet_pretrained.pth",
        "SV_kp",
        "SV_lines",
        "7c0e94f2.pth",
        "04eb4e75.pth",
    ):
        assert expected in preloader
    assert "inspect_preloaded_models()" in api


def test_api_dependency_annotation_is_compatible_with_python_39() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Annotated[Optional[str], Header" in source
    assert "Annotated[str | None, Header" not in source


def test_deployment_defaults_to_scale_zero() -> None:
    operator = (ROOT.parent.parent / "infra/azure/gamestate-operator.sh").read_text(encoding="utf-8")
    assert "export MENTOX_MIN_REPLICAS=0" in operator
    assert '--min-replicas 0 --max-replicas 1' in operator

