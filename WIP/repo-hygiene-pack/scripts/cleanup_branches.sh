#!/usr/bin/env bash
# RB-HK-001 Phase 1. Classifies remote branches; deletes only merged ones.
# Report-only unless --apply. Refuses unmerged unless --force-unmerged.
set -uo pipefail

APPLY=0; FORCE=0; BASE="main"; REMOTE="origin"
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --force-unmerged) FORCE=1 ;;
    --base=*) BASE="${a#*=}" ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo" >&2; exit 1; }
echo "fetching and pruning $REMOTE ..."
git fetch --prune "$REMOTE" "+refs/heads/*:refs/remotes/$REMOTE/*" >/dev/null 2>&1

merged=(); unmerged=()
for ref in $(git for-each-ref --format='%(refname:short)' "refs/remotes/$REMOTE"); do
  br="${ref#$REMOTE/}"
  [ "$br" = "$BASE" ] && continue
  [ "$br" = "HEAD" ] && continue
  sha=$(git rev-parse --short "$ref")
  days=$(( ( $(date +%s) - $(git log -1 --format=%ct "$ref") ) / 86400 ))
  if git merge-base --is-ancestor "$ref" "$REMOTE/$BASE"; then
    merged+=("$br|$sha|$days")
  else
    ahead=$(git rev-list --count "$REMOTE/$BASE..$ref")
    unmerged+=("$br|$sha|$days|$ahead")
  fi
done

printf '\n=== MERGED into %s (safe to delete) ===\n' "$BASE"
if [ ${#merged[@]} -eq 0 ]; then echo "  none"; else
  printf '  %-58s %-9s %s\n' "BRANCH" "SHA" "IDLE"
  for e in "${merged[@]}"; do IFS='|' read -r b s d <<< "$e"
    printf '  %-58s %-9s %sd\n' "$b" "$s" "$d"; done
fi

printf '\n=== UNMERGED (work exists nowhere else) ===\n'
if [ ${#unmerged[@]} -eq 0 ]; then echo "  none"; else
  printf '  %-52s %-9s %-7s %s\n' "BRANCH" "SHA" "IDLE" "COMMITS AHEAD"
  for e in "${unmerged[@]}"; do IFS='|' read -r b s d a <<< "$e"
    printf '  %-52s %-9s %-7s %s\n' "$b" "$s" "${d}d" "$a"; done
  printf '\n  Do NOT delete these to make a report green. For each: open a PR,\n'
  printf '  cherry-pick what matters, or file a Linear issue capturing intent.\n'
fi

printf '\nRecovery for any deleted branch:\n  git push %s <sha>:refs/heads/<branch>\n' "$REMOTE"

if [ "$APPLY" -eq 0 ]; then
  printf '\nDRY-RUN. Re-run with --apply to delete the MERGED list.\n'
  exit 0
fi

printf '\nDeleting %d merged branch(es)...\n' "${#merged[@]}"
for e in "${merged[@]}"; do IFS='|' read -r b s d <<< "$e"
  echo "  $b ($s)"
  git push "$REMOTE" --delete "$b" || echo "  FAILED: $b"
done

if [ "$FORCE" -eq 1 ] && [ ${#unmerged[@]} -gt 0 ]; then
  printf '\n--force-unmerged given. This DESTROYS unmerged work.\n'
  read -r -p 'Type DESTROY to confirm: ' ans
  if [ "$ans" = "DESTROY" ]; then
    for e in "${unmerged[@]}"; do IFS='|' read -r b s d a <<< "$e"
      echo "  deleting UNMERGED $b ($s, $a commits ahead)"
      git push "$REMOTE" --delete "$b" || echo "  FAILED: $b"; done
  else
    echo "  aborted"
  fi
fi
echo "done"
