#!/usr/bin/env bash
# PII gate: scan tracked files and all of `git log -p` for personal data.
# Usage: scripts/pii_check.sh [DENYLIST]
#   Generic patterns always run: email addresses (noreply ones allowed), /Users/ or /home/ paths, 10+ digit runs
#   (except test-card 4111…, 0000…, 1234567… and one-repeated-digit runs), and family-relationship words.
#   DENYLIST: optional file of terms to reject (one per line, case-insensitive) — keep it outside this repo.
# Prints "file:line: kind" (or "history <commit> file: kind") per hit, never the matched text. Exits 1 on any hit.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
deny=${1:-/dev/null}
# this script and its test hold the patterns themselves
self='^(scripts/pii_check\.sh|tests/test_pii_check\.py)$'

{
  git grep -nI -e '' -- . | sed -E 's/^([^:]*):([0-9]*):/\1:\2:\t/'
  git log -p --all --no-color | awk -v self="$self" '
    /^commit [0-9a-f]{40}/ { c = substr($2, 1, 7); f = ""; next }
    /^diff --git / { f = substr($4, 3); next }
    f !~ self { print "history " c " " f ":\t" $0 }'
} | awk -F'\t' -v self="$self" -v deny="$deny" '
  BEGIN {
    while ((getline t < deny) > 0) { gsub(/^[ \t]+|[ \t\r]+$/, "", t); if (t != "") terms[tolower(t)] }
  }
  {
    loc = $1; sub(/\t.*/, "", loc); text = substr($0, length(loc) + 2)
    file = loc; sub(/:[0-9]+:$/, "", file)
    if (file ~ self) next
    low = tolower(text)
    kind = ""
    if (text ~ /[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z][A-Za-z]+/ && low !~ /noreply/) kind = "email"
    else if (text ~ /\/(Users|home)\//) kind = "home path"
    else if (low ~ /(^|[^a-z0-9])(mom|mum|dad|mother|father|wife|husband|sister|brother|inherited)([^a-z0-9]|$)/) kind = "relationship word"
    else {
      s = text
      while (match(s, /[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]+/)) {
        run = substr(s, RSTART, RLENGTH)
        before = RSTART > 1 ? substr(s, RSTART - 1, 1) : ""
        after = substr(s, RSTART + RLENGTH, 1)
        s = substr(s, RSTART + RLENGTH)
        if (before ~ /[A-Za-z]/ || after ~ /[A-Za-z]/) continue  # part of a hash or id, not a bare number
        if (run ~ /^(4111|0000|1234567)/) continue  # test card, zero-padded and 1234567… placeholders
        rep = run; gsub(substr(run, 1, 1), "", rep); if (rep == "") continue
        kind = "long digit run"; break
      }
    }
    if (kind == "") for (t in terms) if (index(low, t)) { kind = "denylist term"; break }
    if (kind != "") { print loc " " kind; hits++ }
  }
  END { exit hits > 0 }' | sed -E 's/:[[:space:]]+/: /'
