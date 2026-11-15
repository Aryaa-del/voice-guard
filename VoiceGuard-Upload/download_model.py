"""Download model data only, using a pinned repository revision."""
import os
import hashlib
import time
from pathlib import Path

from detector import MODEL_ID, MODEL_REVISION, MODEL_PATH

WEIGHT_SHA256 = '2f5f95a1722bd6e9349ccd3a38adadd7dccad501e84d99c708f7d893dc93f2e5'


def download_weights():
    """Stream public model data with resume support, then verify its LFS SHA256."""
    import requests
    target = MODEL_PATH / 'model.safetensors'
    partial = MODEL_PATH / 'model.safetensors.part'
    def digest(path):
        result = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                result.update(chunk)
        return result.hexdigest()
    if target.exists() and digest(target) == WEIGHT_SHA256:
        print('Model weights already verified.', flush=True)
        return
    url = f'https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/model.safetensors'
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        try:
            with requests.get(url, headers={'Range': f'bytes={offset}-'} if offset else {},
                              stream=True, timeout=(20, 60)) as response:
                response.raise_for_status()
                append = offset > 0 and response.status_code == 206
                if not append:
                    offset = 0
                received, last_report = offset, time.monotonic()
                with partial.open('ab' if append else 'wb') as handle:
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        handle.write(chunk)
                        received += len(chunk)
                        if time.monotonic() - last_report > 8:
                            print(f'Model weights: {received / 1_000_000:.0f} / 378 MB', flush=True)
                            last_report = time.monotonic()
            if digest(partial) != WEIGHT_SHA256:
                raise RuntimeError('Downloaded weight checksum does not match the pinned model.')
            partial.replace(target)
            print('Model weights downloaded and SHA256 verified.', flush=True)
            return
        except requests.RequestException:
            print(f'Download interrupted; retrying ({attempt + 1}/3)...', flush=True)
            if attempt == 2:
                raise RuntimeError('Model download did not finish. Check your connection and retry setup.bat.') from None


def configure_certificates():
    # Use the local organization's trusted Windows roots if a bundle is available.
    # TLS verification remains enabled.
    bundle = Path(__file__).parent / '.venv' / 'windows-ca.pem'
    if bundle.is_file():
        os.environ.setdefault('REQUESTS_CA_BUNDLE', str(bundle))
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')


if __name__ == '__main__':
    configure_certificates()
    from huggingface_hub import snapshot_download, hf_hub_download
    print('Downloading pretrained voice model (~380 MB). No recordings are uploaded.')
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir=str(MODEL_PATH),
                      allow_patterns=['config.json', 'preprocessor_config.json',
                                      'README.md', 'LICENSE*'])
    download_weights()
    print('Checking that the model loads...')
    from detector import load_model
    load_model()
    print('Downloading a public human speech example...')
    import soundfile as sf
    source = hf_hub_download('Narsil/asr_dummy', '1.flac', repo_type='dataset',
                             revision='8d141c8', local_dir=str(MODEL_PATH / 'sample-source'))
    audio, rate = sf.read(source)
    output = Path(__file__).parent / 'static' / 'samples' / 'human-speech.wav'
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), audio, rate, subtype='PCM_16')
    print('Downloading a public neural TTS example...')
    neural_source = hf_hub_download('hexgrad/Kokoro-82M', 'samples/af_heart_0.wav',
                                    revision='f3ff357', local_dir=str(MODEL_PATH / 'neural-sample-source'))
    neural_audio, neural_rate = sf.read(neural_source)
    sf.write(str(output.parent / 'neural-voice.wav'), neural_audio, neural_rate, subtype='PCM_16')
    print('Ready. Open start.bat to launch Voice Guard.')
