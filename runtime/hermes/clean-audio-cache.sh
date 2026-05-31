#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: runtime/hermes/clean-audio-cache.sh [--dry-run]

Deletes all Hermes gateway audio cache files:
  - ~/.hermes-charlotte/audio_cache/
  - ~/.hermes-charlotte/cache/audio/

Options:
  --dry-run   Print matching files without deleting them.
  -h, --help  Show this help.
EOF
}

dry_run=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

hermes_home="${CHARLOTTE_HERMES_HOME:-$HOME/.hermes-charlotte}"
targets=(
  "$hermes_home/audio_cache"
  "$hermes_home/cache/audio"
)

matched=0
bytes=0

for target in "${targets[@]}"; do
  if [ ! -d "$target" ]; then
    continue
  fi

  while IFS= read -r -d '' file; do
    matched=$((matched + 1))
    size="$(wc -c < "$file" | tr -d '[:space:]')"
    bytes=$((bytes + size))
    if [ "$dry_run" -eq 1 ]; then
      printf 'would delete %s (%s bytes)\n' "$file" "$size"
    else
      rm -f -- "$file"
      printf 'deleted %s (%s bytes)\n' "$file" "$size"
    fi
  done < <(
    find "$target" -type f \
      \( -iname '*.ogg' -o -iname '*.mp3' -o -iname '*.wav' -o -iname '*.m4a' -o -iname '*.opus' -o -iname '*.webm' \) \
      -print0
  )
done

if [ "$dry_run" -eq 1 ]; then
  printf 'dry run: %s file(s), %s bytes\n' "$matched" "$bytes"
else
  printf 'deleted %s file(s), %s bytes\n' "$matched" "$bytes"
fi
