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

class StudyValidationTests(unittest.TestCase):
    def test_invalid_documents_preserve_cards(self):
        import json
        valid = {'term':'猫', 'source':'猫です。', 'translation':'고양이예요.'}
        variants = [None, [], 'text', {'version':True,'cards':[]}, {'version':1,'cards':[],'key':'secret'}]
        for field, bad in [('term',''), ('term',' '*3), ('term','a'*2001), ('source',''), ('source','a'*2001), ('translation',' '), ('translation',8), ('translation','a'*20001)]:
            variants.append({'version':1,'cards':[dict(valid, **{field:bad})]})
        a=StudyStore();a.save('犬','犬','개')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'cards.json'
            for data in variants:
                with self.subTest(data_type=type(data).__name__):
                    p.write_text(json.dumps(data),encoding='utf-8')
                    with self.assertRaises(ValueError):a.load(p)
                    self.assertEqual(a.cards[0]['term'],'犬')

    def test_invalid_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.json';p.write_bytes(b'\xff')
            with self.assertRaises(ValueError):StudyStore().load(p)

    def test_failed_replace_preserves_original_and_cleans_temporary(self):
        from unittest.mock import patch
        a=StudyStore();a.save('猫','猫','고양이')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'cards.json';p.write_bytes(b'old file')
            with patch('study.os.replace',side_effect=PermissionError('locked')):
                with self.assertRaises(PermissionError):a.export(p)
            self.assertEqual(p.read_bytes(),b'old file')
            self.assertEqual(list(Path(folder).iterdir()),[p])

    def test_export_limit_preserves_original(self):
        from unittest.mock import patch
        a=StudyStore();a.save('猫','猫','고양이')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'cards.json';p.write_bytes(b'old file')
            with patch('study.MAX_FILE_BYTES',20):
                with self.assertRaises(ValueError):a.export(p)
            self.assertEqual(p.read_bytes(),b'old file')

    def test_save_validation_applies_before_mutation(self):
        a=StudyStore()
        for values in [(None,'猫','고양이'),('猫',' ','고양이'),('猫','猫','')]:
            with self.assertRaises(ValueError):a.save(*values)
        self.assertEqual(a.cards,[])
