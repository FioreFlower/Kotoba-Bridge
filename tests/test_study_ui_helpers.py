import tkinter as tk
from types import SimpleNamespace
import unittest
from study import StudyStore
from study_ui import StudyWindow, source_selection, style_matches


class SelectedText:
    def __init__(self,value):self.value=value
    def get(self,*args):
        if self.value is None:raise tk.TclError('no selection')
        return self.value


class StudyUIHelperTests(unittest.TestCase):
    def test_click_through_requires_all_flags(self):
        self.assertFalse(style_matches(0x20,True))
        self.assertFalse(style_matches(0x08000000,True))
        self.assertTrue(style_matches(0x20|0x08000000|0x80000,True))
        self.assertFalse(style_matches(0x20,False))
        self.assertTrue(style_matches(0x80000,False))

    def test_no_selection_is_empty(self):
        self.assertEqual(source_selection(SelectedText(None)), '')

    def window(self,source_selection_value,overlay_source,overlay_selection):
        window=StudyWindow.__new__(StudyWindow)
        window.text=SelectedText(source_selection_value)
        window.translation_text=SelectedText('고양이')
        window.current={'source':'猫です。','translation':'고양이예요.'}
        window.app=SimpleNamespace(subtitle=SimpleNamespace(source=overlay_source,selection_text=lambda:overlay_selection))
        return window

    def test_korean_pane_does_not_supply_dictionary_query(self):
        window=self.window(None,'different','猫')
        with self.assertRaises(ValueError):window.selected()

    def test_overlay_selection_allowed_only_for_matching_dialogue(self):
        window=self.window(None,'猫です。','猫')
        self.assertEqual(window.selected(),'猫')

    def test_source_selection_takes_precedence(self):
        window=self.window('猫です。','猫です。','猫')
        self.assertEqual(window.selected(),'猫です。')
