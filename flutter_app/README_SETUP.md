# Flutter App — Phase 3 Setup

## Quick start

```bash
# 1. Create the Flutter project shell (run once)
flutter create --org com.sravank --project-name ai_assistant flutter_app_shell
cd flutter_app_shell

# 2. Copy our source files over the generated scaffold
cp -r ../flutter_app/lib ./
cp ../flutter_app/pubspec.yaml ./

# 3. Install dependencies
flutter pub get

# 4. Add Android permissions
# Edit android/app/src/main/AndroidManifest.xml — see android_permissions_snippet.xml

# 5. Start the backend
cd ../../
uvicorn assistant.api.server:app --host 0.0.0.0 --port 8000 --reload

# 6. Run the app
cd flutter_app_shell
flutter run
```

## Backend URL

| Target | URL |
|---|---|
| Android emulator | `http://10.0.2.2:8000` (default) |
| Physical Android/iOS | `http://<your-computer-ip>:8000` |
| iOS simulator | `http://localhost:8000` |

Change it in the app under **⋮ → Settings**.

## Architecture

```
lib/
  main.dart                 App entry, providers, theme wiring
  theme/aurora_theme.dart   Aurora Dark palette (#3DF5B8 / #080D12)
  models/
    message.dart            Chat message model
    agent.dart              Agent model + defaults
  services/
    api_service.dart        HTTP + SSE streaming client
  providers/
    chat_provider.dart      ChangeNotifier: messages, STT, TTS, agents
  screens/
    chat_screen.dart        Main chat UI
    settings_screen.dart    Backend URL + voice preferences
  widgets/
    agent_selector.dart     Horizontal chip row
    chat_bubble.dart        Streaming bubble with cursor + typing dots
    mic_button.dart         Animated mic with pulse rings
```

## Features

- ✅ Aurora Dark theme — `#3DF5B8` mint on `#080D12` navy
- ✅ SSE streaming — text appears token-by-token, no wait
- ✅ TTS — speaks each sentence as it arrives (~0.5s latency)
- ✅ STT — tap mic, speak, auto-sends
- ✅ 9 specialist agents — switch with one tap
- ✅ Session management — clear history per-agent or all at once
- ✅ Backend health indicator — green dot = online
