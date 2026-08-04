"use strict";

// ---- State ---------------------------------------------------------------
const state = {
  file: null,
  layers: [],       // [{z, segments:[{x1,y1,x2,y2,kind}]}]
  gcode: "",
  current: 0,
  bounds: null,     // {minX,maxX,minY,maxY}
  playing: false,
  timer: null,
};

const COLORS = {
  perimeter: "#4da3ff",
  infill: "#ff9f43",
  travel: "rgba(120,132,160,0.35)",
};

// ---- Element handles -----------------------------------------------------
const el = (id) => document.getElementById(id);
const stlInput = el("stl");
const fileLabel = el("file-label");
const sliceBtn = el("slice-btn");
const downloadBtn = el("download-btn");
const statusEl = el("status");
const statsEl = el("stats");
const canvas = el("canvas");
const ctx = canvas.getContext("2d");
const slider = el("layer-slider");
const layerLabel = el("layer-label");
const prevBtn = el("prev");
const nextBtn = el("next");
const playBtn = el("play");
const ghostChk = el("ghost");

const PARAM_IDS = [
  "layer_height", "extrusion_width", "perimeters", "wall_thickness",
  "infill_percentage", "infill_type", "angular_steps",
];

// ---- File selection ------------------------------------------------------
stlInput.addEventListener("change", () => {
  state.file = stlInput.files[0] || null;
  fileLabel.textContent = state.file ? state.file.name : "Choose an STL file…";
  sliceBtn.disabled = !state.file;
});

// ---- Slice ---------------------------------------------------------------
sliceBtn.addEventListener("click", async () => {
  if (!state.file) return;
  stopPlaying();
  setStatus("Slicing…", "busy");
  sliceBtn.disabled = true;

  const form = new FormData();
  form.append("stl", state.file);
  for (const id of PARAM_IDS) form.append(id, el(id).value);

  try {
    const resp = await fetch("/api/slice", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Slicing failed.");

    state.gcode = data.gcode;
    state.layers = data.layers;
    state.current = 0;
    computeBounds();

    if (state.layers.length === 0) {
      setStatus("No layers produced — check parameters vs model size.", "err");
    } else {
      setStatus("Done.", "ok");
    }
    renderStats(data.stats);
    setupViewer();
  } catch (err) {
    setStatus(err.message, "err");
  } finally {
    sliceBtn.disabled = false;
  }
});

// ---- Download ------------------------------------------------------------
downloadBtn.addEventListener("click", () => {
  if (!state.gcode) return;
  const blob = new Blob([state.gcode], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const base = (state.file && state.file.name.replace(/\.stl$/i, "")) || "model";
  a.href = url;
  a.download = base + ".gcode";
  a.click();
  URL.revokeObjectURL(url);
});

// ---- Viewer setup --------------------------------------------------------
function setupViewer() {
  const n = state.layers.length;
  const hasLayers = n > 0;
  slider.max = Math.max(0, n - 1);
  slider.value = 0;
  slider.disabled = !hasLayers;
  prevBtn.disabled = nextBtn.disabled = playBtn.disabled = !hasLayers;
  downloadBtn.disabled = !state.gcode;
  drawLayer();
}

slider.addEventListener("input", () => {
  state.current = Number(slider.value);
  drawLayer();
});
prevBtn.addEventListener("click", () => step(-1));
nextBtn.addEventListener("click", () => step(1));
ghostChk.addEventListener("change", drawLayer);
playBtn.addEventListener("click", () => (state.playing ? stopPlaying() : startPlaying()));

function step(delta) {
  const n = state.layers.length;
  if (!n) return;
  state.current = (state.current + delta + n) % n;
  slider.value = state.current;
  drawLayer();
}

function startPlaying() {
  if (!state.layers.length) return;
  state.playing = true;
  playBtn.textContent = "Pause";
  state.timer = setInterval(() => step(1), 120);
}
function stopPlaying() {
  state.playing = false;
  playBtn.textContent = "Play";
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
}

// ---- Geometry / drawing --------------------------------------------------
function computeBounds() {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const layer of state.layers) {
    for (const s of layer.segments) {
      minX = Math.min(minX, s.x1, s.x2);
      maxX = Math.max(maxX, s.x1, s.x2);
      minY = Math.min(minY, s.y1, s.y2);
      maxY = Math.max(maxY, s.y1, s.y2);
    }
  }
  if (!isFinite(minX)) { minX = maxX = minY = maxY = 0; }
  state.bounds = { minX, maxX, minY, maxY };
}

function transformer() {
  const b = state.bounds;
  const pad = 24;
  const w = canvas.width - pad * 2;
  const h = canvas.height - pad * 2;
  const spanX = Math.max(b.maxX - b.minX, 1e-6);
  const spanY = Math.max(b.maxY - b.minY, 1e-6);
  const scale = Math.min(w / spanX, h / spanY);
  const cx = (b.minX + b.maxX) / 2;
  const cy = (b.minY + b.maxY) / 2;
  // Center the model; flip Y so +Y points up like a print bed.
  return {
    x: (x) => canvas.width / 2 + (x - cx) * scale,
    y: (y) => canvas.height / 2 - (y - cy) * scale,
  };
}

function drawSegments(t, segments, alpha) {
  // Group by color to minimise strokeStyle switches.
  for (const kind of ["travel", "infill", "perimeter"]) {
    ctx.beginPath();
    ctx.strokeStyle = COLORS[kind];
    ctx.globalAlpha = alpha * (kind === "travel" ? 1 : 1);
    ctx.lineWidth = kind === "perimeter" ? 1.6 : 1.2;
    let drew = false;
    for (const s of segments) {
      if (s.kind !== kind) continue;
      ctx.moveTo(t.x(s.x1), t.y(s.y1));
      ctx.lineTo(t.x(s.x2), t.y(s.y2));
      drew = true;
    }
    if (drew) ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

function drawLayer() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!state.layers.length) {
    layerLabel.textContent = "—";
    return;
  }
  const t = transformer();

  // Optional ghost of all lower layers.
  if (ghostChk.checked) {
    for (let i = 0; i < state.current; i++) {
      drawSegments(t, ghostFilter(state.layers[i].segments), 0.12);
    }
  }

  const layer = state.layers[state.current];
  drawSegments(t, layer.segments, 1);

  layerLabel.textContent =
    `Layer ${state.current + 1}/${state.layers.length}  ·  z=${layer.z.toFixed(2)}`;
}

// Ghost layers only show extrusions, not travels, to reduce clutter.
function ghostFilter(segments) {
  return segments.filter((s) => s.kind !== "travel");
}

// ---- Helpers -------------------------------------------------------------
function setStatus(msg, cls) {
  statusEl.textContent = msg;
  statusEl.className = "status " + (cls || "");
}
function renderStats(stats) {
  if (!stats) { statsEl.textContent = ""; return; }
  statsEl.innerHTML =
    `Layers: <b>${stats.layer_count}</b> &nbsp;·&nbsp; ` +
    `Segments: <b>${stats.segment_count}</b> &nbsp;·&nbsp; ` +
    `G-code lines: <b>${stats.gcode_lines}</b>`;
}
