# Voice Guard — Human vs AI Voice Detection

For online deployment of the complete website and analyzer, follow [HOSTING.md](HOSTING.md). The hosting entry point is `hosted_app.py`; it uses the same detector and serves the frontend and API together. These files prepare a deployment but do not publish it. In hosted mode, audio is transmitted to the hosting server for processing.

A college web project with HTML, CSS, JavaScript and Python. **This version uses a pretrained Wav2Vec2 neural audio classifier**, replacing the original volume/pause rules. It runs locally and supports microphone recording and WAV uploads.

## Open the project

1. Open this folder in File Explorer.
2. If setup has not been completed, double-click **setup.bat**. Internet is needed to install packages and download the model (approximately 380 MB plus dependencies).
3. Double-click **start.bat** and keep its terminal open.
4. Open **http://localhost:8000** in Chrome or Edge.
5. Record **5–15 seconds** of speech, stop recording, then click **Analyze audio**.

If an older Voice Guard server is already running, close its terminal first. Refresh the webpage with **Ctrl+F5** after an update. Do not open index.html directly.

The project requires 64-bit Python 3.10+ (tested with 3.11). Setup creates `.venv` within this folder; it does not modify the global Python installation. Allow several GB of disk space for the environment and model. CPU inference is supported; no GPU or API key is required. Stop the server with Ctrl+C.

Manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip --index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --index-url https://pypi.org/simple
.\.venv\Scripts\python.exe download_model.py
.\.venv\Scripts\python.exe app.py
```

Setup.bat overrides `PIP_NO_INDEX=1` only for its own process. On managed networks it supports a custom CA bundle at `.venv/windows-ca.pem`, keeping TLS verification enabled. Ask IT for certificate help rather than disabling verification.

## What changed

The previous version assigned human-like/synthetic-like labels from changes in volume and pauses. Those rules could not distinguish real speech from generated speech. **They no longer determine the prediction.**

Current flow:

```text
Browser microphone or WAV upload
  → Python validates 16-bit PCM audio and mixes stereo to mono
  → scipy resamples to 16 kHz with a polyphase filter
  → pretrained Wav2Vec2 model analyzes up to ten one-second windows
  → average fake/real softmax scores
  → likely AI / likely human / inconclusive
  → browser displays model scores, audio quality and limitations
