#!/usr/bin/env bash
# Helper to fetch a few real 360° dashcam clips for testing.
#
# Usage:
#   ./scripts/download_360_samples.sh <youtube-url> [<youtube-url> ...]
#
# Picks the highest-resolution equirectangular variant and saves it to
# data/raw_downloads/. Then use ffmpeg to trim a 5–10 s scenario and add
# a row to data/scenarios_360.csv pointing at the trimmed file.

set -e

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <youtube-url> [<youtube-url> ...]"
  echo ""
  echo "Find 360° dashcam clips on YouTube by searching:"
  echo "  - '360 dashcam'"
  echo "  - '360 driving compilation'"
  echo "  - 'VR180 dashcam'"
  echo ""
  echo "Look for the VR/360 badge in the thumbnail to confirm it's"
  echo "equirectangular (not a regular wide-angle clip)."
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "yt-dlp is not installed. Install with: brew install yt-dlp"
  exit 127
fi

mkdir -p data/raw_downloads

for url in "$@"; do
  echo ""
  echo "▶ Downloading $url"
  # Prefer the highest-resolution equirectangular VP9/AV1 stream
  yt-dlp \
    -f "bestvideo[height>=2160][vcodec~='vp9|av01']+bestaudio/best[height>=2160]/best" \
    --merge-output-format mp4 \
    -o "data/raw_downloads/360_source_%(id)s.%(ext)s" \
    --no-playlist \
    "$url"
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Next: trim a scenario with ffmpeg, e.g."
echo ""
echo "  ffmpeg -ss 02:14 -i data/raw_downloads/360_source_XYZ.mp4 -t 8 \\"
echo "    -c:v libx264 -preset fast -crf 23 -an \\"
echo "    data/scenarios/360_01_pedestrian_critical.mp4"
echo ""
echo "  Then add a row to data/scenarios_360.csv with the new filename"
echo "  and projection=equirectangular."
echo "════════════════════════════════════════════════════════════════"
