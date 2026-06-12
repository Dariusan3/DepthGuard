// DepthGuard WebXR companion — Three.js scene + WebSocket client.
// Renders the live dashcam frame on a virtual windshield in front of the user,
// reflects the alert state as ambient lighting + bottom HUD strip,
// and sends brake-press events back to DepthGuard.

import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ─── DOM refs ────────────────────────────────────────────────
const previewImg = document.getElementById('frame-preview');
const previewCanvas = document.getElementById('frame-canvas-preview');
const previewCtx = previewCanvas.getContext('2d');
const alertBar   = document.getElementById('alert-bar');
const connDot    = document.getElementById('conn-dot');
const connText   = document.getElementById('conn-text');
const metaCond   = document.getElementById('meta-condition');
const metaTrial  = document.getElementById('meta-trial');
const metaLat    = document.getElementById('meta-latency');
const metaDetector = document.getElementById('meta-detector');
const btnVR      = document.getElementById('btn-vr');
const btnBrake   = document.getElementById('btn-brake');
const btnPlayback = document.getElementById('btn-playback');
const btnStop    = document.getElementById('btn-stop');

// ─── WebSocket setup ─────────────────────────────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsURL = `${wsProtocol}://${window.location.host}/ws`;
let ws = null;
let latestFrame = null;     // {imageBitmap, alert, trial}
let latencyPing = 0;        // last measured RTT in ms
let latestObjects = [];
let vrPlayButton = null;
let vrBrakeButton = null;

function connect() {
  setConn(false, 'CONNECTING…');
  ws = new WebSocket(wsURL);
  ws.onopen = () => {
    setConn(true, 'CONNECTED');
    setInterval(sendPing, 2000);
  };
  ws.onclose = () => {
    setConn(false, 'DISCONNECTED — retrying in 2s');
    setTimeout(connect, 2000);
  };
  ws.onmessage = handleMessage;
  ws.onerror = () => setConn(false, 'WS ERROR');
}

function setConn(live, text) {
  connDot.classList.toggle('live', live);
  connText.textContent = text;
}

function sendPing() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping', t_client: performance.now() }));
  }
}

function handleMessage(ev) {
  let msg;
  try { msg = JSON.parse(ev.data); } catch { return; }

  if (msg.type === 'frame') {
    handleFrame(msg);
  } else if (msg.type === 'condition') {
    metaCond.textContent = msg.value;
  } else if (msg.type === 'pong') {
    latencyPing = Math.round(performance.now() - msg.t_client_echo);
    metaLat.textContent = `${latencyPing} ms`;
  } else if (msg.type === 'playback') {
    setPlaybackState(Boolean(msg.data && msg.data.playing));
  } else if (msg.type === 'trial_start' || msg.type === 'block_start' || msg.type === 'session_end') {
    if (msg.data && msg.data.label) {
      metaTrial.textContent = msg.data.label;
    }
  }
}

// ── Paused state mirror (from laptop) ──
const pauseBanner = document.createElement('div');
Object.assign(pauseBanner.style, {
  position: 'fixed', top: '20px', left: '50%', transform: 'translateX(-50%)',
  zIndex: '20', background: 'rgba(255,159,10,0.95)', color: '#1a1a00',
  padding: '10px 28px', borderRadius: '20px',
  fontSize: '13px', fontWeight: '800', letterSpacing: '2px',
  fontFamily: 'sans-serif', display: 'none',
});
pauseBanner.textContent = '⏸  PAUSED';
document.body.appendChild(pauseBanner);

// In-scene 3D paused indicator — shown floating over the windshield in VR
const pauseTexCanvas = document.createElement('canvas');
pauseTexCanvas.width = 512; pauseTexCanvas.height = 128;
{
  const ctx = pauseTexCanvas.getContext('2d');
  ctx.fillStyle = 'rgba(255,159,10,0.9)';
  ctx.fillRect(0, 0, 512, 128);
  ctx.fillStyle = '#1a1a00';
  ctx.font = '800 64px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('⏸  PAUSED', 256, 88);
}
const pauseTex = new THREE.CanvasTexture(pauseTexCanvas);
pauseTex.colorSpace = THREE.SRGBColorSpace;
const pauseLabel = new THREE.Mesh(
  new THREE.PlaneGeometry(0.9, 0.225),
  new THREE.MeshBasicMaterial({ map: pauseTex, transparent: true, opacity: 0 })
);
pauseLabel.position.set(0, 0.8, 0.05);
// pauseLabel is attached to windshieldGroup after that group is created (further down)

function setPaused(paused) {
  pauseBanner.style.display = paused ? 'block' : 'none';
  pauseLabel.material.opacity = paused ? 1.0 : 0.0;
}

function setPlaybackState(playing) {
  setPaused(!playing);
  btnPlayback.textContent = playing ? 'PAUSE' : 'PLAY';
  if (vrPlayButton) {
    updateVRControlButton(vrPlayButton, playing ? 'PAUSE' : 'PLAY');
  }
}

