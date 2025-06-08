# PseudoTube

A Flask-based video sharing platform inspired by YouTube, supporting video upload, transcoding, streaming, user authentication through OAuth2, comments, likes, and search. Built for deployment on Google App Engine with Google Cloud Storage, Transcoder API integration. Can use Google Cloud Functions for better experience.

## Features
- User authentication via Google OAuth2
- Video uploads straight to bucket
- Automatic video transcoding to multiple resolutions/bitrates/fps using Google Cloud Transcoder
- Video streaming with DASH manifests
- Video search, trending, most liked, and most recent listings
- Comments, likes, and view tracking per video
- Google Cloud Storage for video and thumbnail storage

## Project Structure
```
app/            # Main Flask app and blueprints
  models/       # SQLAlchemy models (User, Video, Comment, etc.)
  routes/       # Flask blueprints for user, video, upload, watch, search, etc.
  context.py    # App context, DB, login, storage, transcoder setup
  storage.py    # Google Cloud Storage integration
  transcoder.py # Google Cloud Transcoder integration
  oauth.py      # OAuth2 provider manager
  gae.py        # Google App Engine and GCP integration
static/         # Static files (CSS, JS, images)
templates/      # Jinja2 HTML templates
entry.py        # App entry point
requirements.txt# Python dependencies
app.yaml        # Google App Engine deployment config
*.creds.json    # GCP service account credentials (not for public sharing)
```

## Requirements
- Python 3.10+
- MySQL database (Cloud SQL recommended)
- Google Cloud project with:
  - Cloud Storage bucket
  - Video Transcoder API enabled
  - Pub/Sub topic for transcoder jobs
  - OAuth2 credentials (Google)
  - Service accounts for storage, transcoder, ffprobe

## Installation
1. Clone the repository and `cd` into the project directory.
2. Create a Python virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables (see `app.yaml` for required variables) and place your GCP credentials in the root directory as `*.creds.json` files (for local use).
5. Initialize the database (tables are auto-created on first run).

## Running Locally
```bash
python entry.py
```
The app will be available at http://localhost:5000

## Deployment (Google App Engine)
1. Ensure all environment variables and credentials are set as in `app.yaml`.
2. Deploy with:
   ```bash
   gcloud app deploy
   ```

## License
This project is for educational purposes.
