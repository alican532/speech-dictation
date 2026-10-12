#!/bin/sh
set -e
SRC=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/SpeechDictation"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_SRC=""

if [ ! -x "$SRC/SpeechDictation" ]; then
  echo "SpeechDictation binary not found next to install.sh" >&2
  exit 1
fi

mkdir -p "$DEST" "$BIN_DIR" "$APP_DIR"
# Keep the installed tree replaceable by the in-app updater.
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$SRC"/. "$DEST"/
chmod +x "$DEST/SpeechDictation" "$DEST/install.sh" "$DEST/uninstall.sh" 2>/dev/null || true

if [ -f "$DEST/assets/icon.png" ]; then
  ICON_SRC="$DEST/assets/icon.png"
elif [ -f "$DEST/_internal/assets/icon.png" ]; then
  ICON_SRC="$DEST/_internal/assets/icon.png"
fi

cat > "$APP_DIR/speech-dictation.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SpeechDictation
Comment=Tray dictation with Groq Whisper and Gemini
Exec=$DEST/SpeechDictation
Icon=${ICON_SRC:-speech-dictation}
Terminal=false
Categories=Utility;AudioVideo;
StartupNotify=false
EOF

ln -sfn "$DEST/SpeechDictation" "$BIN_DIR/speech-dictation"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo "Add $BIN_DIR to your PATH if the command is not found."
    ;;
esac

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "Installed to $DEST"
echo "Start from the app menu, or run: speech-dictation"
echo "Uninstall with: $DEST/uninstall.sh"