let frameCount = 0;
function handleFrame(msg) {
  frameCount++;
  if (frameCount === 1) console.log('[WebXR] first frame received', msg.alert);
  if (frameCount % 50 === 0) console.log(`[WebXR] ${frameCount} frames received`);
  // Update 2D preview (and reuse this same <img> as the 3D texture source —
  // the browser handles orientation correctly that way, no ImageBitmap dance)
  if (msg.frame_jpeg_b64) {
    previewImg.src = `data:image/jpeg;base64,${msg.frame_jpeg_b64}`;
  }
  // Update alert state
  const level = msg.alert?.level || 'SAFE';
  alertBar.textContent = level;
  alertBar.className = `alert-bar ${level}`;
  latestObjects = Array.isArray(msg.objects) ? msg.objects : [];
  if (metaDetector) metaDetector.textContent = msg.detector_status || `${latestObjects.length} objects`;
  // Trial metadata
  if (msg.trial?.label) metaTrial.textContent = msg.trial.label;
  pendingAlert = level;
}

// Route frames through a fixed-size canvas so the texture dimensions never
// change between clips (different aspect ratios would otherwise overflow
// the allocated texture and trigger glTexSubImage2D errors).
const frameCanvas = document.createElement('canvas');
frameCanvas.width = 1024;
frameCanvas.height = 576;
const frameCtx = frameCanvas.getContext('2d');
frameCtx.fillStyle = '#0C1021';
frameCtx.fillRect(0, 0, frameCanvas.width, frameCanvas.height);
previewCtx.fillStyle = '#0C1021';
previewCtx.fillRect(0, 0, previewCanvas.width, previewCanvas.height);

const windshieldTexture = new THREE.CanvasTexture(frameCanvas);
windshieldTexture.colorSpace = THREE.SRGBColorSpace;
windshieldTexture.minFilter = THREE.LinearFilter;
windshieldTexture.magFilter = THREE.LinearFilter;
windshieldTexture.generateMipmaps = false;
windshieldTexture.wrapS = THREE.ClampToEdgeWrapping;
windshieldTexture.wrapT = THREE.ClampToEdgeWrapping;

let hasFirstFrame = false;
previewImg.addEventListener('load', () => {
  drawFrameWithObjects(frameCtx, frameCanvas);
  drawFrameWithObjects(previewCtx, previewCanvas);
  hasFirstFrame = true;
  windshieldTexture.needsUpdate = true;
});

const objectColors = {
  person: '#FF2D55',
  bicycle: '#FF9F0A',
  motorcycle: '#FF9F0A',
  car: '#00E5A0',
  bus: '#30D158',
  truck: '#30D158',
  'traffic light': '#FFD60A',
  'stop sign': '#FF2D55',
};

function objectColor(obj) {
  const depth = Number(obj.depth);
  if (Number.isFinite(depth)) {
    if (depth <= 0.25) return '#FF2D55';
    if (depth <= 0.40) return '#FF9F0A';
    if (depth <= 0.60) return '#FFD60A';
  }
  return objectColors[obj.label] || '#E8ECF4';
}

function drawFrameWithObjects(ctx, canvas) {
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const iw = previewImg.naturalWidth;
  const ih = previewImg.naturalHeight;
  if (iw <= 0 || ih <= 0) return;

  const scale = Math.min(canvas.width / iw, canvas.height / ih);
  const dw = iw * scale;
  const dh = ih * scale;
  const dx = (canvas.width - dw) / 2;
  const dy = (canvas.height - dh) / 2;
  ctx.drawImage(previewImg, dx, dy, dw, dh);
  drawObjectBoxes(ctx, latestObjects, dx, dy, scale);
  drawDetectorStatus(ctx, latestObjects, canvas);
}

function drawObjectBoxes(ctx, objects, dx, dy, scale) {
  ctx.save();
  ctx.lineJoin = 'round';
  for (const obj of objects) {
    if (!obj.bbox || obj.bbox.length !== 4) continue;
    const [x1, y1, x2, y2] = obj.bbox.map(Number);
    const px = dx + x1 * scale;
    const py = dy + y1 * scale;
    const pw = Math.max(1, (x2 - x1) * scale);
    const ph = Math.max(1, (y2 - y1) * scale);
    const color = objectColor(obj);
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, 3 * scale);
    ctx.strokeRect(px, py, pw, ph);

    const conf = Number.isFinite(obj.confidence) ? ` ${obj.confidence.toFixed(2)}` : '';
    const depth = Number.isFinite(obj.depth) ? ` d=${obj.depth.toFixed(2)}` : '';
    const text = `${String(obj.label || 'object').toUpperCase()}${conf}${depth}`;
    ctx.font = '700 13px sans-serif';
    const padX = 6;
    const padY = 4;
    const textW = ctx.measureText(text).width;
    const labelH = 20;
    const ly = Math.max(0, py - labelH - 2);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.9;
    ctx.fillRect(px, ly, textW + padX * 2, labelH);
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(text, px + padX, ly + labelH - padY - 2);
  }
  ctx.restore();
}

