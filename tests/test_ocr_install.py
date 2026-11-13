import unittest
from urllib.parse import urlsplit
from unittest.mock import patch
import ocr_install


class OcrInstallTests(unittest.TestCase):
    def test_guidance_is_offline_and_never_launches_anything(self):
        with patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('webbrowser.open', side_effect=AssertionError('browser forbidden')):
            guide = ocr_install.get_install_guide()
            text = ocr_install.format_install_guide()
        self.assertEqual(len(guide['steps']), 6)
        self.assertIn('jpn', text)
        self.assertIn('제3자', text)
        self.assertIn('기존 폴더', text)
        self.assertIn('보증이 아닙니다', text)

    def test_display_links_use_reviewed_https_sources(self):
        allowed = {'tesseract-ocr.github.io', 'github.com'}
        for _, url in ocr_install.get_install_guide()['links']:
            parsed = urlsplit(url)
            self.assertEqual(parsed.scheme, 'https')
            self.assertIn(parsed.hostname, allowed)
            self.assertIsNone(parsed.username)
            self.assertFalse(parsed.query)

    def test_callers_cannot_mutate_future_guidance(self):
        guide = ocr_install.get_install_guide()
        guide['steps'].clear()
        guide['links'].append(('bad', 'http://invalid'))
        fresh = ocr_install.get_install_guide()
        self.assertEqual(len(fresh['steps']), 6)
        self.assertEqual(len(fresh['links']), 4)

    def test_winget_is_review_information_not_install_command(self):
        text = ocr_install.format_install_guide()
        self.assertIn(ocr_install.PACKAGE_ID, text)
        self.assertIn('불일치', text)
        for unsafe in ('winget install', '--ignore-security-hash', '--silent'):
            self.assertNotIn(unsafe, text)


if __name__ == '__main__':
    unittest.main()
