import unittest
from core import ReaderError
from input_sources import CandidateSession, source_text

class SourceTests(unittest.TestCase):
    def test_no_consent_fails_closed(self):
        s=CandidateSession()
        with self.assertRaises(ReaderError):s.start()
        self.assertFalse(s.active)
    def test_invalid_and_bounded_text(self):
        for value in ['', 'a'*2001, '\x00secret', None]:
            with self.assertRaises(ReaderError):source_text(value)
        self.assertEqual(source_text('  こんにちは。\n '),'こんにちは。')
    def test_stale_after_stop_and_restart(self):
        s=CandidateSession();old=s.start(True);s.ingest(old,'line','こんにちは。');s.stop()
        new=s.start(True)
        self.assertFalse(s.ingest(old,'line','古い文'))
        self.assertEqual(s.candidates,{})
        self.assertTrue(s.ingest(new,'line','新しい文'))
    def test_never_auto_select(self):
        s=CandidateSession();g=s.start(True);s.ingest(g,'name','葵');s.ingest(g,'line','一緒に帰りましょう。')
        self.assertEqual(s.ranked()[0].identifier,'line');self.assertIsNone(s.selected)
        self.assertEqual(s.select('name'),'葵')
        self.assertIn('미확인',s.reasons(s.candidates['name']))
    def test_repeated_stream_counts_without_growing_history(self):
        s=CandidateSession();g=s.start(True)
        for _ in range(4):s.ingest(g,'line','同じ文章です。')
        self.assertEqual(len(s.candidates),1);self.assertEqual(s.candidates['line'].repeats,3)
    def test_stream_limit_clears(self):
        s=CandidateSession();g=s.start(True)
        for i in range(32):s.ingest(g,str(i),'文')
        with self.assertRaises(ReaderError):s.ingest(g,'overflow','文')
        self.assertFalse(s.active);self.assertEqual(s.candidates,{})
    def test_event_limit_clears(self):
        s=CandidateSession();g=s.start(True)
        for _ in range(1000):s.ingest(g,'line','文')
        with self.assertRaises(ReaderError):s.ingest(g,'line','文')
        self.assertFalse(s.active)
    def test_bad_identifier_does_not_mutate(self):
        s=CandidateSession();g=s.start(True)
        with self.assertRaises(ReaderError):s.ingest(g,'../private','文')
        self.assertEqual(s.candidates,{})
    def test_selection_missing_rejected(self):
        with self.assertRaises(ReaderError):CandidateSession().select('line')
