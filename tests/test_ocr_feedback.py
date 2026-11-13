import unittest
from core import Region
from ocr_feedback import spacing_candidate, preview_text, region_hint, usage_label

class FeedbackTests(unittest.TestCase):
 def test_candidate_only_single_japanese_spaces(self):
  self.assertEqual(spacing_candidate('こ ん に ち は。'),('こんにちは。',4))
  raw='東京  駅\n次の\t台詞　です。HP 100 / New Game / 第 2 話'
  self.assertEqual(spacing_candidate(raw),(raw,0))
 def test_preview_preserves_original_and_marks_candidate(self):
  raw='  東京 駅\n次の台詞。  '
  rendered=preview_text(raw)
  self.assertIn('[OCR 원본 · 공백 보존]\n'+raw,rendered)
  self.assertIn('자동 적용 안 함',rendered)
  self.assertEqual(raw,'  東京 駅\n次の台詞。  ')
 def test_large_hint_advisory_narrow_dimensions_preserved(self):
  monitor=dict(width=1920,height=1080)
  self.assertIn('넓은 영역',region_hint(Region(0,0,1279,725),monitor))
  self.assertIn('900×70',region_hint(Region(0,0,900,70),monitor))
  self.assertNotIn('넓은 영역',region_hint(Region(0,0,900,70),monitor))
 def test_usage_modes_never_describe_demo_as_paid(self):
  demo=usage_label(13,100,demo=True,local=True)
  self.assertIn('모의 사용량 13/100',demo);self.assertIn('API 과금 없음',demo);self.assertIn('외부 전송 없음',demo)
  self.assertIn('로컬 번역',usage_label(13,100,demo=False,local=True))
  self.assertIn('실제 청구액 아님',usage_label(13,100,demo=False))
