#!/bin/bash
set -euo pipefail
patch_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$patch_root"
export PATH="$patch_root/local-patch/toolchain/bin:$PATH"
export CODEXBAR_MACOS_SDK_PATH=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
export CODEXBAR_EXISTING_WIDGET_EXTENSION=${CODEXBAR_EXISTING_WIDGET_EXTENSION:-/Applications/CodexBar.app/Contents/PlugIns/CodexBarWidget.appex}
export XCODE_DEFAULT_TOOLCHAIN_OVERRIDE=/Library/Developer/CommandLineTools
swift package resolve
python3 local-patch/prepare-build.py
CODEXBAR_SIGNING=adhoc ./Scripts/package_app.sh release
# Vortex assets are unchanged; use the installed compiled asset catalog.
ditto /Applications/CodexBar.app/Contents/Resources/Vortex_Vortex.bundle CodexBar.app/Contents/Resources/Vortex_Vortex.bundle
python3 - <<'MARKER'
from pathlib import Path
import plistlib
info = Path("CodexBar.app/Contents/Info.plist")
data = plistlib.loads(info.read_bytes())
data["CodexBarLocalPricingPolicy"] = "ChatGPT subscription token history; separate API estimates only"
info.write_bytes(plistlib.dumps(data))
MARKER
codesign --force --sign - CodexBar.app/Contents/Resources/Vortex_Vortex.bundle
codesign --force --sign - --preserve-metadata=entitlements CodexBar.app
codesign --verify --deep --strict CodexBar.app
