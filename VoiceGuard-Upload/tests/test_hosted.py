import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hosted_app import app, _analysis_slot
from detector import DetectorUnavailable


class HostedRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_site_and_audio_assets_share_origin(self):
        for path in ('/', '/app.js', '/samples/neural-voice.wav'):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/health').json['processingLocation'], 'server')

    def test_upload_returns_detector_result(self):
        expected = {'label': 'Likely AI-generated voice', 'score': 92}
        with patch('hosted_app.analyze', return_value=expected) as analyze:
            response = self.client.post('/api/analyze', data=b'wav-bytes', content_type='audio/wav')
            self.assertEqual(response.json, expected)
            analyze.assert_called_once_with(b'wav-bytes')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_model_failure_is_safe_and_slot_is_released(self):
        with patch('hosted_app.analyze', side_effect=DetectorUnavailable('private path')):
            with self.assertLogs(level='ERROR'):
                response = self.client.post('/api/analyze', data=b'wav')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private path', response.get_data(as_text=True))
        self.assertTrue(_analysis_slot.acquire(blocking=False))
        _analysis_slot.release()

    def test_bad_empty_and_oversized_audio(self):
        self.assertEqual(self.client.post('/api/analyze', data=b'').status_code, 400)
        self.assertEqual(self.client.post('/api/analyze', data=b'bad').status_code, 400)
        with patch.dict(app.config, {'MAX_CONTENT_LENGTH': 10}):
            self.assertEqual(self.client.post('/api/analyze', data=b'x'*11).status_code, 413)

    def test_busy_service_returns_retry_response(self):
        _analysis_slot.acquire()
        try:
            response = self.client.post('/api/analyze', data=b'wav')
            self.assertEqual(response.status_code, 429)
        finally:
            _analysis_slot.release()


if __name__ == '__main__':
    unittest.main()
