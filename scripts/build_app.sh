#!/bin/bash
# Builds "Voice Typer.app", a double-clickable launcher for this project (macOS).
# Usage: scripts/build_app.sh [destination-folder]   (default: ~/Desktop)
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$HOME/Desktop}"
APP="$DEST/Voice Typer.app"
PY="$PROJECT/.venv/bin/python"

[ -x "$PY" ] || { echo "Missing $PY. Create the venv and install requirements first (see README)."; exit 1; }

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

mkdir -p "$PROJECT/assets"
"$PY" "$PROJECT/scripts/make_icon.py" "$PROJECT/assets/AppIcon.icns"   # also used for the Dock icon
cp "$PROJECT/assets/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Voice Typer</string>
  <key>CFBundleDisplayName</key><string>Voice Typer</string>
  <key>CFBundleIdentifier</key><string>com.voicetyper.app</string>
  <key>CFBundleExecutable</key><string>VoiceTyper</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Voice Typer records your voice to transcribe it.</string>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/VoiceTyper" <<LAUNCH
#!/bin/bash
# Don't start a second copy if one is already running.
pgrep -f "$PROJECT/main.py" >/dev/null && exit 0
cd "$PROJECT"
exec "$PY" -u "$PROJECT/main.py" >> "\$HOME/Library/Logs/voice-typer.log" 2>&1
LAUNCH
chmod +x "$APP/Contents/MacOS/VoiceTyper"

# Ad-hoc signature so macOS keeps the permissions you grant to this app.
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || echo "warning: codesign failed"
echo "Built: $APP"