function drawDetectorStatus(ctx, objects, canvas) {
  if (objects.length > 0) return;
  const text = metaDetector?.textContent || '';
  if (!text || text === '—') return;
  ctx.save();
  ctx.font = '700 13px sans-serif';
  const shown = text.length > 86 ? `${text.slice(0, 83)}...` : text;
  const w = ctx.measureText(shown).width + 18;
  ctx.globalAlpha = 0.78;
  ctx.fillStyle = '#0C1021';
  ctx.fillRect(12, 12, Math.min(w, canvas.width - 24), 28);
  ctx.globalAlpha = 1;
  ctx.fillStyle = '#FFD60A';
  ctx.fillText(shown, 21, 31);
  ctx.restore();
}

// ─── Brake handling ──────────────────────────────────────────
function sendBrake(source) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    type: 'brake',
    source,                                // 'controller' / 'keyboard' / 'click'
    t_client: performance.now(),
    latency_hint_ms: latencyPing,
  }));
  // Visual flash — both the 2D page button and the in-world VR panel button
  btnBrake.style.filter = 'brightness(1.5)';
  setTimeout(() => btnBrake.style.filter = '', 150);
  flashVRBrakeButton();
}

function sendControl(action, source, extra = {}) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    type: 'control',
    action,
    source,
    t_client: performance.now(),
    latency_hint_ms: latencyPing,
    ...extra,
  }));
}

btnBrake.addEventListener('click', () => sendBrake('click'));
btnPlayback.addEventListener('click', () => sendControl('toggle_play', 'web'));
btnStop.addEventListener('click', () => sendControl('stop', 'web'));
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' || e.code === 'KeyB' || e.code === 'Backspace') {
    e.preventDefault();
    sendBrake(e.code === 'Backspace' ? 'keyboard_back' : 'keyboard');
  }
});

// ─── Three.js scene + WebXR ──────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x06080F);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.6, 0);
const playerRig = new THREE.Group();
scene.add(playerRig);
playerRig.add(camera);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true;
renderer.domElement.style.display = 'none'; // hide until VR enters
document.body.appendChild(renderer.domElement);

// ── Floor + reference grid so the user has spatial grounding ──
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(40, 40),
  new THREE.MeshBasicMaterial({ color: 0x06080F, side: THREE.DoubleSide })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = 0;
scene.add(floor);

const grid = new THREE.GridHelper(40, 40, 0x2A3558, 0x1A2038);
grid.position.y = 0.001;          // a hair above the floor to avoid z-fighting
scene.add(grid);

// Virtual windshield: a 16:9 plane 1.5m in front of the user
const windshieldGeom = new THREE.PlaneGeometry(2.4, 1.35);

// Placeholder texture — a "waiting for frames" canvas so the user can tell
// whether the 3D scene works vs. the WebSocket isn't delivering frames yet
const placeholderCanvas = document.createElement('canvas');
placeholderCanvas.width = 960;
placeholderCanvas.height = 540;
const pctx = placeholderCanvas.getContext('2d');
pctx.fillStyle = '#0C1021';
pctx.fillRect(0, 0, 960, 540);
pctx.fillStyle = '#6B7A99';
pctx.font = '700 28px sans-serif';
pctx.textAlign = 'center';
pctx.fillText('WAITING FOR FRAMES', 480, 250);
pctx.font = '500 16px sans-serif';
pctx.fillText('Press Play in DepthGuard to start the playlist', 480, 290);
const placeholderTex = new THREE.CanvasTexture(placeholderCanvas);
placeholderTex.colorSpace = THREE.SRGBColorSpace;
// Group the windshield + strip + glow so they all move together when grabbed
// with a Quest controller. The group origin sits where the windshield does.
const windshieldGroup = new THREE.Group();
const WINDSHIELD_DEFAULT_POS = new THREE.Vector3(0, 1.6, -1.6);
const WINDSHIELD_DEFAULT_QUAT = new THREE.Quaternion();
windshieldGroup.position.copy(WINDSHIELD_DEFAULT_POS);
scene.add(windshieldGroup);

const windshieldMat = new THREE.MeshBasicMaterial({ map: placeholderTex, side: THREE.DoubleSide });
const windshield = new THREE.Mesh(windshieldGeom, windshieldMat);
windshield.position.set(0, 0, 0);    // local to group
windshieldGroup.add(windshield);

// Bottom HUD strip — local offset under the windshield
const stripGeom = new THREE.PlaneGeometry(2.4, 0.08);
const stripMat = new THREE.MeshBasicMaterial({ color: 0xff2d55, transparent: true, opacity: 0 });
const strip = new THREE.Mesh(stripGeom, stripMat);
strip.position.set(0, -0.7, 0.01);
windshieldGroup.add(strip);

