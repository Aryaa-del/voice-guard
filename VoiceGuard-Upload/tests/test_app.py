import io
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
import wave
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Handler, ThreadingHTTPServer, analyze, demo_audio
from detector import summarize_scores, DetectorUnavailable


class AudioTests(unittest.TestCase):
    def test_model_decisions_and_abstention(self):
        self.assertEqual(summarize_scores([0.95, 0.90], 6)['tone'], 'warning')
        self.assertEqual(summarize_scores([0.05, 0.10], 6)['tone'], 'success')
        self.assertEqual(summarize_scores([0.05] * 9 + [0.95], 10)['tone'], 'success')
        self.assertEqual(summarize_scores([0.99] * 4 + [0.01], 5)['tone'], 'warning')
        for scores, duration, poor in [([0.5], 6, False), ([0.05, 0.95], 6, False),
                                       ([0.99], 1.5, False), ([0.99], 6, True)]:
            self.assertEqual(summarize_scores(scores, duration, poor)['label'], 'Inconclusive')
        with self.assertRaises(DetectorUnavailable):
            summarize_scores([float('nan')], 6)

    def test_prediction_comes_from_model(self):
        prediction = summarize_scores([0.95], 6)
        with patch('app.classify', return_value=prediction) as classifier:
            result = analyze(demo_audio('varied'))
            self.assertEqual(result['label'], 'Likely AI-generated voice')
            self.assertEqual(result['score'], 95)
            classifier.assert_called_once()

    def test_unavailable_model_never_falls_back_to_human(self):
        with patch('app.classify', side_effect=DetectorUnavailable('Model unavailable')):
            with self.assertRaises(DetectorUnavailable):
                analyze(demo_audio('varied'))

    def test_invalid_file(self):
        with self.assertRaises(ValueError):
            analyze(b'not audio')

    def test_silent_file(self):
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\0' * 64000)
        with self.assertRaisesRegex(ValueError, 'too quiet'):
            analyze(output.getvalue())

    def test_http_flow(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base) as response:
                self.assertIn(b'VoiceGuard', response.read())
            with urllib.request.urlopen(base + '/api/demo?kind=varied') as response:
                data = response.read()
            request = urllib.request.Request(base + '/api/analyze', data=data, headers={'Content-Type': 'audio/wav'})
            with patch('app.classify', return_value=summarize_scores([0.9], 6)):
                with urllib.request.urlopen(request) as response:
                    result = json.load(response)
                    self.assertEqual(result['duration'], 6.0)
                    self.assertEqual(result['label'], 'Likely AI-generated voice')
            with patch('app.classify', side_effect=DetectorUnavailable('Model missing')):
                with self.assertRaises(urllib.error.HTTPError) as missing:
                    urllib.request.urlopen(request)
                self.assertEqual(missing.exception.code, 503)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(base + '/api/analyze', data=b'bad'))
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
