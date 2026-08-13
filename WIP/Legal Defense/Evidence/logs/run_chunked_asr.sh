#!/bin/bash
# Chunked local mlx-whisper. Media never leaves this host.
# After a first-run hallucination loop (condition_on_previous_text=True),
# clips use --condition-on-previous-text False.
set -euo pipefail
CUSTODY="/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence"
# shellcheck source=/dev/null
source "$CUSTODY/.venv/bin/activate"
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export PYTHONIOENCODING=utf-8

STEM="$1"
DUR_SEC="$2"
CHUNK="${3:-600}"
LOG="$CUSTODY/logs/asr_${STEM##*_}.log"
# Use a short tag from the filename clock (0153/0211/0312/0426)
TAG=$(echo "$STEM" | sed -n 's/.*_2026-04-30_\([0-9]\{4\}\)_.*/\1/p')
LOG="$CUSTODY/logs/asr_${TAG}.log"
WAV="$CUSTODY/working/${STEM}_audio.wav"
OUTDIR="$CUSTODY/derived/transcripts"
mkdir -p "$OUTDIR"

echo "ASR $TAG CHUNKED START $(date) dur=$DUR_SEC chunk=$CHUNK HF_HUB_OFFLINE=$HF_HUB_OFFLINE" | tee -a "$LOG"

start=0
while [ "$start" -lt "$DUR_SEC" ]; do
  end=$((start + CHUNK))
  if [ "$end" -gt "$DUR_SEC" ]; then
    end=$DUR_SEC
  fi
  name="${STEM}_clip_${start}_${end}"
  if [ -f "$OUTDIR/${name}.json" ]; then
    echo "SKIP existing $name $(date)" | tee -a "$LOG"
    start=$end
    continue
  fi
  echo "CLIP $start-$end START $(date)" | tee -a "$LOG"
  set +e
  mlx_whisper "$WAV" \
    --model mlx-community/whisper-large-v3-mlx \
    --language en \
    --word-timestamps True \
    --condition-on-previous-text False \
    --hallucination-silence-threshold 2 \
    -f all \
    --output-dir "$OUTDIR" \
    --output-name "$name" \
    --clip-timestamps "${start},${end}" \
    >> "$LOG" 2>&1
  rc=$?
  set -e
  echo "CLIP $start-$end DONE rc=$rc $(date)" | tee -a "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "FAILED clip $start-$end rc=$rc" | tee -a "$LOG"
    exit "$rc"
  fi
  start=$end
done
echo "ASR $TAG CHUNKED ALL_CLIPS_DONE $(date)" | tee -a "$LOG"