// Subtle ambient glow plane behind the windshield
const glowGeom = new THREE.PlaneGeometry(3.6, 2.0);
const glowMat = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.0 });
const glow = new THREE.Mesh(glowGeom, glowMat);
glow.position.set(0, 0, -0.1);
windshieldGroup.add(glow);

// Now that the group exists, attach the pause label that was created earlier
windshieldGroup.add(pauseLabel);

// VR-only control console. DOM buttons are not visible in immersive WebXR, so
// this panel is part of the scene and follows the movable windshield.
const vrControlTargets = [];
const vrControlPanel = new THREE.Group();
vrControlPanel.position.set(0, -0.98, 0.035);
windshieldGroup.add(vrControlPanel);

const vrPanelBack = new THREE.Mesh(
  new THREE.PlaneGeometry(2.42, 0.64),
  new THREE.MeshBasicMaterial({ color: 0x0C1021, transparent: true, opacity: 0.95 })
);
vrPanelBack.position.set(0, -0.05, -0.012);
vrControlPanel.add(vrPanelBack);

function updateVRControlButton(button, label = button.userData.label, hovered = button.userData.hovered) {
  button.userData.label = label;
  button.userData.hovered = hovered;
  const ctx = button.userData.ctx;
  const canvas = button.userData.canvas;
  const flashing = !!button.userData.flashing;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // Flashing (just pressed) renders brightest, then hover, then base color
  ctx.fillStyle = flashing ? '#FFFFFF' : (hovered ? button.userData.hoverColor : button.userData.color);
  ctx.fillRect(4, 4, canvas.width - 8, canvas.height - 8);
  ctx.strokeStyle = (flashing || hovered) ? '#FFFFFF' : '#24304D';
  ctx.lineWidth = (flashing || hovered) ? 5 : 3;
  ctx.strokeRect(4, 4, canvas.width - 8, canvas.height - 8);
  ctx.fillStyle = flashing ? button.userData.color : '#FFFFFF';
  ctx.font = '700 34px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(label, canvas.width / 2, canvas.height / 2);
  button.userData.texture.needsUpdate = true;
}

// Press animation for the in-world BRAKE button — fires no matter where the
// brake came from (trigger, left X/Y, keyboard, 2D click, or the panel itself)
// so the participant always gets the visual confirmation in VR.
function flashVRBrakeButton() {
  if (!vrBrakeButton) return;
  vrBrakeButton.userData.flashing = true;
  vrBrakeButton.scale.set(0.86, 0.86, 1);   // press-down effect
  updateVRControlButton(vrBrakeButton);
  setTimeout(() => {
    vrBrakeButton.userData.flashing = false;
    vrBrakeButton.scale.set(1, 1, 1);
    updateVRControlButton(vrBrakeButton);
  }, 220);
}

function makeVRControlButton(label, action, color, hoverColor, x, y) {
  const canvas = document.createElement('canvas');
  canvas.width = 320;
  canvas.height = 112;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const button = new THREE.Mesh(
    new THREE.PlaneGeometry(0.72, 0.19),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide })
  );
  button.position.set(x, y, 0);
  button.userData = {
    action, label, color, hoverColor, canvas, texture,
    ctx: canvas.getContext('2d'), hovered: false,
  };
  updateVRControlButton(button);
  vrControlTargets.push(button);
  vrControlPanel.add(button);
  return button;
}

vrPlayButton = makeVRControlButton('PLAY', 'toggle_play', '#007E63', '#00B887', -0.78, 0.12);
makeVRControlButton('BACK 5S', 'seek_back', '#273451', '#3A4D75', 0, 0.12);
makeVRControlButton('FWD 5S', 'seek_forward', '#273451', '#3A4D75', 0.78, 0.12);
vrBrakeButton = makeVRControlButton('BRAKE', 'brake', '#C91F42', '#FF2D55', -0.78, -0.12);
makeVRControlButton('STOP', 'stop', '#273451', '#495D87', 0, -0.12);
makeVRControlButton('RESET', 'reset', '#273451', '#495D87', 0.78, -0.12);

const vrHintCanvas = document.createElement('canvas');
vrHintCanvas.width = 960;
vrHintCanvas.height = 56;
const vrHintCtx = vrHintCanvas.getContext('2d');
vrHintCtx.fillStyle = '#9BA8BF';
vrHintCtx.font = '600 24px sans-serif';
vrHintCtx.textAlign = 'center';
vrHintCtx.textBaseline = 'middle';
vrHintCtx.fillText('POINT + TRIGGER = SELECT   |   GRIP + DRAG = MOVE SCREEN', 480, 28);
const vrHintTexture = new THREE.CanvasTexture(vrHintCanvas);
vrHintTexture.colorSpace = THREE.SRGBColorSpace;
const vrHint = new THREE.Mesh(
  new THREE.PlaneGeometry(2.24, 0.13),
  new THREE.MeshBasicMaterial({ map: vrHintTexture, transparent: true })
);
vrHint.position.set(0, -0.29, 0);
vrControlPanel.add(vrHint);

