#!/usr/bin/env bash
# Start the ngrok tunnel on the user's static domain so the lab's bookmarked
# headset URL always reaches this laptop.
#
# Usage:
#   ./scripts/start_tunnel.sh
#
# Open a separate terminal and run `python main.py` first, then toggle
# WebXR ON in the app. After that, share this URL:
#
#   https://ichthyosaurian-nonsatiric-kellan.ngrok-free.dev/

set -e

NGROK_DOMAIN="ichthyosaurian-nonsatiric-kellan.ngrok-free.dev"
LOCAL_PORT=8765

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  DepthGuard WebXR tunnel"
echo "  Public URL: https://${NGROK_DOMAIN}/"
echo "  Forwarding → http://localhost:${LOCAL_PORT}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Make sure 'python main.py' is running in another terminal AND"
echo "the WebXR toggle inside DepthGuard is ON before opening the URL."
echo ""

ngrok http --url="${NGROK_DOMAIN}" "${LOCAL_PORT}"
