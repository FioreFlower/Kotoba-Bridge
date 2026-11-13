import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from overlay_settings import opacity,save_opacity,load_opacity
from core import ReaderError
from study_ui import Subtitle

class OpacityTests(unittest.TestCase):
    def test_save_reload_and_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'overlay.json'
            self.assertEqual(load_opacity(p),85)
            for value in [0,35,85,100]:save_opacity(value,p);self.assertEqual(load_opacity(p),value)
            p.write_text('{"version":1,"background_opacity":25,"key":"fixture"}',encoding='utf-8')
            with self.assertRaises(ReaderError):load_opacity(p)
    def test_bad_values(self):
        for value in [True,-1,101,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):opacity(value)
    def test_background_only_alpha(self):
        subtitle=Subtitle.__new__(Subtitle);subtitle.window=Mock();subtitle.background=Mock()
        subtitle.separate_background=True;subtitle._queue_sync=Mock()
        subtitle.set_background_opacity(25)
        subtitle.window.attributes.assert_called_once_with('-alpha',1.0)
        subtitle.background.attributes.assert_called_once_with('-alpha',0.25)
    def test_unsupported_never_dim_text(self):
        subtitle=Subtitle.__new__(Subtitle);subtitle.window=Mock();subtitle.separate_background=False
        self.assertFalse(subtitle.set_background_opacity(0))
        subtitle.window.attributes.assert_called_once_with('-alpha',1.0)
