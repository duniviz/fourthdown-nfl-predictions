#!/usr/bin/env bash
# Only stage this writer's declared output. Retry races on unrelated commits.
set -euo pipefail
message=$1
shift
for path in "$@"; do
  if [[ -f "$path" ]]; then git add -- "$path"; fi
done
if git diff --cached --quiet; then exit 0; fi
git -c user.name=github-actions -c user.email=github-actions[bot]@users.noreply.github.com commit -m "$message"
for attempt in 1 2 3 4 5; do
  git fetch origin main
  git -c user.name=github-actions -c user.email=github-actions[bot]@users.noreply.github.com rebase --autostash FETCH_HEAD
  if git push origin HEAD:main; then exit 0; fi
  sleep "$attempt"
done
exit 1
