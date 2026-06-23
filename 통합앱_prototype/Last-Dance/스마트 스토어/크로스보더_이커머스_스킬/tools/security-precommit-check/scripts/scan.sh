#!/bin/bash
# scan.sh — Security pre-commit scanner.
#
# Scans target files against rule files (universal default + per-repo custom)
# and reports BLOCK / WARN matches. Exits non-zero if any BLOCK match found
# (rejects commit when invoked from .git/hooks/pre-commit).
#
# Usage:
#   scan.sh                        # scan staged files (default; use from git hook)
#   scan.sh --staged               # same as above
#   scan.sh --all                  # scan all tracked files
#   scan.sh --files PATH [PATH...] # scan specific files
#
# Rules format (rules/default.txt + .security-precommit-rules.txt):
#   SEVERITY|PATTERN|DESCRIPTION
#   SEVERITY: BLOCK or WARN
#   PATTERN: extended-regex (passed to grep -E)
#   Lines starting with # are comments.

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEFAULT_RULES="$SCRIPT_DIR/../rules/default.txt"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_RULES="$REPO_ROOT/.security-precommit-rules.txt"

# -------------------- determine target files --------------------

MODE="${1:---staged}"
case "$MODE" in
  --staged)
    FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null) ;;
  --all)
    FILES=$(git ls-files 2>/dev/null) ;;
  --files)
    shift
    FILES="$*" ;;
  *)
    echo "scan.sh: unknown mode '$MODE' (expected --staged | --all | --files PATH...)" >&2
    exit 2 ;;
esac

if [ -z "$FILES" ]; then
  exit 0
fi

# -------------------- collect rules --------------------

RULE_FILES=()
[ -f "$DEFAULT_RULES" ] && RULE_FILES+=("$DEFAULT_RULES")
[ -f "$PROJECT_RULES" ] && RULE_FILES+=("$PROJECT_RULES")

if [ ${#RULE_FILES[@]} -eq 0 ]; then
  echo "scan.sh: no rule files found (looked at $DEFAULT_RULES and $PROJECT_RULES)" >&2
  exit 2
fi

# -------------------- scan --------------------

ISSUES_BLOCK=()
ISSUES_WARN=()

for rule_file in "${RULE_FILES[@]}"; do
  while IFS= read -r line || [ -n "$line" ]; do
    # skip comments and blanks
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac

    SEVERITY=$(echo "$line" | cut -d'|' -f1)
    PATTERN=$(echo "$line" | cut -d'|' -f2)
    DESC=$(echo "$line" | cut -d'|' -f3-)

    [ -z "$PATTERN" ] && continue
    [ "$SEVERITY" != "BLOCK" ] && [ "$SEVERITY" != "WARN" ] && continue

    for f in $FILES; do
      [ -f "$f" ] || continue
      # Don't scan binary files
      if file --brief --mime "$f" 2>/dev/null | grep -q "charset=binary"; then
        continue
      fi
      # Don't scan the scanner's own files (rule definitions are designed to
      # contain the patterns they block — that's their job)
      [[ "$f" == *"security-precommit-check/"* ]] && continue
      [[ "$(basename "$f")" == ".security-precommit-rules.txt" ]] && continue

      MATCHES=$(grep -nE "$PATTERN" "$f" 2>/dev/null || true)
      [ -z "$MATCHES" ] && continue

      while IFS= read -r m; do
        # Truncate long lines
        m_short=$(echo "$m" | cut -c1-180)
        entry="$f:$m_short  ← [$DESC]"
        if [ "$SEVERITY" = "BLOCK" ]; then
          ISSUES_BLOCK+=("$entry")
        else
          ISSUES_WARN+=("$entry")
        fi
      done <<< "$MATCHES"
    done
  done < "$rule_file"
done

# -------------------- report --------------------

if [ ${#ISSUES_WARN[@]} -gt 0 ]; then
  echo
  echo "[WARN] ${#ISSUES_WARN[@]} project-specific keyword match(es):"
  for entry in "${ISSUES_WARN[@]}"; do
    echo "  $entry"
  done
fi

if [ ${#ISSUES_BLOCK[@]} -gt 0 ]; then
  echo
  echo "[BLOCK] ${#ISSUES_BLOCK[@]} potential secret/credential match(es):"
  for entry in "${ISSUES_BLOCK[@]}"; do
    echo "  $entry"
  done
  echo
  echo "Commit blocked. Fix the issues above, OR bypass intentionally with:"
  echo "  git commit --no-verify"
  exit 1
fi

if [ ${#ISSUES_WARN[@]} -gt 0 ]; then
  echo
  echo "Warnings only (non-blocking). Use --no-verify to skip warnings entirely."
fi

exit 0
