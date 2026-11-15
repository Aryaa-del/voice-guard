# Put the complete VoiceGuard website online

This setup serves the website and voice analysis from one HTTPS address. GitHub stores the code; a Python web service runs it. This is prepared for a small educational demo, not a service with guaranteed capacity or detection accuracy.

## 1. Upload the source to GitHub

Create a repository named `voice-guard`. Put the **contents** of your local voice-guard folder at the repository root. Keep the `static` directory intact.

Required files:

```text
app.py
hosted_app.py
detector.py
download_model.py
requirements.txt
requirements-hosted.txt
.python-version
.gitignore
README.md
THIRD_PARTY_NOTICES.md
static/                         (including its samples folder)
```

The startup and setup .bat files, test files, and this guide can be included too. Exclude `.venv/`, `models/`, `__pycache__/`, credentials, reports, and ZIP archives. The model is downloaded during the host build, not uploaded to GitHub.

If you previously uploaded only the frontend assets at the root, use a new repository with the complete structure above to avoid mixing layouts. This hosted setup expects `static/index.html`, not a root-level index.html.

## 2. Create a Python web service on Render

Open https://dashboard.render.com, sign in, and choose **New > Web Service**. Connect the GitHub repository. Choose these settings:

| Setting | Value |
| --- | --- |
| Language | Python 3 |
| Branch | main (or your actual default branch) |
| Root Directory | Leave blank when app.py is at the repository root |
| Health Check Path | /api/health |

Paste this as the **Build Command** (one line):

```sh
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && python -m pip install -r requirements-hosted.txt && python download_model.py
```

Paste this as the **Start Command** (one line):

```sh
gunicorn hosted_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180 --access-logfile - --error-logfile -
```

The `.python-version` file selects Python 3.11. Keep **one worker**: extra workers each load another model copy. The app permits only one active analysis per process and returns a friendly busy response for concurrent requests.

## 3. Check memory and cost before creating the service

The detector is a roughly 380 MB checkpoint, and its runtime needs additional memory. For initial planning, allow **at least 2 GB RAM**, preferably more for long clips. This is a recommendation, not a validated minimum or a guarantee. A low-memory free instance may start the page but fail when loading or using the model.

Read the displayed compute limits and price before accepting a plan. Nothing in this project creates a service or authorizes a purchase automatically.

The selected detector's repository metadata declares CC BY-NC 4.0. Use this configuration for a noncommercial educational demo and retain the model and sample acknowledgments. Commercial use requires resolving the upstream license questions documented in README.md.

## 4. Deploy and test

Click **Create Web Service** only after reviewing the settings and cost. Build logs should show dependency installation, model checksum verification, and a successful model-load check. The build downloads public assets; it does not upload personal recordings.

When the service is live, open its HTTPS URL:

1. Confirm the page says **Ready to analyze**.
2. Load the AI sample and select **Analyze audio**.
3. Load the human sample and analyze it too.
4. Allow microphone permission and record a short clear clip.
5. Confirm that an analysis request returns a result rather than an error. Model labels can be wrong; an unexpected label is separate from an HTTP or startup failure.

If deployment fails, inspect **Build logs** for setup problems and **Runtime logs** for analysis exceptions. The service reports safe user-facing errors while keeping exception details in server logs. Do not log uploaded WAV bytes.

## Privacy and local running

On a hosted website, audio is transmitted to the hosting server to analyze it. VoiceGuard does not write it to an audio archive, but hosting-provider data handling also applies. Browser history stores result summaries only. The website wording has been updated to describe server processing accurately.

The existing local command still works:

```powershell
.\.venv\Scripts\python.exe app.py
```

No deployment has been performed or verified on Render by preparing these files. Local hosted-route tests do not establish cloud memory capacity, microphone permissions, or public availability.

Official setup references: https://render.com/docs/deploy-flask, https://render.com/docs/python-version, https://render.com/docs/web-services.
