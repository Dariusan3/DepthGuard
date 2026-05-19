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
  } else if (msg.type === 'playback') {
    setPaused(msg.data && !msg.data.playing);
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

// VR controllers — trigger = brake, grip (squeeze) = grab-to-move windshield,
// A/X or B/Y button = reset windshield + camera to default position.
const xrControllers = [];

function buildControllerVisual() {
  // Visible 1m laser pointer pointing forward from the controller, plus a small
  // sphere at the controller tip. Tip color reflects current button state.
  const group = new THREE.Group();

  const rayGeom = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1),
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

  // ── Trigger → brake ──
  ctrl.addEventListener('selectstart', () => {
    console.log(`[WebXR] controller ${index} trigger`);
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

  scene.add(ctrl);
  xrControllers.push(ctrl);
}
setupController(0);
setupController(1);

// Reset button — A/X (button index 4) or B/Y (button index 5) on Quest controllers.
// Polled in the animation loop with a debounce so a single press doesn't fire
// every frame the button is held.
let _resetCooldown = 0;
function pollResetButton(dtSec) {
  const session = renderer.xr.getSession();
  if (!session) return;
  _resetCooldown = Math.max(0, _resetCooldown - dtSec);
  if (_resetCooldown > 0) return;
  for (const src of session.inputSources) {
    if (!src.gamepad) continue;
    const btns = src.gamepad.buttons;
    if ((btns[4] && btns[4].pressed) || (btns[5] && btns[5].pressed)) {
      // Make sure the group is back under the scene (not a controller)
      if (windshieldGroup.parent !== scene) scene.attach(windshieldGroup);
      windshieldGroup.position.copy(WINDSHIELD_DEFAULT_POS);
      windshieldGroup.quaternion.copy(WINDSHIELD_DEFAULT_QUAT);
      windshieldGroup.scale.set(1, 1, 1);
      // Also recenter the user's stage to origin
      camera.position.set(0, 1.6, 0);
      camera.rotation.set(0, 0, 0);
      _resetCooldown = 0.5;
      console.log('[WebXR] reset windshield + camera');
      return;
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

  camera.getWorldDirection(_xrFwd);
  _xrFwd.y = 0; _xrFwd.normalize();
  _xrRight.crossVectors(_xrFwd, _xrUp).normalize();

  for (const src of session.inputSources) {
    if (!src.gamepad) continue;
    const [sx, sy] = pickThumbstickAxes(src.gamepad);
    const handedness = src.handedness; // 'left' / 'right' / 'none'
    const dz = 0.18;

    if (handedness === 'left' || handedness === 'none') {
      // Walk + strafe — camera-relative
      if (Math.abs(sy) > dz) camera.position.addScaledVector(_xrFwd, -sy * VR_WALK_SPEED * dtSec);
      if (Math.abs(sx) > dz) camera.position.addScaledVector(_xrRight, sx * VR_WALK_SPEED * dtSec);
    } else if (handedness === 'right') {
      // Snap-turn (yaw) on x — comfort feature
      if (Math.abs(sx) > 0.7 && performance.now() - _lastSnapTurnTime > 300) {
        const yaw = THREE.MathUtils.degToRad(VR_SNAP_TURN_DEG) * Math.sign(sx);
        camera.rotation.y -= yaw;
        _lastSnapTurnTime = performance.now();
      }
      // Vertical move on y
      if (Math.abs(sy) > dz) camera.position.y += -sy * VR_WALK_SPEED * dtSec;
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
  // In immersive VR, poll the controllers for thumbstick locomotion + reset button
  if (renderer.xr.isPresenting) {
    const now = performance.now();
    const dt = Math.min(0.1, (now - _xrLastT) / 1000);
    _xrLastT = now;
    pollXRGamepads(dt);
    pollResetButton(dt);
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
