const $ = (selector) => document.querySelector(selector);
$('#browse').addEventListener('click', () => $('#file').click());
let selectedFile = null, audioUrl = null, busy = false;
let recorder = null, recordingTimer = null, recordingStarted = 0, recordingContext = null;
let history = [];
try { const saved = JSON.parse(localStorage.getItem('voiceguard-model-history') || '[]'); if (Array.isArray(saved)) history = saved.filter(x => x && typeof x.name === 'string' && typeof x.label === 'string').slice(0, 10); } catch { /* Storage can be disabled. */ }

function showError(message = '') { $('#error').textContent = message; $('#error').hidden = !message; }
function updateControls() {
  const recording = recorder && recorder.state !== 'inactive';
  $('#analyze').disabled = !selectedFile || busy || recording;
  $('#record').disabled = busy;
  $('#remove').disabled = busy || recording;
  $('#file').disabled = busy || recording;
  $('#browse').disabled = busy || recording;
  document.querySelectorAll('[data-demo]').forEach(button => button.disabled = busy || recording);
}
function saveHistory() { try { localStorage.setItem('voiceguard-model-history', JSON.stringify(history)); } catch { /* In-memory history still works. */ } }
function renderHistory() {
  $('#history-count').textContent = history.length;
  $('#history-list').replaceChildren();
  if (!history.length) {
    const empty = document.createElement('div'); empty.className = 'no-history'; empty.textContent = 'A fresh start. Your recent voice checks will appear here.'; $('#history-list').append(empty); return;
  }
  history.forEach(item => {
    const row = document.createElement('div'); row.className = 'history-row';
    const name = document.createElement('span'); name.className = 'history-name'; name.textContent = item.name;
    const badge = document.createElement('span'); badge.className = `badge ${['success', 'warning', 'neutral'].includes(item.tone) ? item.tone : 'neutral'}`; badge.textContent = item.label;
    const time = document.createElement('small'); time.textContent = new Date(item.date).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    row.append(name, badge, time); $('#history-list').append(row);
  });
}
async function drawWaveform(file) {
  $('#waveform').replaceChildren();
  let context;
  try {
    context = new AudioContext();
    const decoded = await context.decodeAudioData(await file.arrayBuffer());
    if (selectedFile !== file) return;
    const data = decoded.getChannelData(0), count = 64, block = Math.max(1, Math.floor(data.length / count));
    for (let i = 0; i < count; i++) {
      let peak = 0;
      for (let j = i * block; j < Math.min((i + 1) * block, data.length); j += 8) peak = Math.max(peak, Math.abs(data[j]));
      const bar = document.createElement('i'); bar.style.height = `${Math.max(3, peak * 28)}px`; $('#waveform').append(bar);
    }
  } catch { /* Backend shows a useful error if the file cannot be decoded. */ }
  finally { if (context) await context.close(); }
}
function selectFile(file) {
  if (busy || (recorder && recorder.state !== 'inactive')) return;
  showError();
  if (!file || !/\.wav$/i.test(file.name)) return showError('Choose a WAV recording, or use your microphone to record here.');
  if (file.size > 20 * 1024 * 1024) return showError('Please choose a file smaller than 20 MB.');
  selectedFile = file;
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = URL.createObjectURL(file); $('#player').src = audioUrl;
  $('#file-name').textContent = file.name; $('#file-size').textContent = `${(file.size / 1024).toFixed(1)} KB · ready to analyze`;
  $('#audio-selection').hidden = false; updateControls(); drawWaveform(file);
  $('#empty-result').hidden = false; $('#result').hidden = true; $('#result-status').textContent = 'READY TO ANALYZE';
}
$('#file').addEventListener('change', event => selectFile(event.target.files[0]));
['dragenter', 'dragover'].forEach(type => $('#dropzone').addEventListener(type, event => { event.preventDefault(); $('#dropzone').classList.add('dragover'); }));
['dragleave', 'drop'].forEach(type => $('#dropzone').addEventListener(type, event => { event.preventDefault(); $('#dropzone').classList.remove('dragover'); }));
$('#dropzone').addEventListener('drop', event => selectFile(event.dataTransfer.files[0]));
$('#remove').addEventListener('click', () => {
  selectedFile = null; $('#file').value = ''; $('#player').pause(); $('#player').removeAttribute('src'); $('#player').load();
  if (audioUrl) URL.revokeObjectURL(audioUrl); audioUrl = null;
  $('#audio-selection').hidden = true; $('#result').hidden = true; $('#empty-result').hidden = false;
  $('#result-status').textContent = 'AWAITING AUDIO'; showError(); updateControls();
});

