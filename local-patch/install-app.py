"""Install or restore a complete, signed local CodexBar bundle with recoverable backups."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import plistlib
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("candidate", nargs="?", default=str(root / "CodexBar.app"))
args = parser.parse_args()
candidate = Path(args.candidate).expanduser().resolve()
destination = Path("/Applications/CodexBar.app")
if candidate == destination.resolve():
    raise SystemExit("Candidate must be separate from the installed bundle")
info = plistlib.loads((candidate / "Contents/Info.plist").read_bytes())
if info.get("CFBundleIdentifier") != "com.steipete.codexbar":
    raise SystemExit("Candidate is not the main CodexBar application")
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(candidate)], check=True)
backup_root = Path.home() / "Library/Application Support/CodexBar/LocalPatchBackups"
backup_root.mkdir(parents=True, exist_ok=True)
backup_root.chmod(0o700)
backup = backup_root / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
backup.mkdir(mode=0o700)
old_bundle = backup / "replaced-install.app"
if destination.exists():
    subprocess.run(["ditto", str(destination), str(backup / "CodexBar.app")], check=True)
subprocess.run(["osascript", "-e", 'tell application id "com.steipete.codexbar" to quit'], check=True)
if destination.exists():
    destination.rename(old_bundle)
try:
    subprocess.run(["ditto", str(candidate), str(destination)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(destination)], check=True)
    subprocess.run(["open", str(destination)], check=True)
except Exception:
    if destination.exists():
        destination.rename(backup / "failed-candidate.app")
    if old_bundle.exists():
        old_bundle.rename(destination)
        subprocess.run(["open", str(destination)], check=False)
    raise
state_file = root / "local-patch/install-state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {}
state.setdefault("original_app_backup", str(backup / "CodexBar.app"))
state.setdefault("backups", []).append(str(backup / "CodexBar.app"))
state.update({
    "installed_app": str(destination),
    "installed_version": info.get("CFBundleShortVersionString"),
    "pricing_policy": info.get("CodexBarLocalPricingPolicy"),
    "signature_verified": True,
    "installed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
    "binary_sha256": {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in ("Contents/MacOS/CodexBar", "Contents/Helpers/CodexBarCLI")
    },
})
state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
print(f"Installed {destination}; backup: {backup / 'CodexBar.app'}")
