# Architecture Overview

## Design Principles

1. **Provider-agnostic brain** — the AI model is behind an interface. Swapping OpenAI for Claude requires only a `.env` change.
2. **Mode-mirroring I/O** — voice input → voice output. Text input → text output. The `input_was_voice` flag routes the output.
3. **Backend-first** — the AI brain lives in a FastAPI server from Phase 2 onwards. Desktop and mobile are both just frontends.
4. **No secrets in code** — all API keys and config live in `.env`, never committed to git.

## Module Map

```
main.py
└── launches one of:
    ├── ui/desktop.py        (Phase 1 — Tkinter UI)
    ├── api/server.py        (Phase 2 — FastAPI backend)
    └── CLI REPL             (dev/debug)

ui/desktop.py  ──────────────────────────────────────┐
api/server.py  ──── both call ──► core/brain.py      │
                                       │              │
                              core/conversation.py    │
                              (rolling message window)│
                                                      │
audio/stt.py ◄──── voice input ──────────────────────┘
audio/tts.py ◄──── voice output ─────────────────────┘

config.py ← loaded by everything via get_settings()
logger.py  ← used by everything via get_logger(__name__)
```

## Data Flow

### Text Mode
```
User types → desktop.py._on_send()
           → brain.chat(text)
           → OpenAIProvider.complete(messages)
           → reply text appended to chat display
```

### Voice Mode
```
User presses mic → stt.transcribe()
                 → brain.chat(transcription)
                 → OpenAIProvider.complete(messages)
                 → tts.speak(reply)           # voice output
                 → reply also shown in chat   # text fallback
```

## Phase Transition Plan

| From | To | Change |
|---|---|---|
| Phase 1 → Phase 2 | Add FastAPI server | Extract brain into `api/server.py`, keep desktop UI |
| Phase 2 → Phase 3 | Add Flutter mobile | Mobile calls `/chat` endpoint, same server |
| OpenAI → Claude | Config only | Set `AI_PROVIDER=anthropic` in `.env` |