// Track alert updates (texture comes from the <img> element directly)
let pendingAlert = null;
const alertColors = {
  SAFE:     0x30D158,
  CAUTION:  0xFFD60A,
  WARNING:  0xFF9F0A,
  CRITICAL: 0xFF2D55,
};

function applyAlertVisuals(level) {
  const c = alertColors[level] ?? 0x000000;
  glowMat.color.setHex(c);
  glowMat.opacity = level === 'CRITICAL' ? 0.35 : (level === 'WARNING' ? 0.20 : (level === 'CAUTION' ? 0.12 : 0));
  stripMat.opacity = level === 'CRITICAL' ? 0.85 : 0;
}

// VR controllers: trigger brakes, grip repositions the windshield, and face
// buttons provide playback controls while retaining a reset shortcut.
const xrControllers = [];

function buildControllerVisual() {
  // Visible laser pointer pointing forward from the controller, plus a small
  // sphere at the controller tip. Tip color reflects current button state.
  const group = new THREE.Group();

  const rayGeom = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -3),
  ]);
  const rayMat = new THREE.LineBasicMaterial({ color: 0x00E5A0, transparent: true, opacity: 0.6 });
  const ray = new THREE.Line(rayGeom, rayMat);
  group.add(ray);

  const tipMat = new THREE.MeshBasicMaterial({ color: 0xE8ECF4 });
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 16), tipMat);
  tip.position.z = -0.02;
  group.add(tip);

  return { group, ray, tip, rayMat, tipMat };
}

const vrControlRaycaster = new THREE.Raycaster();
const vrControlRayRotation = new THREE.Matrix4();
let hoveredVRControl = null;

function targetUnderController(controller) {
  controller.updateWorldMatrix(true, false);
  vrControlPanel.updateWorldMatrix(true, true);
  vrControlRayRotation.identity().extractRotation(controller.matrixWorld);
  vrControlRaycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
  vrControlRaycaster.ray.direction.set(0, 0, -1).applyMatrix4(vrControlRayRotation).normalize();
  const hits = vrControlRaycaster.intersectObjects(vrControlTargets, false);
  return hits.length ? hits[0].object : null;
}

function updateVRControlHover() {
  let nextHovered = null;
  for (const controller of xrControllers) {
    const target = targetUnderController(controller);
    if (target) {
      nextHovered = target;
      break;
    }
  }
  if (nextHovered === hoveredVRControl) return;
  if (hoveredVRControl) updateVRControlButton(hoveredVRControl, hoveredVRControl.userData.label, false);
  hoveredVRControl = nextHovered;
  if (hoveredVRControl) updateVRControlButton(hoveredVRControl, hoveredVRControl.userData.label, true);
}

function activateVRControl(button) {
  const action = button.userData.action;
  if (action === 'brake') {
    sendBrake('controller_panel');
  } else if (action === 'reset') {
    resetView();
  } else if (action === 'seek_back' || action === 'seek_forward') {
    sendControl(action, 'controller_panel', { seconds: 5 });
  } else {
    sendControl(action, 'controller_panel');
  }
}

function setupController(index) {
  const ctrl = renderer.xr.getController(index);
  const vis = buildControllerVisual();
  ctrl.add(vis.group);  // visual moves with the controller
  ctrl.userData.vis = vis;
  ctrl.userData.grabbing = false;

  // ── Connection lifecycle ──
  ctrl.addEventListener('connected', (e) => {
    console.log(`[WebXR] controller ${index} connected:`, e.data.handedness, e.data.profiles);
    ctrl.userData.handedness = e.data.handedness;
  });
  ctrl.addEventListener('disconnected', () => {
    console.log(`[WebXR] controller ${index} disconnected`);
  });

  // Trigger selects an in-world control when pointed at it; elsewhere it brakes.
  ctrl.addEventListener('selectstart', () => {
    console.log(`[WebXR] controller ${index} trigger`);
    const target = targetUnderController(ctrl);
    if (target) {
      activateVRControl(target);
      vis.tipMat.color.setHex(0x00E5A0);
      setTimeout(() => vis.tipMat.color.setHex(0xE8ECF4), 200);
      return;
    }
    vis.tipMat.color.setHex(0xFF2D55);   // tip turns red briefly
    setTimeout(() => vis.tipMat.color.setHex(0xE8ECF4), 200);
    sendBrake('controller');
  });

  // ── Grip → grab the windshield group ──
  ctrl.addEventListener('squeezestart', () => {
    console.log(`[WebXR] controller ${index} grip pressed — grabbing windshield`);
    ctrl.userData.grabbing = true;
    vis.tipMat.color.setHex(0x00E5A0);   // mint = grabbing
    vis.rayMat.color.setHex(0x00E5A0);
    ctrl.attach(windshieldGroup);
  });
  ctrl.addEventListener('squeezeend', () => {
    console.log(`[WebXR] controller ${index} grip released`);
    ctrl.userData.grabbing = false;
    vis.tipMat.color.setHex(0xE8ECF4);
    vis.rayMat.color.setHex(0x00E5A0);
    scene.attach(windshieldGroup);
  });

  playerRig.add(ctrl);
  xrControllers.push(ctrl);
}
setupController(0);
setupController(1);

