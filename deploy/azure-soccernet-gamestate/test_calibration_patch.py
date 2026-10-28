"""Regresiones sin GPU; también ejecutables con unittest dentro de la imagen."""

import ast
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gamestate_calibration_patch", ROOT / "patch_calibration.py")
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)

SOURCE = '''class NBJW_Calib:
    def process(self, batch, detections, metadatas):
        predictions = metadatas["keypoints"][0]
        return predictions
'''
TRACKER_SOURCE = '''def load():
    video_detections = pd.DataFrame()
    return video_detections
'''


class CalibrationPatchTests(unittest.TestCase):
    def test_replaces_only_the_faulty_expression(self):
        result = PATCH.patched_source(SOURCE)
        self.assertEqual(result, SOURCE.replace(PATCH.BEFORE, PATCH.AFTER))

    def test_is_idempotent(self):
        result = PATCH.patched_source(SOURCE)
        self.assertEqual(PATCH.patched_source(result), result)

    def test_rejects_unrecognized_upstream_source(self):
        with self.assertRaises(RuntimeError):
            PATCH.patched_source("class NBJW_Calib: pass\n")

    def test_rejects_duplicate_targets(self):
        with self.assertRaises(RuntimeError):
            PATCH.patched_source(SOURCE + SOURCE)

    def test_rejects_mixed_original_and_patched_source(self):
        with self.assertRaises(RuntimeError):
            PATCH.patched_source(SOURCE + SOURCE.replace(PATCH.BEFORE, PATCH.AFTER))

    def test_rejects_duplicate_patched_targets(self):
        with self.assertRaises(RuntimeError):
            PATCH.patched_source(SOURCE.replace(PATCH.BEFORE, PATCH.AFTER) * 2)

    def test_file_patch_can_be_repeated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / PATCH.RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_text(SOURCE, encoding="utf-8")
            self.assertTrue(PATCH.patch_calibration(root))
            self.assertFalse(PATCH.patch_calibration(root))
            self.assertIn(PATCH.AFTER, target.read_text(encoding="utf-8"))

    def test_missing_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                PATCH.patch_calibration(Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_invalid_syntax_leaves_original_file_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / PATCH.RELATIVE_PATH
            target.parent.mkdir(parents=True)
            invalid = SOURCE + "invalid syntax !\n"
            target.write_text(invalid, encoding="utf-8")
            with self.assertRaises(SyntaxError):
                PATCH.patch_calibration(root)
            self.assertEqual(target.read_text(encoding="utf-8"), invalid)

    def test_dockerfile_patches_after_preloading_weights(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        invocation = "python /opt/prime/patch_calibration.py --root /opt/sn-gamestate"
        self.assertIn(invocation, dockerfile)
        self.assertLess(dockerfile.index("RUN python /opt/prime/preload_models.py"), dockerfile.index(invocation))
        self.assertLess(dockerfile.index("COPY patch_calibration.py"), dockerfile.index(invocation))

    def test_empty_tracker_source_is_patched_idempotently(self):
        result = PATCH.patched_tracker_source(TRACKER_SOURCE)
        self.assertEqual(result, TRACKER_SOURCE.replace(PATCH.TRACKER_BEFORE, PATCH.TRACKER_AFTER))
        self.assertEqual(PATCH.patched_tracker_source(result), result)

    def test_empty_tracker_patch_rejects_unrecognized_source(self):
        with self.assertRaises(RuntimeError):
            PATCH.patched_tracker_source("def load(): return None\n")

    def test_empty_tracker_file_is_patched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / PATCH.TRACKER_PATH
            target.parent.mkdir(parents=True)
            target.write_text(TRACKER_SOURCE, encoding="utf-8")
            self.assertTrue(PATCH.patch_tracker_state(root))
            self.assertFalse(PATCH.patch_tracker_state(root))


class CalibrationPandasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import pandas as pd
        except ImportError:
            raise unittest.SkipTest("Ejecute en la imagen GameState para usar su pandas instalado")
        cls.pandas = pd

    def test_selects_first_row_without_relabeling_frames(self):
        namespace = {}
        exec(PATCH.patched_source(SOURCE), namespace)
        calibration = namespace["NBJW_Calib"]()
        first, second = {"frame": "first"}, {"frame": "second"}
        for labels in ([0, 1], [1, 2], [42, 0], [2698, 2699], ["frame-a", "frame-b"]):
            with self.subTest(labels=labels):
                metadata = self.pandas.DataFrame({"keypoints": [first, second]}, index=labels)
                self.assertIs(calibration.process(None, None, metadata), first)
                self.assertEqual(metadata.index.tolist(), list(labels))

    def test_original_failure_is_reproduced(self):
        namespace = {}
        exec(SOURCE, namespace)
        metadata = self.pandas.DataFrame({"keypoints": [{"frame": 42}]}, index=[42])
        with self.assertRaises(KeyError):
            namespace["NBJW_Calib"]().process(None, None, metadata)

    def test_patch_matches_installed_upstream_method(self):
        root = os.getenv("GAMESTATE_SOURCE_ROOT")
        if not root:
            self.skipTest("GAMESTATE_SOURCE_ROOT solo se configura en la prueba de la imagen")
        source = (Path(root) / PATCH.RELATIVE_PATH).read_text(encoding="utf-8")
        tree = ast.parse(PATCH.patched_source(source))
        calibration = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NBJW_Calib")
        process = next(node for node in calibration.body if isinstance(node, ast.FunctionDef) and node.name == "process")
        assignment = process.body[0]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual(assignment.targets[0].id, "predictions")
        expression = ast.Expression(body=assignment.value)
        metadata = self.pandas.DataFrame({"keypoints": [{"observed": True}]}, index=[42])
        result = eval(compile(expression, "upstream-keypoints", "eval"), {"metadatas": metadata})
        self.assertEqual(result, {"observed": True})

    def test_empty_tracker_retains_schema_without_fabricating_detections(self):
        namespace = {"pd": self.pandas}
        exec(PATCH.patched_tracker_source(TRACKER_SOURCE), namespace)
        detections = namespace["load"]()
        self.assertTrue(detections.empty)
        self.assertEqual(detections.columns.tolist(), ["video_id", "image_id"])

    def test_empty_result_passes_the_installed_tracker_update_method(self):
        if not os.getenv("GAMESTATE_SOURCE_ROOT"):
            self.skipTest("Esta regresión requiere el checkout de la imagen")
        package = importlib.util.find_spec("tracklab")
        path = Path(next(iter(package.submodule_search_locations))) / PATCH.TRACKER_PATH
        tree = ast.parse(PATCH.patched_tracker_source(path.read_text(encoding="utf-8")))
        tracker = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TrackerState")
        load = next(node for node in tracker.body if isinstance(node, ast.FunctionDef) and node.name == "load")
        initial = next(node for node in load.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "video_detections")
        empty = eval(compile(ast.Expression(initial.value), "tracker-load", "eval"), {"pd": self.pandas})
        self.assertTrue(empty.empty)
        update = next(node for node in tracker.body if isinstance(node, ast.FunctionDef) and node.name == "update")
        namespace = {"pd": self.pandas}
        exec(compile(ast.Module(body=[update], type_ignores=[]), "tracker-update", "exec"), namespace)
        image = self.pandas.DataFrame({"video_id": [0], "frame": [0]})
        state = SimpleNamespace(detections_pred=None, image_pred=None, video_id=0)
        namespace["update"](state, empty, image)
        namespace["update"](state, empty, image)
        self.assertTrue(state.detections_pred.empty)
        # El mismo guardado conserva detecciones reales posteriores.
        real = self.pandas.DataFrame({"video_id": [0], "image_id": [0], "track_id": [9]})
        namespace["update"](state, real, image)
        self.assertEqual(state.detections_pred["track_id"].tolist(), [9])


if __name__ == "__main__":
    unittest.main(verbosity=2)
