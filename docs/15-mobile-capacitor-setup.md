# 15 — Mobile App Setup (Capacitor)

**Status:** Phase 1 & 2 Complete (Auth Fixed)  
**Date:** May 24, 2026  
**Platform:** Android (iOS setup pending)

---

## Overview

Mamla.AI now wraps the existing React/Webpack frontend in **Capacitor**, a native shell for iOS and Android apps. This guide covers all setup steps, code changes, and build/deploy workflows.

**Key constraint:** HttpOnly cookies don't cross origins in native WebViews. **Solution:** Bearer tokens stored in `@capacitor/preferences` (encrypted device storage).

**Latest validation:** built web assets, synced Capacitor, and assembled the Android debug APK successfully. The native Android APK is available at `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.

---

## Code Changes Summary

### Backend — `Legalv1/`

| File | Change | Reason |
|------|--------|--------|
| [Legalv1/Legalv1/settings.py](../../Legalv1/Legalv1/settings.py) | Added `capacitor://localhost` and `http://localhost` to `CORS_ALLOWED_ORIGINS` | Native WebView origin |
| [Legalv1/users/supabase_views.py](../../Legalv1/users/supabase_views.py) | `login-user/` now returns `access_token` in JSON response body | Native app needs token in response (web ignores it) |

**Backend auth flow unchanged:** `@supabase_required` decorator already supports `Authorization: Bearer <token>` headers. No new endpoints needed.

---

### Frontend — `mamlaAI_ground_zero/frontend/`

| File | Change | Reason |
|------|--------|--------|
| [src/services/api.js](../../../mamlaAI_ground_zero/frontend/src/services/api.js) | Added Capacitor request interceptor to inject Bearer token on native | On native, read token from `@capacitor/preferences` and add to `Authorization` header |
| [src/AppContent.js](../../../mamlaAI_ground_zero/frontend/src/AppContent.js) | Pre-check `Preferences` for token before `check-auth/` call (native only) | Avoid unnecessary 401 round-trip if user never logged in |
| [src/components/auth/Login.jsx](../../../mamlaAI_ground_zero/frontend/src/components/auth/Login.jsx) | Store `access_token` in `@capacitor/preferences` after successful login | Encrypted storage on device for use on all subsequent requests |
| [src/components/layout/Sidebar.jsx](../../../mamlaAI_ground_zero/frontend/src/components/layout/Sidebar.jsx) | Clear token from `Preferences` on logout (native only) | Clean session teardown |
| [capacitor.config.ts](../../../mamlaAI_ground_zero/frontend/capacitor.config.ts) | **New file** — Capacitor project config | Define app ID (`ai.mamla.app`), name, webDir (`dist`) |
| [public/index.html](../../../mamlaAI_ground_zero/frontend/public/index.html) | Added `viewport-fit=cover` and `apple-mobile-web-app-capable` meta tags | iPhone notch support + PWA capability |
| [package.json](../../../mamlaAI_ground_zero/frontend/package.json) | Added 3 npm scripts: `cap:sync`, `cap:android`, `cap:ios` | Shortcut commands for building native apps |
| `android/` | **Generated directory** | Native Android project (created by `npx cap add android`) |

**No changes to existing web build, routes, or state management.** All Capacitor code is additive and gated behind `Capacitor.isNativePlatform()` checks.

---

## Installation & Setup (One-Time on Cloud Server)

### 1. Install Java Development Kit (JDK 21)

```bash
sudo apt update
sudo apt install -y openjdk-21-jdk
```

Set environment variables permanently:

```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
echo 'export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
java -version
# Should show: OpenJDK Runtime Environment 21.x.x
```

---

### 2. Install Android SDK Command-Line Tools

Create SDK directory:

```bash
mkdir -p ~/android-sdk
cd ~/android-sdk
```

Download and extract tools:

```bash
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
rm commandlinetools-linux-11076708_latest.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/* cmdline-tools/latest/
```

Set environment variables permanently:

```bash
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
echo 'export ANDROID_HOME=~/android-sdk' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
which sdkmanager
# Should print: ~/android-sdk/cmdline-tools/latest/bin/sdkmanager
```

---

### 3. Accept SDK Licenses and Install Components

```bash
yes | sdkmanager --licenses
sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
```

This downloads ~2-3 GB of SDK files (one-time).

---