const controllerButtonState = new Map();
const CONTROLLER_BACK_BUTTON_INDEXES = [8];
const LEFT_BRAKE_BUTTON_INDEXES = [4, 5];

function pressedOnce(source, index) {
  const key = `${source.handedness}:${index}`;
  const pressed = Boolean(source.gamepad.buttons[index]?.pressed);
  const prior = controllerButtonState.get(key) || false;
  controllerButtonState.set(key, pressed);
  return pressed && !prior;
}

function resetView() {
  if (windshieldGroup.parent !== scene) scene.attach(windshieldGroup);
  windshieldGroup.position.copy(WINDSHIELD_DEFAULT_POS);
  windshieldGroup.quaternion.copy(WINDSHIELD_DEFAULT_QUAT);
  windshieldGroup.scale.set(1, 1, 1);
  playerRig.position.set(0, 0, 0);
  playerRig.rotation.set(0, 0, 0);
  console.log('[WebXR] reset windshield + player rig');
}

function pollControllerButtons() {
  const session = renderer.xr.getSession();
  if (!session) return;
  for (const src of session.inputSources) {
    if (!src.gamepad) continue;
    if (CONTROLLER_BACK_BUTTON_INDEXES.some(index => pressedOnce(src, index))) {
      sendBrake('controller_back_button');
    }
    if (src.handedness === 'left') {
      // Quest Browser button indexes vary between builds, so both left face
      // buttons are treated as brake. Pause remains on right A and the VR panel.
      if (LEFT_BRAKE_BUTTON_INDEXES.some(index => pressedOnce(src, index))) {
        sendBrake('controller_left_y');
      }
    } else if (src.handedness === 'right') {
      if (pressedOnce(src, 4)) sendControl('toggle_play', 'controller_right_a');
      if (pressedOnce(src, 5)) resetView();
    }
  }
}

// VR locomotion — read thumbstick axes from the Quest controllers and move
// the camera rig. Left stick = walk/strafe (camera-relative), right stick =
// snap-turn left/right + up/down (vertical).
const _xrFwd = new THREE.Vector3();
const _xrRight = new THREE.Vector3();
const _xrUp = new THREE.Vector3(0, 1, 0);
const VR_WALK_SPEED = 1.4;   // m/s
const VR_SNAP_TURN_DEG = 30; // per stick deflection past threshold
let _lastSnapTurnTime = 0;

function pickThumbstickAxes(gamepad) {
  // Quest controllers report axes [touchpad-x, touchpad-y, stick-x, stick-y].
  // Some xr-standard mappings only report the stick at indices 0/1. Use whichever
  // pair has non-zero values (or fall back to the larger absolute magnitude).
  const a = gamepad.axes;
  const pair23 = [a[2] || 0, a[3] || 0];
  const pair01 = [a[0] || 0, a[1] || 0];
  // Prefer axes[2,3] (xr-standard for thumbstick), fall back to [0,1]
  const m23 = Math.hypot(pair23[0], pair23[1]);
  const m01 = Math.hypot(pair01[0], pair01[1]);
  return m23 > 0.05 ? pair23 : (m01 > 0.05 ? pair01 : pair23);
}

function pollXRGamepads(dtSec) {
  const session = renderer.xr.getSession();
  if (!session) return;

  const xrCamera = renderer.xr.getCamera(camera);
  xrCamera.updateWorldMatrix(true, false);
  xrCamera.getWorldDirection(_xrFwd);
  _xrFwd.y = 0; _xrFwd.normalize();
  _xrRight.crossVectors(_xrFwd, _xrUp).normalize();

  for (const src of session.inputSources) {
    if (!src.gamepad) continue;
    const [sx, sy] = pickThumbstickAxes(src.gamepad);
    const handedness = src.handedness; // 'left' / 'right' / 'none'
    const dz = 0.18;

    if (handedness === 'left' || handedness === 'none') {
      // Walk + strafe — camera-relative
      if (Math.abs(sy) > dz) playerRig.position.addScaledVector(_xrFwd, -sy * VR_WALK_SPEED * dtSec);
      if (Math.abs(sx) > dz) playerRig.position.addScaledVector(_xrRight, sx * VR_WALK_SPEED * dtSec);
    } else if (handedness === 'right') {
      // Snap-turn (yaw) on x — comfort feature
      if (Math.abs(sx) > 0.7 && performance.now() - _lastSnapTurnTime > 300) {
        const yaw = THREE.MathUtils.degToRad(VR_SNAP_TURN_DEG) * Math.sign(sx);
        playerRig.rotation.y -= yaw;
        _lastSnapTurnTime = performance.now();
      }
      // Vertical move on y
      if (Math.abs(sy) > dz) playerRig.position.y += -sy * VR_WALK_SPEED * dtSec;
    }
  }
}

