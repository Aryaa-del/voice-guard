"""WSGI entry point for hosting the website and detector on one origin."""
import logging
import threading

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app import ROOT, MAX_BYTES, analyze
from detector import DetectorUnavailable, status as model_status

app = Flask(__name__, static_folder=str(ROOT / 'static'), static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = MAX_BYTES
_analysis_slot = threading.BoundedSemaphore(1)


@app.get('/')
def index():
    return app.send_static_file('index.html')


@app.get('/api/health')
def health():
    return jsonify(status='ok', processingLocation='server', **model_status())


@app.post('/api/analyze')
def analyze_voice():
    if not _analysis_slot.acquire(blocking=False):
        return jsonify(error='Another recording is being analyzed. Please try again shortly.'), 429
    try:
        data = request.get_data(cache=False)
        if not data:
            return jsonify(error='Please choose or record an audio clip first.'), 400
        return jsonify(analyze(data))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except DetectorUnavailable:
        # Keep diagnostics in service logs, without recording the uploaded audio.
        logging.exception('Voice detector unavailable')
        return jsonify(error='The voice detector could not load. Please try again later.'), 503
    except HTTPException:
        raise
    except Exception:
        logging.exception('Voice analysis failed')
        return jsonify(error='The recording could not be analyzed. Please try again.'), 500
    finally:
        _analysis_slot.release()


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return jsonify(error='Upload a WAV file smaller than 20 MB.'), 413


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response
