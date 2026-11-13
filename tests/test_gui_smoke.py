"""Widget construction checks only: not game, capture, DPI or visual acceptance tests."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

@unittest.skipUnless(sys.platform=='win32' or os.environ.get('DISPLAY'),'No GUI display in this Linux environment')
class WidgetSmokeTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.setting_patch=patch('app.settings_path',return_value=Path(self.folder.name)/'settings.json')
        self.setting_patch.start()
        from app import App
        self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
        self.app.subtitle.window.withdraw()
        self.root.update_idletasks()
    def tearDown(self):
        self.app.close();self.setting_patch.stop();self.folder.cleanup()
    def test_source_and_translation_separated(self):
        self.app.display('こんにちは。\n\n안녕하세요.')
        self.assertEqual(self.app.subtitle.text.get('1.0','end-1c'),'こんにちは。')
        self.assertEqual(self.app.subtitle.translation_text.get('1.0','end-1c'),'안녕하세요.')
    def test_learning_opens_newest_dialogue(self):
        from study_ui import StudyWindow
        self.app.study.record('こんにちは。','안녕하세요.')
        study=StudyWindow(self.app);self.app.study_window=study
        self.assertEqual(study.text.get('1.0','end-1c'),'こんにちは。')
        self.assertEqual(study.translation_text.get('1.0','end-1c'),'안녕하세요.')
        study.window.destroy();self.app.study_window=None
