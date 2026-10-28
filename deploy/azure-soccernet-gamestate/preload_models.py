"""Descarga durante el build todos los pesos usados por SoccerNet GameState."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen


MODEL_ROOT = Path("/models")
MANIFEST_PATH = MODEL_ROOT / "preloaded-models.json"


def digest(path: Path, algorithm: str) -> str:
    checksum = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(name: str, url: str, destination: Path, md5: str | None = None) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    if not destination.is_file():
        print(f"[preload] Descargando {name} -> {destination}", flush=True)
        request = Request(url, headers={"User-Agent": "The-Prime-Moment-model-preloader/1.0"})
        with urlopen(request, timeout=120) as response, temporary.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        temporary.replace(destination)
    if destination.stat().st_size < 1024:
        raise RuntimeError(f"{name} quedó incompleto: {destination}")
    if md5 and digest(destination, "md5") != md5:
        raise RuntimeError(f"MD5 inválido para {name}: {destination}")
    return entry(name, destination, url)


def entry(name: str, path: Path, source: str) -> dict[str, object]:
    return {
        "name": name,
        "path": str(path),
        "source": source,
        "bytes": path.stat().st_size,
        "sha256": digest(path, "sha256"),
    }


def find_one(pattern: str) -> Path:
    matches = list(MODEL_ROOT.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Se esperaba un archivo para {pattern}; encontrados: {matches}")
    return matches[0]


def main() -> None:
    records = [
        download(
            "reid-soccernet",
            "https://zenodo.org/records/10653453/files/prtreid-soccernet-baseline.pth.tar?download=1",
            MODEL_ROOT / "reid/prtreid-soccernet-baseline.pth.tar",
            "9633825232bc89f23a94522c5561650e",
        ),
        download(
            "reid-hrnet32",
            "https://zenodo.org/records/10604211/files/hrnetv2_w32_imagenet_pretrained.pth?download=1",
            MODEL_ROOT / "reid/hrnetv2_w32_imagenet_pretrained.pth",
            "58ea12b0420aa3adaa2f74114c9f9721",
        ),
        download(
            "pitch-keypoints",
            "https://zenodo.org/records/12626395/files/SV_kp?download=1",
            MODEL_ROOT / "calibration/SV_kp",
        ),
        download(
            "pitch-lines",
            "https://zenodo.org/records/12626395/files/SV_lines?download=1",
            MODEL_ROOT / "calibration/SV_lines",
        ),
    ]

    # Ultralytics conserva el peso en la ruta indicada por la configuración de TrackLab.
    from ultralytics import YOLO

    yolo_path = MODEL_ROOT / "yolo/yolo11m.pt"
    yolo_path.parent.mkdir(parents=True, exist_ok=True)
    YOLO(str(yolo_path))
    records.append(entry("bbox-yolo11m", yolo_path, "ultralytics-assets"))

    # MMOCR resuelve sus configuraciones oficiales y deja los dos checkpoints en TORCH_HOME.
    from mmocr.apis import MMOCRInferencer

    MMOCRInferencer(det="dbnet_resnet18_fpnc_1200e_icdar2015", rec="SAR", device="cpu")
    detector = find_one("torch/hub/checkpoints/**/*7c0e94f2.pth")
    recognizer = find_one("torch/hub/checkpoints/**/*04eb4e75.pth")
    records.extend([
        entry("jersey-ocr-detector", detector, "MMOCR model zoo"),
        entry("jersey-ocr-recognizer", recognizer, "MMOCR model zoo"),
    ])

    MANIFEST_PATH.write_text(
        json.dumps({"schema_version": 1, "models": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[preload] {len(records)} pesos listos; manifiesto: {MANIFEST_PATH}", flush=True)


if __name__ == "__main__":
    main()
