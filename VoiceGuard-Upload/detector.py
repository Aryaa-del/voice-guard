"""Local neural voice classification. No audio is sent to an online service."""
import math
import os
import threading
from pathlib import Path

MODEL_ID = 'Bgeorge/deepfake-audio-detector-wav2vec2'
MODEL_REVISION = '7bdcadcb5d47522c0237ef95a97702761fc05baf'
WINDOW_SECONDS = 1
MAX_SEGMENTS = 10
# The author's training-data section and quickstart specify REAL=0, FAKE=1.
# config.json retains the opposite mapping inherited from the base checkpoint.
# Use documented training semantics, not the stale descriptive config labels.
CLASS_LABELS = {0: 'real', 1: 'fake'}
MODEL_PATH = Path(__file__).parent / 'models' / 'voice-detector-bgeorge'
os.environ.setdefault('HF_HOME', str(Path(__file__).parent / 'models' / '.hub-cache'))
MODEL_SOURCE = f'https://huggingface.co/{MODEL_ID}'
_lock = threading.Lock()
_model = None
_processor = None


class DetectorUnavailable(RuntimeError):
    pass


def status():
    installed = all((MODEL_PATH / name).is_file() for name in
                    ('config.json', 'preprocessor_config.json', 'model.safetensors'))
    return {'model': MODEL_ID, 'revision': MODEL_REVISION, 'installed': installed,
            'loaded': _model is not None, 'method': 'pretrained-wav2vec2'}


def load_model():
    global _model, _processor
    if _model is not None:
        return
    if not status()['installed']:
        raise DetectorUnavailable('Detection model is not installed. Close the server, '
                                  'run setup.bat, then reopen start.bat.')
    try:
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        torch.set_num_threads(4)
        processor = AutoFeatureExtractor.from_pretrained(
            str(MODEL_PATH), local_files_only=True, trust_remote_code=False)
        model = AutoModelForAudioClassification.from_pretrained(
            str(MODEL_PATH), local_files_only=True, trust_remote_code=False,
            use_safetensors=True)
        if model.config.num_labels != 2:
            raise ValueError('Unexpected model output; expected two classes.')
        model.config.id2label = CLASS_LABELS.copy()
        model.config.label2id = {label: index for index, label in CLASS_LABELS.items()}
        model.eval()
        _processor, _model = processor, model
    except Exception as exc:
        raise DetectorUnavailable('Could not load the detection model. Run setup.bat '
                                  'and restart using start.bat. Details: ' + str(exc)) from exc


def summarize_scores(fake_scores, duration, poor_quality=False):
    """Aggregate model scores; abstain for uncertain or conflicting predictions."""
    if not fake_scores or any(not math.isfinite(x) or not 0 <= x <= 1 for x in fake_scores):
        raise DetectorUnavailable('The model returned invalid scores. Please try another recording.')
    fake_score = sum(fake_scores) / len(fake_scores)
    # Require substantial support on both sides; a single outlier in a long
    # recording should not override an otherwise consistent prediction.
    real_votes = sum(score <= 0.30 for score in fake_scores) / len(fake_scores)
    fake_votes = sum(score >= 0.70 for score in fake_scores) / len(fake_scores)
    disagreement = real_votes >= 0.30 and fake_votes >= 0.30
    if poor_quality or duration < 2 or disagreement or 0.30 < fake_score < 0.70:
        label, tone = 'Inconclusive', 'neutral'
    elif fake_score >= 0.70:
        label, tone = 'Likely AI-generated voice', 'warning'
    else:
        label, tone = 'Likely human voice', 'success'
    reasons = [f'The pretrained neural model analyzed {len(fake_scores)} speech segment(s).']
    if disagreement:
        reasons.append('Different parts of this recording received conflicting predictions.')
    if poor_quality:
        reasons.append('Low recording level or clipping makes the result unreliable.')
    if duration < 2:
        reasons.append('This clip is very short. Record 5–15 seconds for a more useful result.')
    if tone == 'neutral' and not (disagreement or poor_quality or duration < 2):
        reasons.append('The model scores are too close to make a clear prediction.')
    reasons.append('Predictions may be wrong for unfamiliar voices, languages or synthesis tools.')
    return {'label': label, 'tone': tone, 'score': round(fake_score * 100, 1),
            'humanScore': round((1 - fake_score) * 100, 1),
            'segments': len(fake_scores), 'segmentScores': [round(x * 100, 1) for x in fake_scores],
            'reasons': reasons, 'model': MODEL_ID, 'modelRevision': MODEL_REVISION,
            'method': 'pretrained-wav2vec2', 'modelSource': MODEL_SOURCE,
            'limitation': 'Model scores are not calibrated probabilities or proof of authenticity. '
                          'This college prototype has not been benchmarked on your recordings. '
                          'Use speech only; music, test tones and noise are outside its intended input.'}


def classify(samples, sample_rate, duration, poor_quality=False):
    try:
        return _classify(samples, sample_rate, duration, poor_quality)
    except (DetectorUnavailable, ValueError):
        raise
    except Exception as exc:
        raise DetectorUnavailable('Neural analysis could not finish. Restart with start.bat; '
                                  'if the problem continues, run setup.bat again.') from exc


def _classify(samples, sample_rate, duration, poor_quality=False):
    # Serialize CPU inference to avoid competing model loads and memory spikes.
    with _lock:
        load_model()
        import numpy as np
        import torch
        from scipy.signal import resample_poly
        rate = int(sample_rate)
        audio = np.asarray(samples, dtype=np.float32)
        divisor = math.gcd(rate, 16000)
        if rate != 16000:
            audio = resample_poly(audio, 16000 // divisor, rate // divisor)
        # Match this model's documented one-second training window. Sample up
        # to ten evenly spaced windows to cover the recording without long CPU work.
        length = WINDOW_SECONDS * 16000
        count = min(MAX_SEGMENTS, max(1, math.ceil(len(audio) / length)))
        starts = np.linspace(0, max(0, len(audio) - length), count, dtype=int)
        fake_scores = []
        labels = {str(value).lower(): int(key) for key, value in _model.config.id2label.items()}
        for start in starts:
            window = audio[start:start + length]
            if float(np.sqrt(np.mean(window * window))) < 0.003:
                continue
            inputs = _processor(window, sampling_rate=16000, return_tensors='pt',
                                max_length=length, truncation=True, padding='max_length')
            with torch.inference_mode():
                probabilities = torch.softmax(_model(**inputs).logits, dim=-1)[0]
            fake_scores.append(float(probabilities[labels['fake']]))
        if not fake_scores:
            raise ValueError('No usable speech-level audio was found. Record again closer to the microphone.')
        return summarize_scores(fake_scores, duration, poor_quality)
