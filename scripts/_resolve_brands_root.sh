#!/usr/bin/env bash
# Source this file from kit scripts that need the brands root.
# Exports BRANDS_ROOT as an absolute path.
#
# Resolution order:
#   1. $SLIDESHOW_BRANDS_ROOT env var
#   2. brands_root field in ~/.clawd/slideshow-kit/config.json
#   3. ./brands (CWD-relative, resolved to absolute)
#
# Why: kit consumers don't all have ~/.clawd/. Default to a repo-local
# brands/ dir (gitignored) for discoverability. Power users can pin to
# any path via env or config for multi-tool workflows.

_resolve_brands_root() {
  local root=""
  if [ -n "${SLIDESHOW_BRANDS_ROOT:-}" ]; then
    root="$SLIDESHOW_BRANDS_ROOT"
  elif [ -f "$HOME/.clawd/slideshow-kit/config.json" ]; then
    root="$(jq -r '.brands_root // empty' "$HOME/.clawd/slideshow-kit/config.json" 2>/dev/null || true)"
  fi
  if [ -z "$root" ] || [ "$root" = "null" ]; then
    root="./brands"
  fi
  # Expand leading ~
  root="${root/#\~/$HOME}"
  # Resolve to absolute (CWD-relative if not already absolute)
  case "$root" in
    /*) ;;
    ./*) root="$PWD/${root#./}" ;;
    *) root="$PWD/$root" ;;
  esac
  printf '%s' "$root"
}

BRANDS_ROOT="$(_resolve_brands_root)"
export BRANDS_ROOT
