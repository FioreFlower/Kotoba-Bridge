import tempfile
import unittest
from pathlib import Path
from study import StudyStore, dictionary_url

class StudyTests(unittest.TestCase):
    def test_roundtrip_and_delete(self):
        a=StudyStore();a.record('こんにちは。','안녕하세요.');a.save('こんにちは','こんにちは。','안녕하세요.')
        a.save('こんにちは','こんにちは。','안녕하세요.')
        self.assertEqual(len(a.cards),1)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'cards.json';a.export(p)
            self.assertNotIn('history',p.read_text(encoding='utf-8'))
            b=StudyStore();b.load(p);self.assertEqual(a.cards,b.cards)
            b.cards.clear();self.assertTrue(p.exists())
    def test_invalid_import_is_atomic(self):
        a=StudyStore();a.save('猫','猫','고양이')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.json';p.write_text('{"version":1,"cards":[{"term":5}]}', encoding='utf-8')
            with self.assertRaises(ValueError):a.load(p)
            self.assertEqual(a.cards[0]['term'],'猫')
    def test_history_bound(self):
        a=StudyStore()
        for i in range(510):a.record(str(i),'x')
        self.assertEqual(len(a.history),500)
    def test_url_escapes(self):
        u=dictionary_url('猫/#?')
        self.assertEqual(u,'https://ja.wiktionary.org/wiki/%E7%8C%AB%2F%23%3F')
        with self.assertRaises(ValueError):dictionary_url('x'*101)
