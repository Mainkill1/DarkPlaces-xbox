#!/usr/bin/env bash
set -euo pipefail

token="${WIKI_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "${token}" ]]; then
  echo "No WIKI_TOKEN or GITHUB_TOKEN is available." >&2
  exit 1
fi

repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
remote="https://x-access-token:${token}@github.com/${repo}.wiki.git"
workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

if ! git clone "${remote}" "${workdir}/wiki"; then
  cat >&2 <<'EOF'
The GitHub Wiki Git repository is not initialized or the token cannot write it.
Open the repository Wiki tab, create a single temporary Home page, then rerun
this workflow. If the built-in token is rejected, add a WIKI_TOKEN repository
secret with permission to write this repository.
EOF
  exit 1
fi

find "${workdir}/wiki" -mindepth 1 -maxdepth 1 \
  ! -name .git -exec rm -rf {} +
cp -a wiki/. "${workdir}/wiki/"

cd "${workdir}/wiki"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A

if git diff --cached --quiet; then
  echo "Wiki is already synchronized."
  exit 0
fi

git commit -m "Sync Xbox port wiki from ${GITHUB_SHA:-manual run}"
git push origin HEAD:master
