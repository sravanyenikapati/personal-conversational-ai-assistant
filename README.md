# 🤖 Personal AI Assistant

A personal conversational AI assistant with adaptive I/O — **voice in → voice out, text in → text out**. Built in Python, designed to scale from a desktop prototype to a full mobile app on Google Play and Apple App Store.

---

## ✨ Features

- 🎤 **Voice input** via microphone (OpenAI Whisper transcription)
- ⌨️ **Text input** via keyboard
- 🔊 **Voice output** via Edge TTS (free, no API key, natural-sounding voices)
- 💬 **Text output** in a clean chat UI
- 🧠 **AI brain** powered by OpenAI GPT-4o (Claude integration ready for Phase 2)
- 🔀 **Adaptive mode** — mirrors the input: voice in = voice out, text in = text out
- 🗂️ **Conversation memory** — maintains full context across the session
- 🔌 **Provider-agnostic** — swap AI models via a single config change

---

## 🏗️ Project Structure

```
personal-ai-assistant/
├── src/assistant/
│   ├── config.py          # Settings from .env via Pydantic
│   ├── logger.py          # Structured logging (Rich)
│   ├── core/
│   │   ├── brain.py       # AI provider abstraction (OpenAI / Claude)
│   │   └── conversation.py# Conversation history manager
│   ├── audio/
│   │   ├── stt.py         # Speech-to-Text (Whisper)
│   │   └── tts.py         # Text-to-Speech (Edge TTS)
│   ├── ui/
│   │   └── desktop.py     # Tkinter desktop UI
│   └── api/
│       └── server.py      # FastAPI backend (Phase 2)
├── tests/                 # Pytest test suite
├── .github/workflows/     # CI/CD (GitHub Actions)
├── .env.example           # Environment variable template
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # Dev dependencies
└── main.py                # Entry point
```

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/personal-ai-assistant.git
cd personal-ai-assistant
```

### 2. Create a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Open .env and add your OPENAI_API_KEY
```

### 5. Run the assistant
```bash
python main.py
```

---

## ⚙️ Configuration

All settings live in `.env`. Key options:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Your OpenAI API key (required) |
| `AI_PROVIDER` | `openai` | `openai` or `anthropic` |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |
| `TTS_VOICE` | `en-US-AriaNeural` | Edge TTS voice name |
| `STT_ENGINE` | `whisper-api` | `whisper-api` or `whisper-local` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_CONVERSATION_HISTORY` | `20` | Messages kept in memory |

---

## 🧪 Running Tests

```bash
pip install -r requirements-dev.txt
pytest --cov=src --cov-report=term-missing
```

---

## 🗺️ Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 | 🔄 In Progress | Python desktop prototype (OpenAI + Voice) |
| 2 | ⏳ Planned | FastAPI backend + Claude API integration |
| 3 | ⏳ Planned | Flutter mobile app (Android + iOS) |
| 4 | ⏳ Planned | App Store launch (Google Play + Apple) |

---

## 📄 License

MIT © Sravan Kumar Yenikapati
