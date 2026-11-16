import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from core import ReaderError
from overlay_placement import (Geometry, Monitor, fit_geometry, moved, resized,
                               load_placement, save_placement, preference_path,
                               apply_geometry, window_geometry, _tk_axis,
                               require_physical_coordinates)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.monitors = [Monitor(0, 0, 1920, 1080), Monitor(-1920, 0, 1920, 1080)]

    def test_negative_monitor_is_preserved(self):
        geometry = Geometry(-1600, 120, 650, 210)
        self.assertEqual(fit_geometry(geometry, self.monitors), geometry)

    def test_disconnected_monitor_recovers_to_existing_screen(self):
        geometry = Geometry(-1600, 120, 650, 210)
        recovered = fit_geometry(geometry, self.monitors[:1])
        self.assertEqual(recovered, Geometry(40, 80, 650, 210))

    def test_monitor_gap_is_not_treated_as_screen(self):
        screens = [Monitor(0, 0, 1000, 800), Monitor(2000, -1000, 1000, 800)]
        recovered = fit_geometry(Geometry(1200, 20, 400, 200), screens, preferred_index=1)
        self.assertEqual(recovered, Geometry(2040, -920, 400, 200))

    def test_partial_window_and_size_are_clamped_to_one_monitor(self):
        recovered = fit_geometry(Geometry(-100, 900, 2000, 700), self.monitors)
        self.assertEqual(recovered, Geometry(0, 380, 1920, 700))

    def test_upward_monitor_and_oversized_window(self):
        screen = Monitor(-1280, -1024, 1280, 1024)
        self.assertEqual(fit_geometry(Geometry(-1000, -1000, 3840, 2000), [screen]),
                         Geometry(-1280, -1024, 1280, 1024))

    def test_move_and_resize_boundaries(self):
        initial = Geometry(-20, 100, 650, 210)
        self.assertEqual(moved(initial, -100, 40), Geometry(-120, 140, 650, 210))
        self.assertEqual(resized(initial, -2000, -2000), Geometry(-20, 100, 240, 120))
        self.assertEqual(resized(initial, 10000, 10000), Geometry(-20, 100, 3840, 2160))

    def test_schema_and_numeric_validation(self):
        for changes in [{'x': True}, {'y': 1.5}, {'width': 0}, {'height': 5000}, {'x': 100001}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Geometry(**changes)
        for screens in [[], [{'left': 0}], [Monitor(0, 0, 1000, 800)] * 33]:
            with self.assertRaises(ValueError):
                fit_geometry(Geometry(), screens)

    def test_settings_roundtrip_only_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'data'/'overlay-placement.json'
            self.assertEqual(load_placement(path), Geometry())
            geometry = Geometry(-1800, 150, 800, 300)
            save_placement(geometry, path)
            self.assertEqual(load_placement(path), geometry)
            self.assertEqual(set(json.loads(path.read_text(encoding='utf-8'))),
                             {'version', 'x', 'y', 'width', 'height'})

    def test_malformed_settings_rejected(self):
        valid = {'version':1, 'x':0, 'y':0, 'width':650, 'height':210}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'overlay-placement.json'
            for value in [[], None, dict(valid, version=True), dict(valid, api_key='dummy'), dict(valid, x='0')]:
                path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(ReaderError):load_placement(path)
            path.write_text(' '*2049, encoding='utf-8')
            with self.assertRaises(ReaderError):load_placement(path)

    def test_atomic_save_failure_keeps_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'overlay-placement.json'
            save_placement(Geometry(), path)
            original=path.read_bytes()
            with patch('overlay_placement.os.replace', side_effect=PermissionError('locked')):
                with self.assertRaises(PermissionError):save_placement(Geometry(x=200), path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_data_folder_routing(self):
        with patch('onboarding.data_folder', return_value=Path('/portable/data')):
            self.assertEqual(preference_path(), Path('/portable/data/overlay-placement.json'))

    def test_dpi_failure_prevents_window_mutation(self):
        window=Mock()
        with patch('overlay_placement.require_physical_coordinates', side_effect=ReaderError('DPI')):
            with self.assertRaises(ReaderError):apply_geometry(window, Geometry())
        window.geometry.assert_not_called()

    def test_negative_tk_offset_is_edge_relative_conversion(self):
        self.assertEqual(_tk_axis(-100, 650, 1920), '-1370')
        self.assertEqual(_tk_axis(100, 650, 1920), '+100')

    def test_non_per_monitor_windows_dpi_fails_closed(self):
        api=Mock();api.GetAwarenessFromDpiAwarenessContext.return_value=1
        with patch('overlay_placement.sys.platform', 'win32'), patch('overlay_placement.ctypes.WinDLL', create=True, return_value=api):
            with self.assertRaises(ReaderError):require_physical_coordinates()

    def test_per_monitor_windows_dpi_is_accepted(self):
        api=Mock();api.GetAwarenessFromDpiAwarenessContext.return_value=2
        with patch('overlay_placement.sys.platform', 'win32'), patch('overlay_placement.ctypes.WinDLL', create=True, return_value=api):
            require_physical_coordinates()
