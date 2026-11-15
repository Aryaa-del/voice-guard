"""Voice Guard: an offline, educational audio analysis web application."""
import io
import json
import math
import random
import statistics
import struct
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from detector import classify, status as model_status, DetectorUnavailable

ROOT = Path(__file__).parent
MAX_BYTES = 20 * 1024 * 1024


def read_audio(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                            audio.getframerate(), audio.getnframes())
            if width != 2 or channels not in (1, 2):
                raise ValueError('Use a 16-bit PCM WAV file (mono or stereo).')
            if not 8000 <= rate <= 96000:
                raise ValueError('Sample rate must be between 8 kHz and 96 kHz.')
            duration = frames / rate
            if not 1 <= duration <= 60:
                raise ValueError('Please use an audio clip between 1 and 60 seconds.')
            raw = audio.readframes(frames)
            if len(raw) != frames * channels * width:
                raise ValueError('This WAV file is incomplete. Please export it again.')
            values = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
            samples = [sum(values[i:i + channels]) / (32768 * channels)
                       for i in range(0, len(values), channels)]
            return samples, rate, duration, channels, rate
    except (wave.Error, EOFError, struct.error) as exc:
        raise ValueError('Cannot read this file. Upload a valid 16-bit PCM WAV file.') from exc


def analyze(data):
    samples, rate, duration, channels, original_rate = read_audio(data)
    size = max(1, int(rate * 0.025))
    energy = [math.sqrt(sum(x * x for x in samples[i:i + size]) /
                        len(samples[i:i + size])) for i in range(0, len(samples), size)]
    rms = math.sqrt(sum(x*x for x in samples) / len(samples))
    if rms < 0.003:
        raise ValueError('Audio is too quiet to analyze. Record again closer to the microphone.')
    threshold = max(0.008, max(energy) * 0.08)
    active = [e for e in energy if e > threshold]
    variation = statistics.pstdev(active) / statistics.mean(active) if active else 0
    pause = sum(e <= threshold for e in energy) / len(energy)
    crossings = sum(a * b < 0 for a, b in zip(samples, samples[1:])) / len(samples)
    clipping = sum(abs(x) > 0.985 for x in samples) / len(samples)
    poor_quality = clipping > 0.015 or rms < 0.012
    prediction = classify(samples, rate, duration, poor_quality)
    return {
        **prediction,
        'duration': round(duration, 2), 'sampleRate': original_rate, 'channels': channels,
        'metrics': {'variation': round(variation, 3), 'pausePercent': round(pause * 100, 1),
                    'clippingPercent': round(clipping * 100, 2),
                    'zeroCrossingRate': round(crossings, 4), 'rms': round(rms, 4)},
    }


def demo_audio(kind):
    """Generate test tones, intentionally not real or cloned speech."""
    rate, duration = 16000, 6
    rng = random.Random(7)
    frames = bytearray()
    for i in range(rate * duration):
        t = i / rate
        if kind == 'varied':
            envelope = (0.25 + 0.65 * math.sin(t * 3.7) ** 2) if t % 1.4 < 1.05 else 0
            frequency = 155 + 35 * math.sin(t * 4)
        else:
            envelope, frequency = 0.6, 180
        value = envelope * (0.55 * math.sin(2 * math.pi * frequency * t) +
                            0.18 * math.sin(4 * math.pi * frequency * t))
        value += rng.uniform(-0.006, 0.006)
        frames.extend(struct.pack('<h', int(value * 32767)))
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(frames)
    return output.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def send_data(self, status, data, content_type='application/json'):
        body = json.dumps(data).encode() if content_type == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/health':
            return self.send_data(200, {'status': 'ok', **model_status()})
        if parsed.path == '/api/demo':
            kind = parse_qs(parsed.query).get('kind', ['varied'])[0]
            return self.send_data(200, demo_audio(kind), 'audio/wav')
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/analyze':
            return self.send_data(404, {'error': 'Endpoint not found.'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= MAX_BYTES:
                return self.send_data(413, {'error': 'Upload a WAV file smaller than 20 MB.'})
            self.connection.settimeout(30)
            result = analyze(self.rfile.read(length))
            return self.send_data(200, result)
        except ValueError as exc:
            return self.send_data(400, {'error': str(exc)})
        except DetectorUnavailable as exc:
            return self.send_data(503, {'error': str(exc)})
        except (OSError, TimeoutError):
            return self.send_data(408, {'error': 'Upload timed out. Please try again.'})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Start the Voice Guard college demo.')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Voice Guard is running at http://localhost:{args.port}\nPress Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nVoice Guard stopped.')
    finally:
        server.server_close()
