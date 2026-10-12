#!/bin/sh
set -e
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/SpeechDictation"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

rm -f "$BIN_DIR/speech-dictation"
rm -f "$APP_DIR/speech-dictation.desktop"
rm -rf "$DEST"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "SpeechDictation removed."
