"""
WebXR companion server for DepthGuard.

Runs an aiohttp HTTP+WebSocket server in its own thread (own asyncio loop) so
it can coexist with the synchronous PyQt5 main loop.

Endpoints:
    GET  /                  → serves the WebXR client (web/index.html)
    GET  /static/<file>     → serves web/<file>
    WS   /ws                → live stream:
                              server →  frame (JPEG b64) + depth (optional) + alert
                              client →  brake-press events with timestamps

Designed for two deployment modes:
    A. Local LAN:   point the headset at http://<your-mac-ip>:8765
    B. Public:      `ngrok http 8765` → use the public https URL
"""

from __future__ import annotations

import asyncio
import base64
import json
import socket
import threading
import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

try:
    from aiohttp import web, WSMsgType
except ImportError:  # graceful degradation if user hasn't `pip install`-ed yet
    web = None
    WSMsgType = None


WEB_ROOT = Path(__file__).resolve().parent.parent.parent / "web"
DEFAULT_PORT = 8765


class WebXRServer:
    """
    Thread-safe server you can start/stop from the PyQt main thread.

    Usage:
        srv = WebXRServer(on_brake=lambda ev: ...)
        srv.start()
        srv.push_frame(frame_bgr, depth_map, alert_dict)  # call from main loop
        ...
        srv.stop()
    """

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        on_brake: Callable[[dict], None] | None = None,
        jpeg_quality: int = 60,
        frame_max_width: int = 960,
    ):
        if web is None:
            raise RuntimeError(
                "aiohttp not installed. Run: pip install aiohttp websockets"
            )
        self.port = port
        self.on_brake = on_brake
        self.jpeg_quality = jpeg_quality
        self.frame_max_width = frame_max_width

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._clients: set = set()
        self._running = False
        self._latest_payload: dict | None = None  # latest frame, debounced

    # ── Lifecycle ────────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        # Wait briefly for loop to be ready
        for _ in range(20):
            if self._loop is not None:
                return
            time.sleep(0.05)

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)

    def is_running(self) -> bool:
        return self._running

    def public_url_hint(self) -> str:
        """Return a URL the operator can paste into a headset browser (LAN)."""
        ip = self._local_ip()
        return f"http://{ip}:{self.port}/"

    # ── Public push API (called from PyQt main thread) ───────────
    def push_frame(self, frame_bgr: np.ndarray, depth_map: np.ndarray | None,
                   alert: dict, trial_meta: dict | None = None):
        """
        Encode and broadcast a frame to all connected WebXR clients.

        Args:
            frame_bgr: BGR uint8 (H, W, 3) — straight from cv2.VideoCapture
            depth_map: float32 (H, W) in [0,1], or None to skip
            alert: {"level": ..., "min_depth": ..., "avg_depth": ...}
            trial_meta: optional {"trial_id", "trial_num", "total", "event_type"}
        """
        if not self._running or self._loop is None:
            return
        payload = self._encode_payload(frame_bgr, depth_map, alert, trial_meta)
        self._latest_payload = payload
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    def push_condition(self, condition: str):
        """Tell the headset which experimental condition is active."""
        if not self._running or self._loop is None:
            return
        msg = {"type": "condition", "value": condition, "t_server": time.time()}
        asyncio.run_coroutine_threadsafe(self._broadcast(msg), self._loop)

    def push_event(self, event_type: str, data: dict | None = None):
        """Push an arbitrary control event (e.g. trial_start, block_end)."""
        if not self._running or self._loop is None:
            return
        msg = {"type": event_type, "data": data or {}, "t_server": time.time()}
        asyncio.run_coroutine_threadsafe(self._broadcast(msg), self._loop)

    # ── Internals ────────────────────────────────────────────────
    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._start_server())
            loop.run_forever()
        finally:
            loop.close()

    async def _start_server(self):
        self._app = web.Application()
        self._app.add_routes([
            web.get("/", self._handle_index),
            web.get("/ws", self._handle_ws),
            web.get("/health", self._handle_health),
            web.get("/favicon.ico", self._handle_favicon),
            web.static("/static", str(WEB_ROOT), follow_symlinks=False),
        ])
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host="0.0.0.0", port=self.port)
        await self._site.start()
        print(f"[WebXR] serving at {self.public_url_hint()}  ws://…:{self.port}/ws")

    async def _shutdown(self):
        # Close all WS clients first
        for ws in list(self._clients):
            try:
                await ws.close()
            except Exception:
                pass
        self._clients.clear()
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        # Stop the loop
        self._loop.call_soon_threadsafe(self._loop.stop)

    async def _handle_index(self, request):
        index = WEB_ROOT / "index.html"
        if not index.exists():
            return web.Response(text="WebXR client not found. Build web/index.html.", status=404)
        return web.FileResponse(index)

    async def _handle_health(self, request):
        return web.json_response({"ok": True, "clients": len(self._clients)})

    async def _handle_favicon(self, request):
        # 204 No Content — stops the browser's automatic favicon 404 in console
        return web.Response(status=204)

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)
        self._clients.add(ws)
        peer = request.remote
        print(f"[WebXR] client connected from {peer}  (total={len(self._clients)})")

        # Send the latest frame immediately if we have one
        if self._latest_payload:
            try:
                await ws.send_json(self._latest_payload)
            except Exception:
                pass

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    self._handle_client_message(msg.data, peer)
                elif msg.type == WSMsgType.ERROR:
                    print(f"[WebXR] ws error: {ws.exception()}")
        finally:
            self._clients.discard(ws)
            print(f"[WebXR] client disconnected  (total={len(self._clients)})")
        return ws

    def _handle_client_message(self, raw: str, peer: str):
        try:
            data = json.loads(raw)
        except Exception:
            return
        mtype = data.get("type")
        if mtype == "brake" and self.on_brake:
            # Invoke the callback on the *main thread* via a marshaling layer
            # (the caller is expected to handle thread-safety — for PyQt,
            # see MainWindow._handle_remote_brake which uses QTimer.singleShot).
            try:
                self.on_brake(data)
            except Exception as e:
                print(f"[WebXR] on_brake handler error: {e}")
        elif mtype == "ping":
            # Echo back for latency calibration
            asyncio.run_coroutine_threadsafe(
                self._send_to(peer, {"type": "pong", "t_server": time.time(),
                                     "t_client_echo": data.get("t_client")}),
                self._loop,
            )

    async def _send_to(self, peer, payload):
        for ws in self._clients:
            if not ws.closed:
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass

    async def _broadcast(self, payload: dict):
        dead = []
        for ws in self._clients:
            if ws.closed:
                dead.append(ws)
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            self._clients.discard(d)

    def _encode_payload(self, frame_bgr, depth_map, alert, trial_meta):
        h, w = frame_bgr.shape[:2]
        # Downscale large frames to keep bandwidth manageable
        if w > self.frame_max_width:
            scale = self.frame_max_width / w
            new_size = (self.frame_max_width, int(h * scale))
            frame_bgr = cv2.resize(frame_bgr, new_size, interpolation=cv2.INTER_AREA)
            if depth_map is not None:
                depth_map = cv2.resize(depth_map, new_size, interpolation=cv2.INTER_LINEAR)

        # JPEG encode the frame
        ok, jpeg = cv2.imencode(".jpg", frame_bgr,
                                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        frame_b64 = base64.b64encode(jpeg.tobytes()).decode("ascii") if ok else ""

        # Depth as low-res grayscale PNG (compact)
        depth_b64 = ""
        if depth_map is not None:
            d8 = (np.clip(depth_map, 0, 1) * 255).astype(np.uint8)
            d8 = cv2.resize(d8, (160, max(1, int(160 * d8.shape[0] / d8.shape[1]))))
            ok2, png = cv2.imencode(".png", d8)
            if ok2:
                depth_b64 = base64.b64encode(png.tobytes()).decode("ascii")

        return {
            "type": "frame",
            "t_server": time.time(),
            "alert": {
                "level": alert.get("level", "SAFE"),
                "min_depth": float(alert.get("min_depth", 0.0)),
                "avg_depth": float(alert.get("avg_depth", 0.0)),
            },
            "frame_jpeg_b64": frame_b64,
            "depth_png_b64": depth_b64,
            "trial": trial_meta or {},
        }

    @staticmethod
    def _local_ip() -> str:
        """Best-effort local network IP (for the URL hint)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
