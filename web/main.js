// DepthGuard WebXR companion — Three.js scene + WebSocket client.
// Renders the live dashcam frame on a virtual windshield in front of the user,
// reflects the alert state as ambient lighting + bottom HUD strip,
// and sends brake-press events back to DepthGuard.

import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ─── DOM refs ────────────────────────────────────────────────
const previewImg = document.getElementById('frame-preview');
const alertBar   = document.getElementById('alert-bar');
const connDot    = document.getElementById('conn-dot');
const connText   = document.getElementById('conn-text');
const metaCond   = document.getElementById('meta-condition');
const metaTrial  = document.getElementById('meta-trial');
const metaLat    = document.getElementById('meta-latency');
const btnVR      = document.getElementById('btn-vr');
const btnBrake   = document.getElementById('btn-brake');

// ─── WebSocket setup ─────────────────────────────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsURL = `${wsProtocol}://${window.location.host}/ws`;
let ws = null;
let latestFrame = null;     // {imageBitmap, alert, trial}
let latencyPing = 0;        // last measured RTT in ms

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
  } else if (msg.type === 'trial_start' || msg.type === 'block_start' || msg.type === 'session_end') {
    if (msg.data && msg.data.label) {
      metaTrial.textContent = msg.data.label;
    }
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

const windshieldTexture = new THREE.CanvasTexture(frameCanvas);
windshieldTexture.colorSpace = THREE.SRGBColorSpace;
windshieldTexture.minFilter = THREE.LinearFilter;
windshieldTexture.magFilter = THREE.LinearFilter;
windshieldTexture.generateMipmaps = false;
windshieldTexture.wrapS = THREE.ClampToEdgeWrapping;
windshieldTexture.wrapT = THREE.ClampToEdgeWrapping;

let hasFirstFrame = false;
previewImg.addEventListener('load', () => {
  // Letterbox-fit the incoming image into the fixed canvas
  frameCtx.fillStyle = '#000';
  frameCtx.fillRect(0, 0, frameCanvas.width, frameCanvas.height);
  const iw = previewImg.naturalWidth;
  const ih = previewImg.naturalHeight;
  if (iw > 0 && ih > 0) {
    const scale = Math.min(frameCanvas.width / iw, frameCanvas.height / ih);
    const dw = iw * scale, dh = ih * scale;
    const dx = (frameCanvas.width - dw) / 2;
    const dy = (frameCanvas.height - dh) / 2;
    frameCtx.drawImage(previewImg, dx, dy, dw, dh);
    hasFirstFrame = true;
    windshieldTexture.needsUpdate = true;
  }
});

// ─── Brake handling ──────────────────────────────────────────
function sendBrake(source) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    type: 'brake',
    source,                                // 'controller' / 'keyboard' / 'click'
    t_client: performance.now(),
    latency_hint_ms: latencyPing,
  }));
  // Visual flash
  btnBrake.style.filter = 'brightness(1.5)';
  setTimeout(() => btnBrake.style.filter = '', 150);
}

btnBrake.addEventListener('click', () => sendBrake('click'));
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' || e.code === 'KeyB') {
    e.preventDefault();
    sendBrake('keyboard');
  }
});

// ─── Three.js scene + WebXR ──────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x06080F);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.6, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true;
renderer.domElement.style.display = 'none'; // hide until VR enters
document.body.appendChild(renderer.domElement);

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
const windshieldMat = new THREE.MeshBasicMaterial({ map: placeholderTex, side: THREE.DoubleSide });
const windshield = new THREE.Mesh(windshieldGeom, windshieldMat);
windshield.position.set(0, 1.6, -1.6);
scene.add(windshield);

// Bottom HUD strip (initially invisible; lights up red on CRITICAL)
const stripGeom = new THREE.PlaneGeometry(2.4, 0.08);
const stripMat = new THREE.MeshBasicMaterial({ color: 0xff2d55, transparent: true, opacity: 0 });
const strip = new THREE.Mesh(stripGeom, stripMat);
strip.position.set(0, 1.6 - 0.7, -1.59);
scene.add(strip);

// Subtle ambient glow box behind the windshield — color shifts with alert
const glowGeom = new THREE.PlaneGeometry(3.6, 2.0);
const glowMat = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.0 });
const glow = new THREE.Mesh(glowGeom, glowMat);
glow.position.set(0, 1.6, -1.7);
scene.add(glow);

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

// VR controllers — both triggers count as a brake press
function setupController(index) {
  const ctrl = renderer.xr.getController(index);
  ctrl.addEventListener('selectstart', () => sendBrake('controller'));
  scene.add(ctrl);
}
setupController(0);
setupController(1);

// VR enter button — replace our custom button with Three.js's VRButton.
// Three.js needs to handle the click itself so the user gesture context propagates
// (browsers reject programmatic WebXR session requests).
const vrButton = VRButton.createButton(renderer);
vrButton.style.position = 'static';
vrButton.style.transform = 'none';
vrButton.style.left = 'unset';
vrButton.style.bottom = 'unset';
vrButton.style.width = '100%';
vrButton.style.height = '46px';
vrButton.style.flex = '1';
vrButton.style.padding = '14px 20px';
vrButton.style.borderRadius = '8px';
vrButton.style.border = 'none';
vrButton.style.background = '#00E5A0';
vrButton.style.color = '#06080F';
vrButton.style.fontWeight = '700';
vrButton.style.fontSize = '13px';
vrButton.style.letterSpacing = '1px';
vrButton.style.cursor = 'pointer';
vrButton.style.opacity = '1';
btnVR.parentNode.replaceChild(vrButton, btnVR);

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

function enterPreview3D() {
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.position = 'fixed';
  renderer.domElement.style.inset = '0';
  renderer.domElement.style.zIndex = '100';

  // Hide the floating Three.js VRButton (it's position:absolute and escapes z-index containment)
  if (vrButton) vrButton.style.visibility = 'hidden';

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
}

function exitPreview3D() {
  renderer.domElement.style.display = 'none';
  if (orbitControls) { orbitControls.dispose(); orbitControls = null; }
  if (vrButton) vrButton.style.visibility = 'visible';
  btnPreview3D.textContent = 'PREVIEW 3D';
  if (previewHint) { previewHint.remove(); previewHint = null; }
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
});
renderer.xr.addEventListener('sessionend', () => {
  renderer.domElement.style.display = 'none';
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
  renderer.render(scene, camera);
});

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
