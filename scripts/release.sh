#!/usr/bin/env bash
set -euo pipefail

# Simple release script using conventional-changelog-cli and npm version/tagging.
# Usage:
#   ./scripts/release.sh [major|minor|patch]
#   ./scripts/release.sh set <version>

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CMD=${1:-}

function usage() {
  echo "Usage: $0 [major|minor|patch|set <version>]"
  exit 2
}

if [ -z "$CMD" ]; then
  usage
fi

if [ "$CMD" = "set" ]; then
  if [ $# -lt 2 ]; then
    echo "set requires a version argument, e.g. ./scripts/release.sh set 1.2.3"
    exit 2
  fi
  NEW_VERSION="$2"
  echo "Setting version to $NEW_VERSION"
  npm version --no-git-tag-version "$NEW_VERSION"
else
  case "$CMD" in
    major|minor|patch)
      echo "Bumping $CMD version"
      npm version --no-git-tag-version "$CMD"
      ;;
    *)
      usage
      ;;
  esac
fi

# Generate or update CHANGELOG.md using conventional-changelog
npx conventional-changelog -p angular -i CHANGELOG.md -s || true

# Commit version change and changelog
git add package.json CHANGELOG.md
git commit -m "chore(release): bump version to $(node -p "require('./package.json').version")" || true

# Create annotated tag
TAG="v$(node -p "require('./package.json').version")"
git tag -a "$TAG" -m "Release $TAG" || true

echo "Created tag $TAG"
echo "Push with: git push origin --tags && git push"