```

Audio volume, pauses and clipping are still measured for context. Low recording levels or clipping can force an inconclusive result, but cannot turn a human prediction into AI or vice versa.

## Model and interpretation

- Model: [Bgeorge/deepfake-audio-detector-wav2vec2](https://huggingface.co/Bgeorge/deepfake-audio-detector-wav2vec2).
- Pinned revision: `7bdcadcb5d47522c0237ef95a97702761fc05baf`; config and weights are stored in `models/voice-detector-bgeorge`.
- Repository metadata declares **CC BY-NC 4.0**. This project is intended for noncommercial college demonstration. The README has an inconsistent placeholder about licensing; follow the repository's declared license and contact its author for clarification before other uses.
- Architecture: Wav2Vec2ForSequenceClassification, approximately 94.6 million parameters.
- **Class-label correction:** the author's model card describes training labels and supplies inference code using **0=REAL, 1=FAKE**. The downloaded config retains the opposite labels from its base checkpoint. `CLASS_LABELS` in detector.py explicitly follows the author's training description and quickstart. This is a fixed model-wide mapping, never a decision based on filename or sample choice. The known-source smoke tests document its behavior.
- Inputs match the author's one-second, 16 kHz training format. Up to ten windows are sampled across a long recording; not every second of a long recording is analyzed.
- Only local safetensors weights are loaded. Remote custom Python code is disabled. No pickle model files are downloaded or loaded.

Decision rules are conservative presentation choices, not validated operating thresholds:

- Average fake score ≥70% → **Likely AI-generated voice**.
- Average fake score ≤30% → **Likely human voice**.
- Otherwise → **Inconclusive**.
- Substantial segment disagreement (at least 30% strongly real and at least 30% strongly fake), clips under two seconds, clipping, or weak volume → **Inconclusive**. Isolated outliers do not automatically invalidate a longer recording.
- Missing model/dependencies → an explicit error, with **no fallback** to the old heuristic.

**Model scores are not calibrated probabilities, accuracy percentages, or proof of authenticity.** Even a score near 100% can be wrong. No accuracy guarantee is made for your recordings, accent or unseen generators. The model was trained/evaluated on English speech from a single dataset; other languages and unfamiliar synthesis tools may behave differently. Do not quote its self-reported evaluation score as this project's accuracy. The window aggregation and thresholds used here have not been independently validated.

Use speech only. This classifier is not a speech recognizer or voice activity detector: music, tones, silence, noisy audio, mixed human/AI speech and unusual microphone processing are unsuitable inputs. Generated voices can be missed; genuine speech can be flagged. It does not identify a speaker, monitor incoming calls, or detect whether spoken statements are true.

## Sample audio and privacy

- `everyday-voice.wav` and `ai-voice.wav`: synthetic speech produced locally with installed Windows text-to-speech voices. File contents are analyzed normally; filenames and sample choice never determine the prediction. These examples are traditional TTS, not a benchmark of modern voice cloning.
- `neural-voice.wav`: converted to 16-bit WAV from the published [Kokoro neural TTS sample af_heart_0.wav](https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff357/samples/af_heart_0.wav). This is the AI sample offered by the website. It contains a short ordinary sentence, without an announcement that it is AI. Source and attribution are recorded in THIRD_PARTY_NOTICES.md.
- `human-speech.wav`: converted from [Narsil/asr_dummy/1.flac](https://huggingface.co/datasets/Narsil/asr_dummy/blob/8d141c8/1.flac), a public speech test sample. Its [loading script](https://huggingface.co/datasets/Narsil/asr_dummy/blob/8d141c8/automatic_speech_recognition_dummy.py) identifies LibriSpeech as its ASR source; [LibriSpeech](https://www.openslr.org/12) is licensed CC BY 4.0. Original FLAC is retained under the model directory for provenance. This is a smoke test, not evidence of unseen-speaker accuracy or training/test independence.

After setup, inference is offline. No microphone audio is uploaded to Hugging Face or another third-party inference service. Audio is held in server memory; only the last ten result summaries are saved in the browser. Clear history with the button. Earlier heuristic results use a separate storage key and are not mixed with neural model results. Optional Google Fonts require internet; system fonts work offline.

## Files

```text
app.py                  Local HTTP server, WAV parsing and quality measurements
detector.py             Model loading, resampling, inference and aggregation
download_model.py       Pinned model and public human sample download
requirements.txt        Python dependencies (PyTorch installed separately)
setup.bat / start.bat    Windows install and launch shortcuts
static/                 HTML, CSS, JavaScript and speech examples
tests/test_app.py       Regression and HTTP tests with stubbed model scores
models/                 Downloaded model files, excluded from source control
.venv/                  Project-local Python environment
```

`GET /api/health` reports model installation/loading status; `POST /api/analyze` accepts raw WAV bytes and returns JSON. Invalid audio returns 400; missing model returns 503. The old `/api/demo` tone generator remains only for test fixtures; the website uses actual speech samples.

Supported WAV: 16-bit uncompressed PCM, mono or stereo, 8–96 kHz, 1–60 seconds, up to 20 MB. The browser converts microphone recordings to WAV. First analysis loads the model and may take longer. Public deployment needs a production HTTP server and resource controls; this server binds only to localhost.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
.\.venv\Scripts\python.exe verify_model.py
```

Regression tests check decision thresholds, abstention, invalid/silent audio, missing-model behavior and HTTP responses. They use stubbed neural scores and **do not measure detection accuracy**. `verify_model.py` runs the installed model on bundled speech samples, checks repeatability without filenames, and writes `MODEL_TEST_REPORT.json`. A few samples cannot establish accuracy. Test the presenter's microphone separately before the presentation.

An earlier candidate, MelodyMachine/Deepfake-audio-detection-V2, missed the synthetic examples and was replaced. The final report includes the older Windows voices too, including any inconclusive result. Selection on these examples means they are development smoke tests, **not an independent test set**. There is no guarantee that every AI voice will be detected.

## Presentation outline

1. Problem: synthetic voices can resemble human speech.
2. Goal: build a speech upload/recording interface connected to a pretrained deepfake classifier.
3. Frontend: HTML/CSS and JavaScript handle recording, WAV conversion and results.
4. Backend: Python validates audio, resamples it and runs Wav2Vec2 with PyTorch.
5. Demo: analyze the synthetic sample, human sample and a new microphone recording. Explain errors or uncertainty honestly.
6. Limitations: pretrained model bias, unfamiliar generators/languages, noise and uncalibrated scores.
7. Future work: evaluate an independently labeled dataset with unseen speakers and generators; report precision, recall, false positives and false negatives; compare stronger models.

Suggested title: **Voice Guard: Human and AI Voice Classification Using a Pretrained Wav2Vec2 Model**.