function renderResult(result) {
  const target = $('#result'); target.replaceChildren(); target.className = result.tone;
  // All user-controlled strings are inserted with textContent.
  const add = (tag, className, text, parent = target) => { const element = document.createElement(tag); element.className = className; element.textContent = text; parent.append(element); return element; };
  add('div', 'result-icon', result.tone === 'success' ? '✓' : result.tone === 'warning' ? '✧' : '?');
  add('h3', 'result-title', result.label);
  add('p', 'result-subtitle', result.tone === 'neutral' ? 'The signals are mixed. A clearer or longer recording may help.' : 'A closer look at the patterns in your recording. This result is an estimate, not proof.');
  const label = add('div', 'score-label', 'AI signal score'); add('strong', '', `${result.score}%`, label);
  const track = add('div', 'score-track', ''); const fill = add('span', '', '', track); fill.style.width = `${result.score}%`;
  add('p', 'score-help', `Human signal score: ${result.humanScore}%. These scores do not represent guaranteed accuracy or certainty.`);
  const metrics = add('div', 'metrics', '');
  [[`${result.duration}s`, 'DURATION'], [`${result.metrics.pausePercent}%`, 'QUIET PAUSES'], [result.segments, 'SECTIONS CHECKED']].forEach(([value, name]) => { const metric = add('div', 'metric', '', metrics); add('strong', '', value, metric); add('span', '', name, metric); });
  const reasons = add('ul', 'reasons', '');
  add('li', '', `Checked ${result.segments} short sections of your recording.`, reasons);
  result.reasons.slice(1).forEach(reason => add('li', '', reason, reasons));
  add('p', 'result-meta', 'Private analysis · Your recording is not saved');
  add('p', 'score-help', 'Clear speech gives more useful results. Background noise, music and unfamiliar voices can affect the prediction.');
  $('#empty-result').hidden = true; target.hidden = false; $('#result-status').textContent = 'ANALYSIS COMPLETE';
}
$('#analyze').addEventListener('click', async () => {
  if (!selectedFile || busy) return;
  busy = true; updateControls(); showError(); $('#result-panel').setAttribute('aria-busy', 'true');
  $('#analyze').firstElementChild.textContent = 'Analyzing audio…'; $('#result-status').textContent = 'PROCESSING'; $('#result-panel').classList.add('loading');
  try {
    const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: selectedFile });
    const result = await response.json(); if (!response.ok) throw new Error(response.status === 503 ? 'Voice analysis is temporarily unavailable. Please try again later.' : result.error || 'Could not analyze this audio.');
    renderResult(result);
    history.unshift({ name: selectedFile.name, label: result.label, tone: result.tone, date: new Date().toISOString() });
    history = history.slice(0, 10); saveHistory(); renderHistory();
  } catch (error) { showError(error.message === 'Failed to fetch' ? 'Cannot reach VoiceGuard. Check your connection and try again.' : error.message); $('#result-status').textContent = 'PLEASE TRY AGAIN'; }
  finally { busy = false; updateControls(); $('#analyze').firstElementChild.textContent = 'Analyze audio'; $('#result-panel').setAttribute('aria-busy', 'false'); $('#result-panel').classList.remove('loading'); }
});
document.querySelectorAll('[data-demo]').forEach(button => button.addEventListener('click', async () => {
  busy = true; updateControls(); showError();
  try {
    const sample = button.dataset.demo === 'synthetic' ? 'neural-voice.wav' : 'human-speech.wav';
    const response = await fetch(`/samples/${sample}`); if (!response.ok) throw new Error('Sample could not be loaded.');
    const blob = await response.blob(); busy = false;
    selectFile(new File([blob], `${button.dataset.demo}-speech-sample.wav`, { type: 'audio/wav' }));
    $('#analyzer').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    $('#analyze').focus({ preventScroll: true });
  } catch { showError('This sample is unavailable. Try recording your voice or choosing an audio file.'); $('#analyzer').scrollIntoView({ behavior: 'auto' }); }
  finally { busy = false; updateControls(); }
}));
$('#clear-history').addEventListener('click', () => { history = []; saveHistory(); renderHistory(); });

