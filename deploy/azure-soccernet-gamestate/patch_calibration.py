"""Corrige keypoints de GameState y el estado vacío de TrackLab fijados."""

import argparse
import importlib.util
from pathlib import Path


RELATIVE_PATH = Path("sn_gamestate/calibration/nbjw_calib.py")
BEFORE = 'predictions = metadatas["keypoints"][0]'
AFTER = 'predictions = metadatas["keypoints"].iloc[0]'
TRACKER_PATH = Path("datastruct/tracker_state.py")
TRACKER_BEFORE = "video_detections = pd.DataFrame()"
TRACKER_AFTER = 'video_detections = pd.DataFrame(columns=["video_id", "image_id"])'


def patched_source(source: str) -> str:
    return replace_expected(source, BEFORE, AFTER, RELATIVE_PATH)


def patched_tracker_source(source: str) -> str:
    return replace_expected(source, TRACKER_BEFORE, TRACKER_AFTER, TRACKER_PATH)


def replace_expected(source: str, before: str, after: str, path: Path) -> str:
    original_count = source.count(before)
    patched_count = source.count(after)
    if original_count == 1 and patched_count == 0:
        result = source.replace(before, after, 1)
    elif original_count == 0 and patched_count == 1:
        result = source
    else:
        raise RuntimeError(
            "El código de {} cambió: original={}, corregido={}. "
            "Revise el parche antes de construir.".format(
                path, original_count, patched_count
            )
        )
    compile(result, str(path), "exec")
    return result


def patch_calibration(root: Path) -> bool:
    target = root / RELATIVE_PATH
    source = target.read_text(encoding="utf-8")
    result = patched_source(source)
    if result == source:
        return False
    target.write_text(result, encoding="utf-8")
    return True


def patch_tracker_state(root: Path) -> bool:
    target = root / TRACKER_PATH
    source = target.read_text(encoding="utf-8")
    result = patched_tracker_source(source)
    if result == source:
        return False
    target.write_text(result, encoding="utf-8")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/opt/sn-gamestate"))
    args = parser.parse_args()
    changed = patch_calibration(args.root)
    print("Calibración GameState: {}".format("parche aplicado" if changed else "ya corregida"))
    tracklab = importlib.util.find_spec("tracklab")
    if tracklab is None or not tracklab.submodule_search_locations:
        raise RuntimeError("No se encontró el paquete TrackLab que debe corregirse")
    changed = patch_tracker_state(Path(next(iter(tracklab.submodule_search_locations))))
    print("Estado vacío TrackLab: {}".format("parche aplicado" if changed else "ya corregido"))
