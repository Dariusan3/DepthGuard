#!/usr/bin/env bash
# Trim a clip from a raw download and save it as a scenario.
#
# Usage:
#   ./scripts/trim_scenario.sh <source-file> <start-time> <duration> <scenario-id> <event_type> <alert_level>
#
# Example:
#   ./scripts/trim_scenario.sh data/raw_downloads/source_abc.mp4 02:14 8 01 pedestrian critical
#
# Time formats: ss, mm:ss, hh:mm:ss
# Event types: pedestrian / brake_lights / cyclist / lane_intrusion / safe
# Alert levels: critical / warning / caution / safe (lowercase in filename)

set -euo pipefail

if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <source-file> <start-time> <duration> <scenario-id> <event_type> <alert_level>"
  echo "Example: $0 data/raw_downloads/source_abc.mp4 02:14 8 01 pedestrian critical"
  exit 1
fi

SOURCE="$1"
START="$2"
DURATION="$3"
ID="$4"
EVENT_TYPE="$5"
ALERT_LEVEL="$6"

OUT_DIR="data/scenarios"
OUT_FILE="${OUT_DIR}/${ID}_${EVENT_TYPE}_${ALERT_LEVEL}.mp4"

if [ ! -f "$SOURCE" ]; then
  echo "Source file not found: $SOURCE"
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "Trimming $SOURCE [$START + ${DURATION}s] → $OUT_FILE"

ffmpeg -y -ss "$START" -i "$SOURCE" -t "$DURATION" \
       -c:v libx264 -preset fast -crf 23 -an \
       -movflags +faststart \
       "$OUT_FILE"

echo ""
echo "✓ Saved: $OUT_FILE"
echo ""
echo "Don't forget to update data/scenarios.csv:"
echo "  - source: $SOURCE"
echo "  - duration_ms: $((DURATION * 1000))"
echo "  - event_start_ms: <when does the danger appear, in ms from clip start?>"