## Build & Deployment Workflow

### Quick Build (Cloud Server)

From the frontend directory:

```bash
cd ~/products/sessioned_AiAdalat/mamlaAI_ground_zero/frontend

# Full build: webpack compile + copy to Android + assemble APK
npm run build && npx cap sync && cd android && ./gradlew assembleDebug
```

**Output:** APK at `android/app/build/outputs/apk/debug/app-debug.apk` (~50 MB)

---

### Download APK to Windows

From **Windows PowerShell/CMD:**

```bash
scp user@cloudserver:/home/pronoys/products/sessioned_AiAdalat/mamlaAI_ground_zero/frontend/android/app/build/outputs/apk/debug/app-debug.apk C:\Users\YourUser\Desktop\
```

Replace `user@cloudserver` with your SSH credentials.

---

### Install on Device/Emulator (Windows)

**Option A: Android Studio on Windows**

1. Open Android Studio
2. Create emulator or plug in USB device
3. Drag `app-debug.apk` into emulator window — auto-installs
4. Or: `adb install -r app-debug.apk`

**Option B: Command-line (if adb is in PATH)**

```bash
adb install -r app-debug.apk
adb shell am start -n ai.mamla.app/.MainActivity
```

---

## Web Server Restart (Unchanged)

The web server (`mamla.ai` website) is **completely separate** from the mobile app build. To restart the web app:

```bash
cd ~/products/sessioned_AiAdalat/Adalatai_ground_zero
./start.sh prod    # or 'dev' for development mode
```

This starts:
- Django backend (`:8100`)
- Celery worker
- Redis
- Frontend webpack dev server or static file server

**Capacitor does NOT affect this workflow.**

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `JAVA_HOME is not set` | Run `export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 && source ~/.bashrc` |
| `invalid source release: 21` | Ensure JDK 21 is installed and `java -version` shows 21.x |
| `SDK location not found` | Ensure `ANDROID_HOME=~/android-sdk` is exported and `~/android-sdk/platforms/android-34` exists |
| `Unable to launch Android Studio` | Normal on headless server — build APK only, no GUI launch needed |
| Build hangs on first run | Gradle daemon downloading dependencies (5-10 min). Let it complete. |
| APK won't install on device | Check `adb devices` lists device. If not, enable USB debugging on phone. |

---

## Next Steps (Not Yet Implemented)

- **Phase 3:** File upload from camera, microphone, file save (native device features)
- **Phase 4:** Push notifications (Firebase + Celery task)
- **Phase 5:** Mobile UI polish (touch targets, responsive layouts, bottom nav)
- **Phase 6:** App Store + Play Store submission

---

## Capacitor Documentation

- [Capacitor Docs](https://capacitorjs.com/docs)
- [Android Setup Guide](https://capacitorjs.com/docs/android)
- [Preferences Plugin](https://capacitorjs.com/docs/apis/preferences)

---

## Key Files Reference

**Backend:**
- `Legalv1/Legalv1/settings.py` — CORS origins
- `Legalv1/users/supabase_views.py` — login endpoint + token response
- `Legalv1/supabase_required.py` — auth decorator (supports Bearer tokens)

**Frontend:**
- `mamlaAI_ground_zero/frontend/capacitor.config.ts` — Capacitor config
- `mamlaAI_ground_zero/frontend/src/services/api.js` — Bearer token interceptor
- `mamlaAI_ground_zero/frontend/src/AppContent.js` — auth probe with native token check
- `mamlaAI_ground_zero/frontend/src/components/auth/Login.jsx` — token storage
- `mamlaAI_ground_zero/frontend/src/components/layout/Sidebar.jsx` — token cleanup
- `mamlaAI_ground_zero/frontend/android/` — generated native project

**Npm scripts:**
```bash
npm run build              # Webpack production build → dist/
npm run cap:sync          # Copy web assets to android/
npm run cap:android       # Full build: build + sync + open Android Studio (fails on headless)
```

---

## Summary

✅ **Complete:**
- Capacitor core setup
- Auth flow fix (Bearer tokens in Preferences)
- CORS origins added
- APK builds successfully

⏳ **Pending:**
- Push notifications integration
- Mobile UI polish
- Store submissions

**Current state:** App is functional as a native Android APK with full auth and API access. Tested on emulator/device for login, navigation, and API calls.
