import unittest
from unittest.mock import MagicMock, patch
from core import Region, ReaderError
from live_region import RegionEditSession, drag_region, parse_region, validate_region, real_monitors, ensure_physical_dpi


class LiveGeometryTests(unittest.TestCase):
    def setUp(self):
        self.monitors = [{'left': -1920, 'top': -200, 'width': 1920, 'height': 1080},
                         {'left': 0, 'top': 0, 'width': 2560, 'height': 1440}]
        self.start = Region(100, 200, 500, 120)

    def test_move_uses_absolute_physical_delta(self):
        self.assertEqual(drag_region(self.start, 150, -50, 'move', self.monitors), Region(250, 150, 500, 120))

    def test_move_to_negative_monitor_without_scaling(self):
        self.assertEqual(drag_region(self.start, -1500, -250, 'move', self.monitors), Region(-1400, -50, 500, 120))

    def test_each_corner_keeps_opposite_corner_fixed(self):
        expected = {'nw': Region(110, 220, 490, 100), 'ne': Region(100, 220, 510, 100),
                    'sw': Region(110, 200, 490, 140), 'se': Region(100, 200, 510, 140)}
        for corner, result in expected.items():
            with self.subTest(corner=corner):
                self.assertEqual(drag_region(self.start, 10, 20, corner, self.monitors), result)

    def test_crossed_corner_stops_at_minimum(self):
        self.assertEqual(drag_region(self.start, 1000, 1000, 'nw', self.monitors), Region(580, 300, 20, 20))

    def test_outside_gap_and_spanning_monitors_rejected(self):
        for region in [Region(-10, 100, 30, 40), Region(-100, -210, 50, 30), Region(2550, 0, 20, 20)]:
            with self.subTest(region=region), self.assertRaises(ReaderError):
                validate_region(region, self.monitors)

    def test_monitor_edge_exact_fit_valid(self):
        self.assertEqual(validate_region(Region(-1920, -200, 1920, 1080), self.monitors), Region(-1920, -200, 1920, 1080))

    def test_invalid_numeric_input_never_mutates_draft(self):
        draft = RegionEditSession(self.start, self.monitors)
        for values in [('1.5','0','40','40'), ('x','0','40','40'), ('0','0','19','40'), ('0','0','40'), ('0','0','4000','40')]:
            with self.assertRaises(ReaderError):
                draft.update(parse_region(values, self.monitors))
            self.assertEqual(draft.current, self.start)

    def test_cancel_returns_original_after_multiple_edits(self):
        draft = RegionEditSession(self.start, self.monitors)
        draft.update(Region(300, 400, 50, 50))
        self.assertEqual(draft.finish(False), self.start)
        with self.assertRaises(ReaderError):
            draft.finish(True)

    def test_confirm_returns_latest_once(self):
        draft = RegionEditSession(self.start, self.monitors)
        selected = parse_region(('-1500','-100','600','100'), self.monitors)
        draft.update(selected)
        self.assertEqual(draft.finish(True), selected)
        with self.assertRaises(ReaderError):
            draft.update(self.start)

    def test_monitors_are_copied_and_bad_input_rejected(self):
        draft = RegionEditSession(self.start, self.monitors)
        self.monitors[1]['width'] = 1
        self.assertEqual(draft.monitors[1]['width'], 2560)
        for monitors in [[], [{'left': False, 'top':0, 'width':100, 'height':100}]]:
            with self.assertRaises(ReaderError): real_monitors(monitors)

    def test_maximum_size_clamped_for_resize(self):
        monitors = [{'left':0,'top':0,'width':7680,'height':4320}]
        self.assertEqual(drag_region(self.start, 10000, 10000, 'se', monitors), Region(100,200,3840,2160))

    def test_boolean_and_fractional_coordinates_rejected(self):
        for region in [Region(True,0,20,20),Region(0.5,0,20,20)]:
            with self.assertRaises(ReaderError): validate_region(region,self.monitors)
        with self.assertRaises(ReaderError): drag_region(self.start,True,0,'move',self.monitors)


class DpiGuardTests(unittest.TestCase):
    def test_per_monitor_context_required(self):
        for awareness in (-1, 0, 1, 2):
            api = MagicMock()
            api.GetAwarenessFromDpiAwarenessContext.return_value = awareness
            with self.subTest(awareness=awareness), patch('live_region.sys.platform', 'win32'), patch('ctypes.WinDLL', create=True, return_value=api):
                if awareness == 2:
                    self.assertTrue(ensure_physical_dpi())
                else:
                    with self.assertRaises(ReaderError): ensure_physical_dpi()
            api.SetProcessDpiAwareness.assert_not_called()

    def test_unavailable_windows_api_fails_closed(self):
        with patch('live_region.sys.platform', 'win32'), patch('ctypes.WinDLL', create=True, side_effect=OSError()):
            with self.assertRaises(ReaderError): ensure_physical_dpi()

    def test_non_windows_rejected_without_native_api(self):
        with patch('live_region.sys.platform', 'linux'), patch('ctypes.WinDLL', create=True) as native:
            with self.assertRaises(ReaderError): ensure_physical_dpi()
            native.assert_not_called()


if __name__ == '__main__':
    unittest.main()
