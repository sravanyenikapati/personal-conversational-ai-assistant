# 🤖 Personal Conversational AI Assistant

A full-stack personal AI assistant with **voice + text I/O**, a **multi-agent FastAPI backend**, and a **Flutter mobile app** — built from scratch and deploying to Google Play & App Store.

> **Stack:** Python · FastAPI · Flutter · OpenAI GPT-4o · Whisper STT · Edge TTS · Railway

---

## 🚦 Project Status

| Phase | Status | What was built |
|---|---|---|
| **1 — Desktop Prototype** | ✅ Complete | Python + Tkinter UI, OpenAI brain, Whisper STT, Edge TTS, voice/text adaptive I/O |
| **2 — FastAPI Backend** | ✅ Complete | Multi-agent router, streaming pipeline, 5 specialist agents, REST API |
| **3 — Flutter Mobile App** | ✅ Complete | Android + iOS app, chat UI, voice mic button, real-time streaming, Aurora Dark theme |
| **4 — Custom Agents** | ✅ Complete | CRUD custom-agent system, JSON persistence, create/select agent UI in Flutter |
| **5 — Deploy to Production** | 🔄 In Progress | Railway backend deployment (blocked on billing upgrade), Google Play submission |

---

## ✨ Features

- 🎤 **Voice input** — OpenAI Whisper speech-to-text
- 🔊 **Voice output** — Edge TTS (natural voices, no extra API key)
- 🔀 **Adaptive I/O** — voice in → voice out, text in → text out
- 🧠 **Multi-agent brain** — specialist agents (general, code, writing, research, math)
- 🛠️ **Custom agents** — create your own agents with name, role, and system prompt
- 📡 **Streaming responses** — real-time token streaming to Flutter UI
- 🗂️ **Conversation memory** — full context maintained per session
- 🔌 **Provider-agnostic** — swap OpenAI ↔ Anthropic via one config line
- 📱 **Mobile-first UI** — Flutter app with Aurora Dark theme (#3DF5B8 mint on #080D12 navy)

---

## 🏗️ Architecture

```
personal-ai-assistant/
├── src/assistant/
│   ├── config.py              # Pydantic settings from .env
│   ├── logger.py              # Rich structured logging
│   ├── core/
│   │   ├── brain.py           # OpenAI / Anthropic abstraction
│   │   ├── conversation.py    # Conversation history manager
│   │   └── streaming.py       # Real-time token streaming pipeline
│   ├── audio/
│   │   ├── stt.py             # Whisper speech-to-text
│   │   └── tts.py             # Edge TTS text-to-speech
│   ├── agents/
│   │   ├── router.py          # Multi-agent routing logic
│   │   ├── prompts.py         # System prompts for each agent
│   │   ├── store.py           # Built-in agent registry
│   │   └── custom_store.py    # Custom agent CRUD + JSON persistence
│   ├── ui/
│   │   └── desktop.py         # Tkinter desktop UI
│   └── api/
│       └── server.py          # FastAPI backend (14+ endpoints)
├── flutter_app/
│   └── lib/
│       ├── main.dart
│       ├── theme/aurora_theme.dart
│       ├── screens/
│       │   ├── chat_screen.dart
│       │   ├── settings_screen.dart
│       │   └── create_agent_screen.dart
│       ├── widgets/
│       │   ├── chat_bubble.dart
│       │   ├── mic_button.dart
│       │   └── agent_selector.dart
│       ├── models/
│       │   ├── message.dart
│       │   └── agent.dart
│       ├── services/api_service.dart
│       └── providers/chat_provider.dart
├── tests/                     # Pytest suite (>45% coverage)
├── .github/workflows/         # CI — lint + test on every push
├── Dockerfile                 # Production container
├── nixpacks.toml              # Railway Railpack build config
├── railway.toml               # Railway deploy config
└── main.py                    # Entry point (--cli / --api / --debug)
```

---

## 🚀 Quick Start (Local)

### Backend

```bash
git clone https://github.com/sravanyenikapati/personal-conversational-ai-assistant.git
cd personal-conversational-ai-assistant

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .

cp .env.example .env
# Add your OPENAI_API_KEY to .env

python main.py          # Desktop UI
python main.py --api    # FastAPI server on :8000
python main.py --cli    # Terminal REPL
```

### Flutter App

```bash
cd flutter_app
flutter pub get
flutter run                          # Debug on connected device
flutter build apk --release          # Android APK
flutter build appbundle --release    # Android AAB (Play Store)
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Single-turn chat |
| `POST` | `/chat/stream` | Streaming chat (SSE) |
| `GET` | `/agents` | List all agents |
| `POST` | `/agents/{id}/chat` | Chat with a specific agent |
| `GET` | `/agents/custom` | List custom agents |
| `POST` | `/agents/custom` | Create a custom agent |
| `PUT` | `/agents/custom/{id}` | Update a custom agent |
| `DELETE` | `/agents/custom/{id}` | Delete a custom agent |

**Production URL:** `https://api-backend-production-6c38.up.railway.app`

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `AI_PROVIDER` | `openai` | `openai` or `anthropic` |
| `OPENAI_MODEL` | `gpt-4o` | Model name |
| `TTS_VOICE` | `en-US-AriaNeural` | Edge TTS voice |
| `STT_ENGINE` | `whisper-api` | `whisper-api` or `whisper-local` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_CONVERSATION_HISTORY` | `20` | Messages kept in memory |

---

## 🧪 Tests & CI

```bash
pip install -r requirements-dev.txt
pytest --cov=src --cov-report=term-missing
```

CI runs on every push via GitHub Actions — lints with **Ruff**, type-checks with **Mypy**, and runs the full Pytest suite.

---

## 📱 Mobile App

The Flutter app targets Android (API 21+) and iOS (14+).

- **Theme:** Aurora Dark — `#3DF5B8` mint accent on `#080D12` deep navy
- **Voice:** hold mic button to record, release to transcribe and send
- **Streaming:** responses appear word-by-word in real time
- **Agents:** switch between built-in specialist agents or create custom ones

---

## 🗺️ What's Next

- [ ] Railway Hobby plan upgrade → backend goes live
- [ ] Set `OPENAI_API_KEY` in Railway dashboard → Variables
- [ ] Build Flutter release AAB + submit to Google Play
- [ ] iOS build on macOS + submit to App Store
- [ ] Host privacy policy on GitHub Pages

---

## 📄 License

MIT © Sravan Kumar Yenikapati
