"""Run real-model smoke tests; these do not establish benchmark accuracy."""
import json
import time
from pathlib import Path

from app import analyze
from detector import MODEL_ID, MODEL_REVISION

root = Path(__file__).parent
report = {'model': MODEL_ID, 'revision': MODEL_REVISION,
          'scope': 'Bundled example smoke tests only; not a held-out accuracy benchmark.',
          'samples': []}
for name, known_source in [('ai-voice.wav', 'synthetic Windows TTS'),
                           ('everyday-voice.wav', 'synthetic Windows TTS'),
                           ('neural-voice.wav', 'published Kokoro neural TTS'),
                           ('human-speech.wav', 'public human speech sample')]:
    path = root / 'static' / 'samples' / name
    if not path.exists():
        raise SystemExit(f'Missing sample: {path}. Complete setup first.')
    started = time.monotonic()
    result = analyze(path.read_bytes())
    entry = {'file': name, 'source': known_source, 'prediction': result['label'],
             'aiScore': result['score'], 'humanScore': result['humanScore'],
             'segmentScores': result['segmentScores'], 'seconds': round(time.monotonic() - started, 2)}
    entry['matchesKnownSource'] = (result['tone'] == ('success' if name == 'human-speech.wav' else 'warning'))
    report['samples'].append(entry)
    print(json.dumps(entry), flush=True)
    if name == 'everyday-voice.wav':
        repeated = analyze(bytes(path.read_bytes()))
        assert repeated['score'] == result['score'], 'Non-deterministic sample result'
report['filenameIndependent'] = True
(root / 'MODEL_TEST_REPORT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Saved MODEL_TEST_REPORT.json. These results are examples, not overall accuracy.')
