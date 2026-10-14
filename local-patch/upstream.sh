#!/bin/bash
set -euo pipefail
repository_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repository_root"
mode=${1:-check}
patch_branch=codex/ultrafast-cost-pricing
case "$mode" in
  check)
    git fetch upstream --tags
    printf 'Current branch: %s\n' "$(git branch --show-current)"
    printf 'Upstream main: %s\n' "$(git log -1 --format='%h %s' upstream/main)"
    printf 'Changes since merge base: %s\n' "$(git rev-list --count HEAD..upstream/main)"
    if command -v gh >/dev/null 2>&1; then
      gh api repos/steipete/CodexBar/releases/latest --jq '"Latest release: " + .tag_name + "  " + .html_url'
    fi
    ;;
  merge)
    reference=${2:?Usage: upstream.sh merge vX.Y.Z}
    [[ "$reference" != -* ]] || { echo 'Invalid reference' >&2; exit 2; }
    [[ "$(git branch --show-current)" == "$patch_branch" ]] || { echo "Switch to $patch_branch first" >&2; exit 2; }
    [[ -z "$(git status --porcelain)" ]] || { echo 'Commit or preserve local changes first' >&2; exit 2; }
    git fetch upstream --tags
    target=$(git rev-parse --verify --end-of-options "${reference}^{commit}")
    checkpoint="codex/backup-before-upstream-$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"
    git branch "$checkpoint" HEAD
    printf 'Recovery branch: %s\n' "$checkpoint"
    git merge --no-ff --no-edit "$target"
    printf 'Review, run focused pricing tests, build and install before pushing.\n'
    ;;
  mirror)
    [[ -z "$(git status --porcelain)" ]] || { echo 'Commit or preserve local changes first' >&2; exit 2; }
    git fetch upstream --tags
    if [[ "$(git branch --show-current)" == main ]]; then
      git merge --ff-only upstream/main
    elif git show-ref --verify --quiet refs/heads/main; then
      previous=$(git rev-parse main)
      git merge-base --is-ancestor "$previous" upstream/main || { echo 'main contains local commits; preserve them before mirroring' >&2; exit 2; }
      git update-ref refs/heads/main "$(git rev-parse upstream/main)" "$previous"
    else
      git branch main upstream/main
    fi
    git push origin main:main
    ;;
  *) echo 'Usage: upstream.sh [check | mirror | merge vX.Y.Z]' >&2; exit 2 ;;
esac