// Custom ENTER VR button with explicit error messages — the stock Three.js
// VRButton hides why it fails. We want the Quest user to see what went wrong.
const vrButton = document.createElement('button');
vrButton.textContent = 'ENTER VR';
vrButton.className = btnVR.className;
vrButton.style.cssText =
  'flex:1; padding:14px 20px; border-radius:8px; border:none;' +
  'background:#00E5A0; color:#06080F; font-weight:700; font-size:13px;' +
  'letter-spacing:1px; cursor:pointer;';
btnVR.parentNode.replaceChild(vrButton, btnVR);

let currentXRSession = null;

vrButton.addEventListener('click', async () => {
  if (currentXRSession) {
    currentXRSession.end();
    return;
  }
  try {
    if (!('xr' in navigator)) {
      throw new Error('WebXR API not available in this browser');
    }
    const ok = await navigator.xr.isSessionSupported('immersive-vr');
    if (!ok) {
      throw new Error('Immersive VR not supported (need HTTPS + a WebXR-capable browser)');
    }
    vrButton.textContent = 'STARTING…';
    const session = await navigator.xr.requestSession('immersive-vr', {
      optionalFeatures: ['local-floor', 'bounded-floor', 'hand-tracking'],
    });
    currentXRSession = session;
    session.addEventListener('end', () => {
      currentXRSession = null;
      vrButton.textContent = 'ENTER VR';
    });
    vrButton.textContent = 'EXIT VR';
    await renderer.xr.setSession(session);
  } catch (err) {
    vrButton.textContent = 'ENTER VR';
    alert('VR couldn\'t start: ' + err.message);
    console.error('[WebXR] session error', err);
  }
});

// Check at page-load whether VR is even available; reflect in button label
if (navigator.xr) {
  navigator.xr.isSessionSupported('immersive-vr').then(supported => {
    if (!supported) vrButton.textContent = 'VR UNAVAILABLE';
  }).catch(() => { vrButton.textContent = 'VR UNAVAILABLE'; });
} else {
  vrButton.textContent = 'NO WEBXR';
}

// Preview 3D — desktop fallback that renders the same scene with mouse controls
let orbitControls = null;
const btnPreview3D = document.getElementById('btn-preview3d');
btnPreview3D.addEventListener('click', () => {
  const active = renderer.domElement.style.display === 'block';
  if (active) {
    exitPreview3D();
  } else {
    enterPreview3D();
  }
});

let exitButton = null;

function enterPreview3D() {
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.position = 'fixed';
  renderer.domElement.style.inset = '0';
  renderer.domElement.style.zIndex = '100';

  // Hide the floating Three.js VRButton (it's position:absolute and escapes z-index containment)
  if (vrButton) vrButton.style.visibility = 'hidden';

  // Desktop preview starts from a stable view even after the participant moved in VR.
  playerRig.position.set(0, 0, 0);
  playerRig.rotation.set(0, 0, 0);
  camera.position.set(0.6, 1.7, 0.4);
  camera.lookAt(0, 1.6, -1.6);

  orbitControls = new OrbitControls(camera, renderer.domElement);
  orbitControls.target.set(0, 1.6, -1.6);
  orbitControls.enableDamping = true;
  orbitControls.dampingFactor = 0.08;
  orbitControls.minDistance = 0.5;
  orbitControls.maxDistance = 6.0;
  orbitControls.update();

  btnPreview3D.textContent = 'EXIT PREVIEW (Esc)';
  showPreviewHint();
  showExitButton();
}

function exitPreview3D() {
  renderer.domElement.style.display = 'none';
  if (orbitControls) { orbitControls.dispose(); orbitControls = null; }
  if (vrButton) vrButton.style.visibility = 'visible';
  btnPreview3D.textContent = 'PREVIEW 3D';
  if (previewHint) { previewHint.remove(); previewHint = null; }
  if (exitButton) { exitButton.remove(); exitButton = null; }
}

function showExitButton() {
  console.log('[WebXR] creating EXIT button');
  exitButton = document.createElement('button');
  exitButton.textContent = '✕  EXIT';
  Object.assign(exitButton.style, {
    position: 'fixed',
    top: '20px',
    right: '20px',
    zIndex: '110',                    // above the canvas (which is z-index 100)
    pointerEvents: 'auto',
    background: 'rgba(12, 16, 33, 0.92)',
    color: '#E8ECF4',
    border: '1px solid #1A2038',
    borderRadius: '8px',
    padding: '10px 20px',
    fontSize: '13px',
    fontWeight: '700',
    letterSpacing: '1px',
    fontFamily: 'sans-serif',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
  });
  exitButton.addEventListener('mouseenter', () => {
    exitButton.style.background = '#FF2D55';
    exitButton.style.color = '#FFFFFF';
  });
  exitButton.addEventListener('mouseleave', () => {
    exitButton.style.background = 'rgba(12, 16, 33, 0.92)';
    exitButton.style.color = '#E8ECF4';
  });
  exitButton.addEventListener('click', exitPreview3D);
  document.body.appendChild(exitButton);
}

