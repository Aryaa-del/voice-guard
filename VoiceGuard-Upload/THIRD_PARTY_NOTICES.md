# Model and sample acknowledgments

## Pretrained detection model

Bgeorge, **deepfake-audio-detector-wav2vec2**, revision `7bdcadcb5d47522c0237ef95a97702761fc05baf`.

- Source and model card: https://huggingface.co/Bgeorge/deepfake-audio-detector-wav2vec2
- License declared by repository metadata: CC BY-NC 4.0, https://creativecommons.org/licenses/by-nc/4.0/. The README includes a contradictory license placeholder; use for this noncommercial educational demonstration and seek author clarification before other uses.
- Architecture: Wav2Vec2ForSequenceClassification. Built on the Wav2Vec2 model family.
- Original weights are downloaded during setup. Voice Guard does not train or claim authorship of them.
- SHA256 of pinned safetensors weights: `2f5f95a1722bd6e9349ccd3a38adadd7dccad501e84d99c708f7d893dc93f2e5`.
- Class mapping follows the author's documented training labels and quickstart (0=real, 1=fake), correcting inherited reversed config labels in memory. The original downloaded config is preserved unchanged.

Model evaluation numbers published by the author are not independently verified project accuracy.

## Public human speech sample

`static/samples/human-speech.wav` is converted from the public ASR example `1.flac` in **Narsil/asr_dummy**, revision `8d141c8`:

https://huggingface.co/datasets/Narsil/asr_dummy/blob/8d141c8/1.flac

The repository's automatic speech recognition loading script identifies the source corpus as **LibriSpeech**, prepared by Vassil Panayotov with the assistance of Daniel Povey, from read LibriVox audiobooks. Corpus source: https://www.openslr.org/12. Corpus license: **Creative Commons Attribution 4.0**, https://creativecommons.org/licenses/by/4.0/.

Modification: converted from FLAC to 16-bit PCM WAV. This example is not claimed to be independent of the detector's training data, whose full composition is not documented upstream.

## Synthetic speech samples

`ai-voice.wav` and `everyday-voice.wav` were generated locally with installed Microsoft Windows desktop text-to-speech voices for this educational demonstration. They contain ordinary invented dialogue and do not imitate a requested individual. Their source is known from generation, independent of model predictions.

`neural-voice.wav` is a 16-bit PCM conversion of the published Kokoro sample:

https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff357/samples/af_heart_0.wav

Kokoro-82M by hexgrad is a neural text-to-speech model whose repository declares Apache-2.0 for its weights. This short published audio example is included for educational comparison; the first sentence read is from William Gibson's *Neuromancer*. Source model: https://huggingface.co/hexgrad/Kokoro-82M. No Kokoro model code or weights are executed by this app.

## Libraries

Python dependencies are separately licensed by their authors. See their installed package metadata. The interface optionally uses Google Fonts (DM Sans and Manrope); system font fallbacks are provided.