async function blobToWav(blob, context) {
  const decoded = await context.decodeAudioData(await blob.arrayBuffer());
  const count = Math.min(decoded.length, Math.floor(decoded.sampleRate * 60));
  const buffer = new ArrayBuffer(44 + count * 2), view = new DataView(buffer);
  const write = (offset, text) => [...text].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)));
  write(0, 'RIFF'); view.setUint32(4, 36 + count * 2, true); write(8, 'WAVE'); write(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, decoded.sampleRate, true); view.setUint32(28, decoded.sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); write(36, 'data'); view.setUint32(40, count * 2, true);
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, i) => decoded.getChannelData(i));
  for (let i = 0; i < count; i++) { const value = Math.max(-1, Math.min(1, channels.reduce((sum, data) => sum + data[i], 0) / channels.length)); view.setInt16(44 + i * 2, value < 0 ? value * 32768 : value * 32767, true); }
  return new File([buffer], 'microphone-recording.wav', { type: 'audio/wav' });
}
$('#record').addEventListener('click', async () => {
  if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
  showError();
  if (!navigator.mediaDevices || !window.MediaRecorder) return showError('Microphone recording is unavailable in this browser. Use a WAV upload or try Chrome on localhost.');
  let stream;
  $('#record').disabled = true;
  try {
    recordingContext = new AudioContext(); await recordingContext.resume();
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = []; recorder = new MediaRecorder(stream);
    recorder.addEventListener('dataavailable', event => { if (event.data.size) chunks.push(event.data); });
    recorder.addEventListener('stop', async () => {
      clearInterval(recordingTimer); stream.getTracks().forEach(track => track.stop());
      $('#record').classList.remove('recording'); $('#record').innerHTML = '<span class="record-dot"></span> Record your voice <span id="record-time"></span>';
      busy = true; updateControls();
      try { const file = await blobToWav(new Blob(chunks, { type: recorder.mimeType }), recordingContext); busy = false; selectFile(file); }
      catch { showError('We could not prepare this recording. Try again or choose a WAV file.'); }
      finally { await recordingContext.close(); recordingContext = null; recorder = null; busy = false; updateControls(); }
    });
    recorder.start(); recordingStarted = Date.now(); $('#record').classList.add('recording');
    $('#record').innerHTML = '<span class="record-dot"></span> Stop recording <span id="record-time">0s / 60s</span>';
    recordingTimer = setInterval(() => { const seconds = Math.floor((Date.now() - recordingStarted) / 1000); $('#record-time').textContent = `${seconds}s / 60s`; if (seconds >= 60 && recorder.state === 'recording') recorder.stop(); }, 250);
    updateControls();
  } catch { if (stream) stream.getTracks().forEach(track => track.stop()); if (recordingContext) await recordingContext.close(); recordingContext = null; showError('Microphone access was not available. Allow microphone permission or upload a WAV file.'); updateControls(); }
});
renderHistory();
fetch('/api/health').then(response => response.json()).then(health => {
  const ready = health.method === 'pretrained-wav2vec2' && health.installed;
  $('#model-status').textContent = ready ? 'Ready to analyze' : 'Analysis unavailable';
  $('#model-status').classList.add(ready ? 'ready' : 'unavailable');
}).catch(() => { $('#model-status').textContent = 'Waiting for connection'; $('#model-status').classList.add('unavailable'); });

document.querySelectorAll('.nav-link').forEach(link => link.addEventListener('click', () => {
  document.querySelectorAll('.nav-link').forEach(item => item.classList.toggle('active', item === link));
}));
