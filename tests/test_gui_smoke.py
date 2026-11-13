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
        self.data_patch=patch('onboarding.data_folder',return_value=Path(self.folder.name));self.data_patch.start()
        from app import App
        self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
        self.app.subtitle.window.withdraw()
        self.root.update_idletasks()
    def tearDown(self):
        self.app.close();self.setting_patch.stop();self.data_patch.stop();self.folder.cleanup()
    def test_hook_window_never_launches_implicitly(self):
        with patch('hook_cli.subprocess.Popen') as launch:
            self.app.open_hook();window=self.app.input_window
            self.assertFalse(window.consent.get());self.assertIsNone(window.client.process)
            launch.assert_not_called();window.close();self.assertIsNone(self.app.input_window)

    def test_borderless_subtitle(self):
        self.assertTrue(self.app.subtitle.window.overrideredirect())

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

    def test_explicit_input_window_constructs_without_capture(self):
        self.app.open_input()
        window=self.app.input_window
        self.assertFalse(window.session.active)
        window.preview_consent.set(True);window.begin()
        self.assertEqual(len(window.session.candidates),3)
        self.assertIsNone(window.session.selected)
        window.close()
        self.assertIsNone(self.app.input_window)
        self.assertFalse(self.app.running)

    def test_masked_key_not_refilled(self):
        self.assertEqual(self.app.key.cget('show'),'•')
        self.assertEqual(self.app.key.get(),'')

    def test_background_opacity_keeps_text_opaque(self):
        sub=self.app.subtitle
        sub.window.deiconify();self.root.update_idletasks()
        sub.set_background_opacity(20)
        self.root.update_idletasks()
        self.assertEqual(float(sub.window.attributes('-alpha')),1.0)
        if sys.platform=='win32':
            self.assertTrue(sub.separate_background)
            self.assertAlmostEqual(float(sub.background.attributes('-alpha')),0.2,places=2)
            self.assertTrue(sub.mode(True))
            sub.show('明日\n\n내일');sub.text.tag_add('sel','1.0','1.2')
            self.assertEqual(sub.selection_text(),'明日')
            self.assertTrue(sub.mode(False))
        sub.restore();self.assertEqual(sub.background_opacity,85)
        self.assertEqual(float(sub.window.attributes('-alpha')),1.0)

    def test_local_model_setup_never_downloads_implicitly(self):
        with patch('local_ui.install_model') as download:
            self.app.open_local();window=self.app.local_window
            self.assertFalse(window.accept.get());window.model_id.set('qwen3-4b')
            self.assertIn('2,497,280,256',window.details.get())
            self.assertFalse(window.accept.get());download.assert_not_called()
            window.close();self.assertIsNone(self.app.local_window)