let previewHint = null;
function showPreviewHint() {
  previewHint = document.createElement('div');
  previewHint.innerHTML =
    '<b>WASD</b> walk  ·  <b>Q/E</b> down/up  ·  <b>Shift</b> faster  ·  ' +
    '<b>Drag</b> look  ·  <b>Scroll</b> zoom  ·  <b>B</b> brake  ·  <b>Esc</b> exit';
  Object.assign(previewHint.style, {
    position: 'fixed', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
    zIndex: '11', background: 'rgba(12,16,33,0.85)', color: '#E8ECF4',
    padding: '10px 20px', borderRadius: '8px', fontSize: '12px',
    letterSpacing: '1px', fontFamily: 'sans-serif', pointerEvents: 'none',
    border: '1px solid #1A2038',
  });
  document.body.appendChild(previewHint);
}

// On entering / exiting VR, swap renderer visibility
renderer.xr.addEventListener('sessionstart', () => {
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.position = 'fixed';
  renderer.domElement.style.inset = '0';
  renderer.domElement.style.zIndex = '10';
  console.log('[WebXR] session started');

  // Reflect inputSources changes in the console so we know if controllers connect
  const session = renderer.xr.getSession();
  const logSources = () => {
    const sources = Array.from(session.inputSources).map(s =>
      `${s.handedness}/${s.gamepad ? `${s.gamepad.buttons.length}btn` : 'no-gamepad'}`
    );
    console.log('[WebXR] inputSources:', sources.join(', ') || '(none)');
  };
  logSources();
  session.addEventListener('inputsourceschange', logSources);
});
renderer.xr.addEventListener('sessionend', () => {
  renderer.domElement.style.display = 'none';
  console.log('[WebXR] session ended');
});

window.addEventListener('resize', () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
});

renderer.setAnimationLoop(() => {
  // Swap to the canvas-backed texture as soon as a real frame has been drawn
  if (hasFirstFrame && windshieldMat.map !== windshieldTexture) {
    windshieldMat.map = windshieldTexture;
    windshieldMat.needsUpdate = true;
  }
  if (pendingAlert) {
    applyAlertVisuals(pendingAlert);
    pendingAlert = null;
  }
  if (orbitControls) {
    applyWalkMovement();
    orbitControls.update();
  }
  // In immersive VR, poll thumbstick locomotion and controller shortcuts.
  if (renderer.xr.isPresenting) {
    const now = performance.now();
    const dt = Math.min(0.1, (now - _xrLastT) / 1000);
    _xrLastT = now;
    pollXRGamepads(dt);
    pollControllerButtons();
    updateVRControlHover();
  } else {
    _xrLastT = performance.now();
  }
  renderer.render(scene, camera);
});

let _xrLastT = performance.now();

// Escape exits preview / VR fullscreen
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && orbitControls) {
    exitPreview3D();
  }
});

// ── WASD/QE walk movement on top of orbit controls ──
const moveKeys = new Set();
const MOVE_SPEED = 1.6;    // metres per second
const FAST_MULT  = 2.8;

window.addEventListener('keydown', (e) => {
  if (!orbitControls) return;          // only active while preview is open
  const k = e.key.toLowerCase();
  if (['w', 'a', 's', 'd', 'q', 'e', 'shift'].includes(k)) {
    moveKeys.add(k);
    e.preventDefault();
  }
});
window.addEventListener('keyup', (e) => {
  moveKeys.delete(e.key.toLowerCase());
});

const _fwd = new THREE.Vector3();
const _right = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);
let _lastMoveT = performance.now();

function applyWalkMovement() {
  if (!orbitControls) return;
  const now = performance.now();
  const dt = Math.min(0.1, (now - _lastMoveT) / 1000);   // clamp to avoid jumps
  _lastMoveT = now;
  if (moveKeys.size === 0) return;

  // Direction the camera is looking, projected onto the ground plane
  camera.getWorldDirection(_fwd);
  _fwd.y = 0; _fwd.normalize();
  _right.crossVectors(_fwd, _up).normalize();

  const speed = (moveKeys.has('shift') ? FAST_MULT : 1) * MOVE_SPEED * dt;
  const delta = new THREE.Vector3();
  if (moveKeys.has('w')) delta.addScaledVector(_fwd,    speed);
  if (moveKeys.has('s')) delta.addScaledVector(_fwd,   -speed);
  if (moveKeys.has('d')) delta.addScaledVector(_right,  speed);
  if (moveKeys.has('a')) delta.addScaledVector(_right, -speed);
  if (moveKeys.has('e')) delta.y += speed;
  if (moveKeys.has('q')) delta.y -= speed;

  // Move both the camera and the orbit target together (so orbit keeps working)
  camera.position.add(delta);
  orbitControls.target.add(delta);
}

connect();
