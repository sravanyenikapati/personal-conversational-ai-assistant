# Phase 5 — App Store Launch Guide

Complete step-by-step checklist to go from working code to live on Google Play and Apple App Store.

---

## Step 0 — Push Pending Commit

From PowerShell in the project folder:
```powershell
git push origin main
```

---

## Step 1 — Deploy Backend to Railway (Free)

### 1.1 Create Railway account
1. Go to https://railway.app and sign up with GitHub.

### 1.2 Deploy
1. Click **New Project → Deploy from GitHub repo**.
2. Select `personal-conversational-ai-assistant`.
3. Railway auto-detects the `Dockerfile` and builds it.

### 1.3 Set environment variables in Railway dashboard
Go to your service → **Variables** tab and add:
```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...your-real-key...
LOG_LEVEL=INFO
CUSTOM_AGENTS_DIR=/data
```

### 1.4 Add persistent storage (for custom agents)
1. In Railway: **New → Volume** → mount at `/data`.
2. This keeps custom agents alive across deploys.

### 1.5 Get your public URL
Railway gives you a URL like `https://personal-ai-api.up.railway.app`.
Copy it — you'll need it for the Flutter build.

### 1.6 Test the deployment
```bash
curl https://personal-ai-api.up.railway.app/health
# Expected: {"status":"ok","custom_agent_count":0,...}
```

---

## Step 2 — Set Up Flutter Project (First Time)

You need Flutter installed: https://docs.flutter.dev/get-started/install

```powershell
cd "C:\Users\srava\OneDrive\Documents\Claude\Projects\Personal Conversational AI Assistant\flutter_app"

# Create full Flutter project scaffold (run once)
flutter create . --org com.sravany --project-name ai_assistant

# The lib/ folder already has all source files — Flutter create won't overwrite them.

# Install dependencies
flutter pub get
```

---

## Step 3 — Generate App Icons and Splash Screens

The icon source files are already in `flutter_app/assets/icon/`.

```powershell
cd flutter_app

# Generate icons for Android + iOS + Web
flutter pub run flutter_launcher_icons

# Generate splash screens
flutter pub run flutter_native_splash:create
```

---

## Step 4 — Android Release Build

### 4.1 Create signing keystore (run once — save this file securely!)
```powershell
keytool -genkey -v -keystore upload-keystore.jks `
  -keyalg RSA -keysize 2048 -validity 10000 `
  -alias upload `
  -storepass YOUR_STORE_PASS `
  -keypass YOUR_KEY_PASS
```
Move `upload-keystore.jks` to `flutter_app/android/app/upload-keystore.jks`.

### 4.2 Create key.properties
```powershell
Copy-Item android\key.properties.example android\key.properties
# Edit key.properties with your actual passwords
notepad android\key.properties
```

### 4.3 Update android/app/build.gradle (add signing config)
Open `android/app/build.gradle` and add this block before the `android {` block:

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    // ... existing config ...

    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
        }
    }
}
```

### 4.4 Build release AAB (App Bundle — required for Play Store)
```powershell
flutter build appbundle --release `
  --dart-define=API_URL=https://personal-ai-api.up.railway.app
```
Output: `build/app/outputs/bundle/release/app-release.aab`

### 4.5 (Optional) Build APK for direct testing
```powershell
flutter build apk --release `
  --dart-define=API_URL=https://personal-ai-api.up.railway.app
```

---

## Step 5 — Submit to Google Play

1. Create a developer account at https://play.google.com/console ($25 one-time).
2. Create a new app → fill in store listing using `docs/store_listing.md`.
3. Upload `app-release.aab` under **Production → Create new release**.
4. Upload screenshots (5 from the storyboard in store_listing.md).
5. Add Privacy Policy URL (see Step 7 below).
6. Fill in Content Rating questionnaire (see store_listing.md).
7. Submit for review — typically 1–3 days.

---

## Step 6 — iOS Build (requires macOS + Xcode)

### 6.1 Prerequisites
- macOS machine with Xcode 15+
- Apple Developer account ($99/year): https://developer.apple.com

### 6.2 Configure bundle identifier
In Xcode, open `flutter_app/ios/Runner.xcworkspace`.
Set bundle identifier to `com.sravany.aiassistant` (or your chosen ID).

### 6.3 Build release IPA
```bash
flutter build ipa --release \
  --dart-define=API_URL=https://personal-ai-api.up.railway.app
```

### 6.4 Submit via Xcode / Transporter
Upload to App Store Connect and fill in the listing using `docs/store_listing.md`.
Review typically takes 1–2 days.

---

## Step 7 — Host Privacy Policy

You need a public URL for the privacy policy. Easiest option — GitHub Pages:

1. Go to your GitHub repo → **Settings → Pages**.
2. Set source to `main` branch, `/docs` folder.
3. Your policy will be live at:
   `https://sravanyenikapati.github.io/personal-conversational-ai-assistant/privacy_policy.html`
4. Use this URL in both store listings.

---

## Step 8 — Post-Launch

- Monitor crash reports and reviews.
- Tag the release: `git tag v0.5.0 && git push origin v0.5.0`
- Consider adding Firebase Analytics for usage insights (Phase 6).
- Consider Firebase Auth for user accounts across devices (Phase 6).

---

## Quick Reference — Build Commands

| Target | Command |
|--------|---------|
| Android AAB (Play Store) | `flutter build appbundle --release --dart-define=API_URL=https://...` |
| Android APK (testing) | `flutter build apk --release --dart-define=API_URL=https://...` |
| iOS (macOS only) | `flutter build ipa --release --dart-define=API_URL=https://...` |
| Web | `flutter build web --dart-define=API_URL=https://...` |
| Icons | `flutter pub run flutter_launcher_icons` |
| Splash | `flutter pub run flutter_native_splash:create` |
| Backend (local Docker) | `docker-compose up --build` |

---

## Files Created in Phase 5

| File | Purpose |
|------|---------|
| `Dockerfile` | Containerized backend for cloud deployment |
| `docker-compose.yml` | Local production-like testing |
| `railway.toml` | One-click Railway deployment |
| `.env.production.example` | Server environment variable template |
| `flutter_app/assets/icon/app_icon.png` | 1024×1024 app icon |
| `flutter_app/assets/icon/splash_logo.png` | Splash screen logo |
| `flutter_app/pubspec.yaml` | Updated with icon/splash packages |
| `flutter_app/android/key.properties.example` | Signing keystore template |
| `docs/privacy_policy.html` | Privacy policy (required by both stores) |
| `docs/store_listing.md` | App store descriptions, keywords, screenshots plan |
| `docs/LAUNCH_GUIDE.md` | This file |
