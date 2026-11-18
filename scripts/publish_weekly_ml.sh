#!/usr/bin/env bash
# Publish the already-committed weekly ML data without overwriting fresher
# production ledgers that a concurrent forecast may have published.
set -euo pipefail
for attempt in 1 2 3; do
  git fetch origin main
  if ! git rebase origin/main; then
    mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
    if (( ${#conflicts[@]} == 0 )); then
      git rebase --abort || true
      echo 'Rebase failed without a recognized file conflict.' >&2
      exit 1
    fi
    for file in "${conflicts[@]}"; do
      case "$file" in
        data/game-official-results.json|data/player-calibration.json|data/player-results.json) ;;
        *)
          echo "Unexpected conflict: $file; refusing automatic resolution." >&2
          git rebase --abort || true
          exit 1
          ;;
      esac
    done
    for file in "${conflicts[@]}"; do
      echo "Keeping the newer main version of $file"
      if ! git checkout --ours -- "$file" || ! git add -f -- "$file"; then
        git rebase --abort || true
        exit 1
      fi
    done
    if ! GIT_EDITOR=true git rebase --continue; then
      git rebase --abort || true
      exit 1
    fi
  fi
  if git push origin HEAD:main; then exit 0; fi
  echo "Main changed during publish; retrying ($attempt/3)." >&2
done
echo 'Weekly ML publication could not be safely rebased after three attempts.' >&2
exit 1
