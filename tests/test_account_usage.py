import unittest
from unittest.mock import Mock,patch
from account_usage import format_usage
from app import App

class AccountUsageTests(unittest.TestCase):
 def test_actual_counts_limits_and_timestamp(self):
  value=format_usage(dict(character_count=12345,character_limit=1000000000000,api_key_character_count=12,checked_at='2026-11-13T10:00:00Z'))
  self.assertIn('12,345자',value);self.assertIn('설정 안 됨',value);self.assertIn('API 미제공',value);self.assertIn('몇 분',value);self.assertIn('조회 ',value)
 def test_missing_counts_never_fabricated(self):
  with self.assertRaises(KeyError):format_usage(dict(checked_at='2026-11-13T10:00:00Z'))
 def test_demo_and_local_never_query_or_load_key(self):
  for demo,local in [(True,False),(False,True)]:
   a=App.__new__(App);a.demo=Mock();a.demo.get.return_value=demo;a.is_local=lambda:local
   a.account_usage=Mock();a.bridge=Mock();a.configure_credentials=Mock()
   a.refresh_usage();a.bridge.call.assert_not_called();a.configure_credentials.assert_not_called()
 def test_gui_rate_limit_keeps_timestamp(self):
  a=App.__new__(App);a.demo=Mock();a.demo.get.return_value=False;a.is_local=lambda:False
  a.usage_busy=False;a.usage_attempt=100;a.account_usage=Mock();a.bridge=Mock()
  with patch('app.time.monotonic',return_value=110):a.refresh_usage()
  a.bridge.call.assert_not_called();a.account_usage.set.assert_not_called()
