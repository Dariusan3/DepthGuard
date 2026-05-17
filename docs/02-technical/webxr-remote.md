# WebXR Companion — Remote VR/AR Testing

Implements Option B from [`ar-extension.md`](ar-extension.md): a browser-side WebXR client that connects to DepthGuard over WebSocket. Participants wear a VR/AR headset, point its browser at a URL, and see the live dashcam scene as a virtual windshield with the alert visuals composited in 3D space.

The same client works on:
- Meta Quest 2 / Quest 3 (browser → enter VR)
- Apple Vision Pro (Safari → enter VR)
- iPhone / Android (WebXR AR via Chrome / Safari)
- Desktop browser (no VR — just a flat preview)

---

## Architecture

```
   ┌────────────────────────┐         WebSocket          ┌─────────────────────┐
   │  DepthGuard (your Mac) │ ──── server pushes ────▶  │  WebXR client       │
   │                        │   frame (JPEG b64)         │  (Three.js, in      │
   │  - alert pipeline      │   depth (PNG b64)          │  headset browser)   │
   │  - data logger         │   alert level              │                     │
   │                        │   trial metadata           │  - virtual          │
   │                        │                            │    windshield       │
   │  ⌃                     │  ◀── brake events ───      │  - 3-color HUD      │
   │  reaction → CSV        │   {source, t_client,       │  - controller       │
   │                        │    latency_hint_ms}        │    triggers = BRAKE │
   └────────────────────────┘                            └─────────────────────┘
            HTTP serves web/index.html + web/main.js + /ws
```

---

## Files

| File | Role |
|---|---|
| `src/network/webxr_server.py` | Threaded aiohttp server (HTTP + WebSocket). Encodes frames to JPEG, depth to PNG, pushes to all connected clients. |
| `web/index.html` | Companion page — flat preview + Enter-VR button + brake button. |
| `web/main.js` | Three.js scene with virtual windshield, WebSocket client, controller bindings. |
| `src/ui/main_window.py` | Owns the `WebXRServer` instance. Toggle button starts/stops it. The per-frame loop calls `push_frame()` at ~15 FPS. |

---

## Install (one-time)

```bash
pip install aiohttp websockets
```

To expose the local server to the public internet for remote testing:

```bash
brew install ngrok      # or download from ngrok.com
ngrok config add-authtoken <your-token>   # free account
```

---

## How to run

### Local LAN (you + headset on same network)

1. Start DepthGuard: `python main.py`
2. Click the **📡 WebXR: OFF** button in the controls bar → it flips to **ON**
3. A dialog shows a URL like `http://192.168.1.42:8765/`
4. On the headset's browser, open that URL
5. The dashcam frame appears on the page. Click **ENTER VR**.
6. In VR: a virtual windshield 1.6 m in front of you, with the live feed
7. Press the controller trigger to register a BRAKE (logged to your DepthGuard CSV)

### Remote (headset anywhere with internet)

1. Start DepthGuard and toggle WebXR ON (as above)
2. In another terminal: `ngrok http 8765`
3. ngrok prints a public https URL like `https://abc-123.ngrok-free.app`
4. Share that URL with the remote participant — opens on any device
5. Brake presses stream back to your local DepthGuard in real time

---

## Latency and reaction-time correction

The client measures network round-trip with periodic ping/pong (every 2 s) and includes the latest `latency_hint_ms` in every brake event.

Network latency profile:
- LAN: typically 5–15 ms (negligible)
- ngrok tunnel: typically 50–150 ms (region-dependent)
- Cross-continent: 150–250 ms

For reaction-time analysis, the **half-RTT** can be subtracted from the measured RT to estimate the "true" perceptual reaction time. The `latency_hint_ms` column will be added to `reactions_*.csv` when network mode is detected.

---

## Testing without a real headset

Two options for development:

### Option A: WebXR Emulator Chrome extension
Install [WebXR API Emulator](https://chrome.google.com/webstore/detail/webxr-api-emulator/mjddjgeghkdijejnciaefnkjmkafnnje) — gives you a fake VR view with mouse-controlled head movement and keyboard-mapped controllers. Clicking the trigger registers a brake event.

### Option B: Flat preview only
The companion page works without entering VR — the 2D preview is fully functional. Brake button + keyboard (B or SPACE) send the same events. Use this for fast iteration.

---

## Bandwidth

At default settings:
- Frame: JPEG quality 60, scaled to 960px wide → ~30–80 KB per frame
- Push rate: 15 FPS
- Total: ~5–12 Mbps of upstream from your laptop

Both knobs are tunable in `WebXRServer(jpeg_quality=, frame_max_width=)`.

For very slow networks, drop the push rate in `process_next_frame` (currently `1.0 / 15.0` — change to `1.0 / 5.0` for 5 FPS).

---

## Open work

- [ ] Persist `latency_hint_ms` and `source` in `reactions_*.csv` (currently captured in memory only)
- [ ] Render the AR HUD overlay (translucent threat highlight, BRAKE strip) as 3D geometry instead of flat texture overlay
- [ ] Stereo support — render slightly different views to each eye for proper depth perception
- [ ] Spatial audio for the alert beeps (currently desktop-side only)
