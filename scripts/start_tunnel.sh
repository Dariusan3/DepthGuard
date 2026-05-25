#!/usr/bin/env bash
# Start the ngrok tunnel on the user's static domain so the lab's bookmarked
# headset URL always reaches this laptop.
#
# Usage:
#   ./scripts/start_tunnel.sh
#
# The app starts this script automatically after login. It can still be run
# manually for troubleshooting. After WebXR is enabled, share this URL:
#
#   https://ichthyosaurian-nonsatiric-kellan.ngrok-free.dev/

set -e

NGROK_DOMAIN="ichthyosaurian-nonsatiric-kellan.ngrok-free.dev"
LOCAL_PORT=8765
if command -v ngrok >/dev/null 2>&1; then
    NGROK_BIN="$(command -v ngrok)"
elif [[ -x /opt/homebrew/bin/ngrok ]]; then
    NGROK_BIN="/opt/homebrew/bin/ngrok"
else
    echo "ngrok is not installed or not available in PATH."
    exit 127
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  DepthGuard WebXR tunnel"
echo "  Public URL: https://${NGROK_DOMAIN}/"
echo "  Forwarding → http://localhost:${LOCAL_PORT}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Make sure the WebXR toggle inside DepthGuard is ON before opening the URL."
echo ""

# Replace this shell process so the app can reliably stop the tunnel it owns.
exec "${NGROK_BIN}" http --url="${NGROK_DOMAIN}" "${LOCAL_PORT}"
