# Lull - Live Voice Agent

Lull is a live voice assistant that can:
- Read your laptop screen using OCR and answer questions about it
- Translate English sentences to Hindi, Marathi, or French
- Use the camera to identify objects in your hand
- Respond to "Hi Lull" with a fixed greeting
- Stop talking when you say "Stop"

## Features

- Wake phrase: "Hi Lull"
- Greeting response: "Hi Amita , How may I help you?"
- Screen OCR: Captures the primary screen and extracts text
- Screen Q&A: Answers questions from the extracted text
- Object detection: Uses a built-in camera and YOLOv8
- Translation: Uses LibreTranslate public endpoint (no API key required)
- Stop command: "Stop"

## Requirements

- Python 3.10+
- A working microphone and camera
- Internet access for first-time model downloads
- System packages (Linux):
  - `tesseract-ocr`
  - `portaudio19-dev` (for microphone input)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Tesseract OCR:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr portaudio19-dev
```

## Optional Model Setup (Offline Speech)

Lull can use Vosk for offline speech-to-text. Download a model and set:

```bash
export VOSK_MODEL_PATH="/path/to/vosk-model"
```

If no Vosk model is available, use text input mode:

```bash
python lull_agent.py --text
```

## Run

```bash
python lull_agent.py
```

## Desktop App (Live Screen + Voice)

Run the desktop GUI for true live screen capture and voice input:

```bash
python desktop_app.py
```

Notes:
- Uses your active desktop screen directly (no screenshot uploads).
- Uses microphone input. For offline speech, set `VOSK_MODEL_PATH`.
- If no Vosk model is set, it falls back to Google Web Speech (no API key).
- Use the "Start Camera" button to preview and ensure the camera is visible.
- If the preview is blank, try another camera index (0, 1, 2).

## Web App (Streamlit)

This repo includes a web deployment at `Live_Voice_agents/streamlit_app.py`.

Limitations:
- Browsers cannot read your full laptop screen directly. Upload a screenshot for OCR.
- Voice input/output is not enabled in the web app; use the local app for voice.

Run locally:

```bash
pip install -r ../requirements.txt
streamlit run streamlit_app.py
```

Deploy on Streamlit Community Cloud:
- App file: `Live_Voice_agents/streamlit_app.py`
- System packages: `tesseract-ocr` (see `packages.txt`)

## Example Commands

- "Hi Lull"
- "What is on my screen?"
- "Read my screen"
- "Do you see the word invoice on my screen?"
- "What am I holding in my hand?"
- "Translate I am hungry to Hindi"
- "Translate this sentence to French: Please send the report"
- "Stop"

## Configuration

LibreTranslate public endpoint is used by default:

- `LIBRETRANSLATE_ENDPOINT` (default: `https://libretranslate.de/translate`)
- `LIBRETRANSLATE_ENDPOINTS` (optional comma-separated list)
- `LIBRETRANSLATE_API_KEY` (optional)

No API key is required to run the default setup. If a public endpoint is down,
set `LIBRETRANSLATE_ENDPOINTS` to a list of working endpoints, for example:

```
LIBRETRANSLATE_ENDPOINTS=https://translate.argosopentech.com/translate,https://translate.astian.org/translate
```

If LibreTranslate endpoints are blocked, the app falls back to MyMemory
(public, no API key).
