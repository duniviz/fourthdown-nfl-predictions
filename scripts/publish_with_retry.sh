#!/usr/bin/env bash
# Rebase generated commits onto the latest target branch and retry a push if
# another scheduled publisher updates the branch between fetch and push.
set -euo pipefail

remote="${1:-origin}"
target_branch="${2:-main}"
max_attempts=5

for attempt in $(seq 1 "$max_attempts"); do
  if ! git -c rebase.autoStash=true pull --rebase "$remote" "$target_branch"; then
    git rebase --abort >/dev/null 2>&1 || true
    if [ "$attempt" -eq "$max_attempts" ]; then
      echo "::error::Could not rebase generated commit onto $remote/$target_branch after $max_attempts attempts."
      exit 1
    fi
    echo "Rebase attempt $attempt/$max_attempts failed; retrying after refreshing the target branch."
    sleep "$attempt"
    continue
  fi

  if git push "$remote" "HEAD:$target_branch"; then
    exit 0
  fi

  if [ "$attempt" -lt "$max_attempts" ]; then
    echo "Push attempt $attempt/$max_attempts lost a concurrent update; rebasing and retrying."
    sleep "$attempt"
  fi
done

echo "::error::Could not publish generated commit to $remote/$target_branch after $max_attempts attempts."
exit 1
