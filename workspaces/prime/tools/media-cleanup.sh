#!/bin/bash
# ============================================================
# media-cleanup.sh — Automated media file cleanup
# Moves processed inbound media & workspace audio/video to Trash
# Safe: uses macOS Trash (recoverable), never rm
# ============================================================
#
# Usage:
#   ./media-cleanup.sh              # dry run (shows what would be trashed)
#   ./media-cleanup.sh --execute    # actually move files to Trash
#   ./media-cleanup.sh --cron       # execute silently (for scheduled runs)
#
# What it cleans:
#   1. ~/.openclaw/media/inbound/ — audio, video, images older than N hours
#   2. Workspace scattered mp3/wav/mp4/webp files (NOT in tools/ or audio-previews/)
#   3. tmp-frames/ directory
#
# What it NEVER touches:
#   - PDFs, markdown, text, CSV, docs (potentially important)
#   - audio-previews/ (Sai's voice samples)
#   - Files newer than MIN_AGE_HOURS
# ============================================================

set -euo pipefail

# Config
INBOUND_DIR="$HOME/.openclaw/media/inbound"
WORKSPACE_DIR="$HOME/.openclaw/workspace"
MIN_AGE_HOURS="${MEDIA_CLEANUP_AGE:-6}"  # only trash files older than this
DRY_RUN=true
SILENT=false

# Parse args
for arg in "$@"; do
  case "$arg" in
    --execute) DRY_RUN=false ;;
    --cron) DRY_RUN=false; SILENT=true ;;
    --age=*) MIN_AGE_HOURS="${arg#--age=}" ;;
    --help|-h)
      echo "Usage: media-cleanup.sh [--execute] [--cron] [--age=HOURS]"
      echo "  Default: dry run, 6 hour minimum age"
      exit 0
      ;;
  esac
done

# macOS trash function (recoverable)
trash_file() {
  local f="$1"
  if $DRY_RUN; then
    echo "  [DRY RUN] Would trash: $f ($(du -h "$f" | cut -f1))"
  else
    # Use macOS `trash` if available, otherwise osascript
    if command -v trash &>/dev/null; then
      trash "$f" 2>/dev/null
    else
      osascript -e "tell application \"Finder\" to delete POSIX file \"$f\"" &>/dev/null
    fi
    $SILENT || echo "  🗑️  Trashed: $(basename "$f")"
  fi
}

# Count
total_count=0
total_bytes=0

log() {
  $SILENT || echo "$@"
}

log "🧹 Media Cleanup — $(date '+%Y-%m-%d %H:%M')"
log "   Min age: ${MIN_AGE_HOURS}h | Mode: $($DRY_RUN && echo 'DRY RUN' || echo 'EXECUTE')"
log ""

# ---- 1. Inbound media: audio, video, images ----
log "📂 Inbound media ($INBOUND_DIR):"
if [ -d "$INBOUND_DIR" ]; then
  while IFS= read -r -d '' file; do
    total_count=$((total_count + 1))
    total_bytes=$((total_bytes + $(stat -f%z "$file" 2>/dev/null || echo 0)))
    trash_file "$file"
  done < <(find "$INBOUND_DIR" -type f \( \
    -name "*.mp3" -o -name "*.ogg" -o -name "*.wav" -o -name "*.opus" -o -name "*.m4a" \
    -o -name "*.mp4" -o -name "*.webm" -o -name "*.mov" \
    -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \
  \) -mmin +$((MIN_AGE_HOURS * 60)) -print0 2>/dev/null)
else
  log "  (directory not found)"
fi

# ---- 2. Workspace scattered audio/video ----
log ""
log "📂 Workspace media ($WORKSPACE_DIR):"
while IFS= read -r -d '' file; do
  # Skip protected directories
  case "$file" in
    */audio-previews/*) continue ;;  # Sai's voice samples
    */tools/*) continue ;;           # Tool assets
    */.git/*) continue ;;            # Git internals
    */node_modules/*) continue ;;    # Dependencies
    */colosseum-dashboard/*) continue ;; # Separate repo
  esac
  total_count=$((total_count + 1))
  total_bytes=$((total_bytes + $(stat -f%z "$file" 2>/dev/null || echo 0)))
  trash_file "$file"
done < <(find "$WORKSPACE_DIR" -maxdepth 3 -type f \( \
  -name "*.mp3" -o -name "*.wav" -o -name "*.ogg" -o -name "*.mp4" -o -name "*.webm" -o -name "*.webp" \
\) -mmin +$((MIN_AGE_HOURS * 60)) -print0 2>/dev/null)

# ---- 3. tmp-frames ----
if [ -d "$WORKSPACE_DIR/tmp-frames" ]; then
  log ""
  log "📂 tmp-frames:"
  while IFS= read -r -d '' file; do
    total_count=$((total_count + 1))
    total_bytes=$((total_bytes + $(stat -f%z "$file" 2>/dev/null || echo 0)))
    trash_file "$file"
  done < <(find "$WORKSPACE_DIR/tmp-frames" -type f -mmin +$((MIN_AGE_HOURS * 60)) -print0 2>/dev/null)
fi

# ---- Summary ----
log ""
mb=$((total_bytes / 1024 / 1024))
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Total: $total_count files | ${mb}MB"
if $DRY_RUN; then
  log "⚠️  DRY RUN — run with --execute to actually trash"
else
  log "✅ All moved to Trash (recoverable)"
fi
