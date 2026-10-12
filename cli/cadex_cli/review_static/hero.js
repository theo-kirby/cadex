// SPDX-License-Identifier: LGPL-2.1-or-later
// The hero page (ADR-677; docs/DASHBOARD.md §26). `cadex hero` draws a project's presentation
// stills and videos here, in headless Chromium, with the dashboard's own scene (review_scene.js)
// on the clean mat and none of the page's chrome. Python drives it one frame at a time and
// encodes what it returns; nothing here runs on its own.
//
//   size(w, h, supersample)  the frame in pixels; the scene draws at `supersample` times that and
//                            is filtered down into it, so a still's edges are smooth
//   load(url)                a model manifest (api/model/...) into the scene
//   fitCamera(o)             the camera that frames the design at {yaw, pitch}, filling `fill` of
//                            the frame; with `yaws`, one distance that holds at every one of them
//                            (a turntable), pivoting on the design's centre
//   shot({camera, layers})   one frame: `layers` [{look, style, wipe}], the first drawn whole and
//                            each later one over it behind a diagonal at `wipe` (0..1) of the way
//   rollout(url, o)          a rollout (api/playback/...) resampled at `fps`, with the follow rig
//   rolloutFrame(i, o)       frame i of it
//   plot(spec)               training curves drawn up to `progress` of their length
//   image(type, quality)     the frame as base64 (png or jpeg)
import {create} from './review_scene.js';

const stage = document.getElementById('stage');
const viewer = create(stage, {labels: false});
//: The lens: longer than the viewport's 55 degrees, so a product shot keeps the design's proportions.
const LENS = 30;
viewer.setFov(LENS);
const out = document.createElement('canvas'), ctx = out.getContext('2d');
//: The dark page's tokens (review.css): the wireframe's paper and ink, and the plot's chrome.
const DARK = {paper: '#1b1b1b', ink: '#d6d6d6'};
const PLOT = {bg: '#141414', ink: '#ededed', ink2: '#9a9a9a', rule: '#3a3a3a', accent: '#dcdcdc', ok: '#8be0b0',
              font: 'system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif'};
//: The wipe: a straight edge sweeping from the top left that turns from `from` to `to` degrees off
//: vertical as it goes, its core lit, a broad band of light round it, a split cyan and amber fringe,
//: a glint running along it and a flash over what it has just revealed.
const WIPE = {from: 38, to: 16, core: 1 / 380, glow: 1 / 45, band: 0.055, fringe: 1 / 260, flash: 0.2, trail: 0.12};
let W = 0, H = 0, model = null, roll = null;

function size(w, h, supersample = 1) {
  W = Math.round(w); H = Math.round(h);
  const s = Math.max(1, Math.min(3, Number(supersample) || 1));
  stage.style.width = W * s + 'px'; stage.style.height = H * s + 'px';
  out.width = W; out.height = H;
  viewer.draw();
  return {width: W, height: H, supersample: s, drawn: [stage.width, stage.height]};
}

async function load(url) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error('model HTTP ' + response.status);
  const manifest = await response.json();
  if (!manifest.available) throw new Error('no model: ' + manifest.reason);
  const parts = await viewer.load(manifest);
  model = manifest;
  return {revision: manifest.revision || null, digest: manifest.digest || null, run: manifest.run || null,
          parts: parts.length, triangles: parts.reduce((n, p) => n + p.triangles, 0)};
}

// The camera's right and up, in the model's z-up frame (review_scene's pan).
function basis(c) {
  const sy = Math.sin(c.yaw), cy = Math.cos(c.yaw), sp = Math.sin(c.pitch), cp = Math.cos(c.pitch);
  return {right: [-sy, cy, 0], up: [-sp * cy, -sp * sy, cp]};
}
function mmPerPixel(c) { return 2 * c.distance * Math.tan(LENS * Math.PI / 360) / (stage.clientHeight || 1); }

function fitCamera({yaw = .8, pitch = .35, fill = .78, yaws = null, views = null, centre = true, lift = 0} = {}) {
  const b = viewer.stats().bounds;
  if (!b) throw new Error('nothing to frame');
  const w = stage.clientWidth, h = stage.clientHeight;
  // Every view the shot will take, {yaw, pitch}: one distance must hold at all of them.
  const shots = Array.isArray(views) && views.length ? views
              : (Array.isArray(yaws) && yaws.length ? yaws : [yaw]).map(y => ({yaw: y, pitch}));
  let c = {yaw, pitch, distance: b.radius * 4, target: b.center.slice()};
  for (let k = 0; k < 8; k++) {
    let need = 0, dx = 0, dy = 0, rise = 0;
    for (const v of shots) {
      viewer.setCamera({...c, yaw: v.yaw, pitch: v.pitch, distance: c.distance * (v.scale || 1)});
      const box = viewer.screenBox();
      if (!box) continue;
      if (shots.length === 1 && centre) {
        // One view: centre the design, then fill by its own extent.
        dx = (box[0] + box[2]) / 2 - w / 2; dy = (box[1] + box[3]) / 2 - h / 2;
        need = Math.max(need, (box[2] - box[0]) / (fill * w), (box[3] - box[1]) / (fill * h));
      } else {
        // A turntable pivots on the centre, so it fills by the reach either side of it; it is
        // centred up and down by the mean of its views.
        rise += ((box[1] + box[3]) / 2 - h / 2) / shots.length;
        need = Math.max(need, Math.max(w / 2 - box[0], box[2] - w / 2) / (fill * w / 2),
                        Math.max(h / 2 - box[1], box[3] - h / 2) / (fill * h / 2));
      }
    }
    if (!(need > 0)) break;
    if (shots.length > 1 && centre) dy = rise;
    const {right, up} = basis(c), mm = mmPerPixel(c);
    c = {...c, distance: c.distance * need, target: c.target.map((t, i) => t + right[i] * dx * mm - up[i] * dy * mm)};
  }
  // `lift` raises the design in the frame by that fraction of its height, for a title under it.
  if (lift) { const {up} = basis(c), mm = mmPerPixel(c); c.target = c.target.map((t, i) => t - up[i] * lift * h * mm); }
  viewer.setCamera(c);
  return c;
}

function paint(layer) {
  viewer.setStyle(layer.style === 'wireframe' ? 'wireframe' : 'shaded', DARK);
  if (layer.look) viewer.setLook(layer.look);
  viewer.setClock(layer.clock ?? null);
  viewer.draw();
}
function blit() {
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(stage, 0, 0, stage.width, stage.height, 0, 0, W, H);
}
// The part of the frame a wipe at `p` has passed: the frame cut by the edge n·x = s.
function wipeEdge(p) {
  const a = (WIPE.from + (WIPE.to - WIPE.from) * p) * Math.PI / 180, n = [Math.cos(a), Math.sin(a)];
  const corners = [[0, 0], [W, 0], [W, H], [0, H]], d = corners.map(q => q[0] * n[0] + q[1] * n[1]);
  const lo = Math.min(...d), hi = Math.max(...d), s = lo + (hi - lo) * p;
  const poly = [];
  corners.forEach((q, i) => {
    const r = corners[(i + 1) % 4], dq = d[i] - s, dr = d[(i + 1) % 4] - s;
    if (dq <= 0) poly.push(q);
    if ((dq < 0) !== (dr < 0)) { const t = dq / (dq - dr); poly.push([q[0] + (r[0] - q[0]) * t, q[1] + (r[1] - q[1]) * t]); }
  });
  return {n, s, poly, lo, hi};
}
// The edge, drawn additively over the frame: a broad band of light, a split fringe, the core and
// a glint that runs along it. Strongest mid-sweep; nothing at either end.
function edge(n, s, p, span) {
  const along = [-n[1], n[0]], L = W + H, o = [n[0] * s, n[1] * s], k = Math.sin(Math.PI * p);
  const line = (offset, colour, width, blur) => {
    const q = [o[0] + n[0] * offset, o[1] + n[1] * offset];
    ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.shadowColor = colour; ctx.shadowBlur = blur;
    ctx.beginPath(); ctx.moveTo(q[0] - along[0] * L, q[1] - along[1] * L); ctx.lineTo(q[0] + along[0] * L, q[1] + along[1] * L); ctx.stroke();
  };
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  // The band: light either side of the edge, wider than the core by far.
  const b = span * WIPE.band * (.6 + .4 * k), band = ctx.createLinearGradient(o[0] - n[0] * b, o[1] - n[1] * b, o[0] + n[0] * b, o[1] + n[1] * b);
  band.addColorStop(0, 'rgba(120,170,255,0)'); band.addColorStop(.5, `rgba(170,205,255,${.24 * k})`); band.addColorStop(1, 'rgba(255,190,120,0)');
  ctx.fillStyle = band; ctx.fillRect(0, 0, W, H);
  // The fringe: cyan behind the edge, amber ahead of it.
  const f = H * WIPE.fringe * (1 + 2 * k);
  line(-f, `rgba(60,220,255,${.55 * k})`, Math.max(1, H * WIPE.core * .8), H * WIPE.glow * .5);
  line(f, `rgba(255,170,60,${.5 * k})`, Math.max(1, H * WIPE.core * .8), H * WIPE.glow * .5);
  // The core.
  line(0, `rgba(255,255,255,${Math.min(1, 1.6 * k)})`, Math.max(1.5, H * WIPE.core * (1 + k)), H * WIPE.glow);
  line(0, `rgba(255,255,255,${.9 * k})`, Math.max(1, H * WIPE.core * .5), 0);
  // The glint: a hot spot running down the edge faster than the edge crosses the frame.
  const t = (p * 1.6) % 1, g = [o[0] + along[0] * (t - .5) * L * .9, o[1] + along[1] * (t - .5) * L * .9], r = H * .12;
  const glint = ctx.createRadialGradient(g[0], g[1], 0, g[0], g[1], r);
  glint.addColorStop(0, `rgba(255,255,255,${.95 * k})`); glint.addColorStop(.15, `rgba(200,230,255,${.45 * k})`); glint.addColorStop(1, 'rgba(120,170,255,0)');
  ctx.shadowBlur = 0; ctx.fillStyle = glint; ctx.beginPath(); ctx.arc(g[0], g[1], r, 0, 2 * Math.PI); ctx.fill();
  ctx.restore();
}
function shot({camera = null, layers = [{look: 'studio'}]} = {}) {
  if (camera) viewer.setCamera(camera);
  // The last layer fully across is the floor of this frame; the ones after it wipe over it.
  let base = 0;
  layers.forEach((l, i) => { if (i === 0 || (l.wipe ?? 1) >= 1) base = i; });
  paint(layers[base]); blit();
  for (let i = base + 1; i < layers.length; i++) {
    const p = layers[i].wipe ?? 0;
    if (!(p > 0)) continue;
    const {n, s, poly, lo, hi} = wipeEdge(p);
    if (poly.length < 3) continue;
    paint(layers[i]);
    ctx.save(); ctx.beginPath(); poly.forEach((q, k) => k ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])); ctx.closePath();
    ctx.clip(); blit();
    // The flash: what the edge has just uncovered is lit, fading behind it.
    const trail = (hi - lo) * WIPE.trail, f0 = s - trail;
    const sheen = ctx.createLinearGradient(n[0] * f0, n[1] * f0, n[0] * s, n[1] * s);
    sheen.addColorStop(0, 'rgba(255,255,255,0)'); sheen.addColorStop(1, `rgba(220,235,255,${WIPE.flash * Math.sin(Math.PI * p)})`);
    ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = sheen; ctx.fillRect(0, 0, W, H);
    ctx.restore();
    edge(n, s, p, hi - lo);
  }
  return true;
}

// A pose between the rollout's samples, as the dashboard's playback blends one (review.js).
function blend(a, b, f) {
  const result = {};
  Object.keys(a).forEach(name => {
    const p = a[name], q = b[name] || p, qa = p.rotation_xyzw;
    let qb = q.rotation_xyzw.slice();
    if (qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3] < 0) qb = qb.map(v => -v);
    const r = qa.map((v, i) => v + (qb[i] - v) * f), m = Math.hypot(...r) || 1;
    result[name] = {position_mm: p.position_mm.map((v, i) => v + (q.position_mm[i] - v) * f), rotation_xyzw: r.map(v => v / m)};
  });
  return result;
}
function poseAt(served, t) {
  const times = served.times_s, last = times.length - 1;
  let lo = 0, hi = last;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (times[mid] <= t) lo = mid; else hi = mid; }
  const span = times[hi] - times[lo];
  return blend(served.frames[lo], served.frames[hi], span > 0 ? Math.max(0, Math.min(1, (t - times[lo]) / span)) : 0);
}
async function rollout(url, {fps = 30, fraction = .42, yaw = .8, pitch = .3, smooth_s = .4, hold_s = 0} = {}) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error('rollout HTTP ' + response.status);
  const served = await response.json();
  if (!served.available || !(served.times_s && served.times_s.length >= 2)) throw new Error('rollout unplayable: ' + (served.reason || 'no frames'));
  const times = served.times_s, end = times[times.length - 1], played = Math.ceil(end * fps) + 1;
  // The last pose is held for `hold_s`, so a clip does not cut on the instant the episode ends.
  const count = played + Math.round(hold_s * fps), clocks = [];
  for (let i = 0; i < count; i++) clocks.push(Math.min(end, i / fps));
  const poses = clocks.map(t => poseAt(served, t));
  const boxes = viewer.boundsOver(poses);
  const lo = [0, 1, 2].map(j => Math.min(...boxes.map(b => b.min[j]))), hi = [0, 1, 2].map(j => Math.max(...boxes.map(b => b.max[j])));
  const dist = Math.hypot(...lo.map((v, j) => hi[j] - v));
  viewer.frameBounds({min: lo, max: hi, center: lo.map((v, j) => (v + hi[j]) / 2), radius: dist / 2 || 1});
  const height = boxes[0].max[2] - boxes[0].min[2];
  if (!(height > 0)) throw new Error('the rollout subject has no height');
  viewer.setCamera({yaw, pitch, distance: dist || 1, target: lo.map((v, j) => (v + hi[j]) / 2)});
  const rig = viewer.follow(boxes.map(b => b.min.map((v, j) => (v + b.max[j]) / 2)),
                            {fraction, subject_height_mm: height, smooth_frames: Math.round(smooth_s * fps)});
  roll = {poses, cameras: rig.cameras, clocks};
  delete rig.cameras;
  return {frames: count, fps, sim_seconds: end, run: served.run || null, stem: served.stem || null,
          source: served.source || null, rig};
}
function rolloutFrame(i, {clock = false, look = 'studio'} = {}) {
  if (!roll) throw new Error('no rollout loaded');
  const k = Math.max(0, Math.min(roll.poses.length - 1, i));
  viewer.setCamera(roll.cameras[k]); viewer.setPoses(roll.poses[k]);
  paint({look, clock: clock ? roll.clocks[k] : null}); blit();
  return true;
}

// -- training curves -------------------------------------------------------------------------
function ticks(lo, hi, count) {
  const span = hi - lo || 1, step0 = span / Math.max(1, count), mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 5, 10].map(m => m * mag).find(s => s >= step0) || 10 * mag, first = Math.ceil(lo / step) * step, out = [];
  for (let v = first; v <= hi + 1e-9 * span; v += step) out.push(+v.toPrecision(12));
  return out;
}
function label(v) {
  const a = Math.abs(v);
  return a >= 1e4 ? (v / 1e3).toFixed(0) + 'k' : a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : a >= 1 ? v.toFixed(2) : v.toPrecision(2);
}
function rolling(points) {
  const w = Math.max(1, Math.round(points.length / 12)), result = [];
  let sum = 0;
  points.forEach((p, i) => { sum += p[1]; if (i >= w) sum -= points[i - w][1]; result.push([p[0], sum / Math.min(i + 1, w)]); });
  return result;
}
function panel(spec, box, progress, unit) {
  const [x, y, w, h] = box, pts = spec.points, pad = {l: 5.2 * unit, r: 1.6 * unit, t: 3.2 * unit, b: 2.6 * unit};
  ctx.fillStyle = PLOT.ink; ctx.font = `600 ${1.5 * unit}px ${PLOT.font}`; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  ctx.fillText(spec.label, x + pad.l, y + 1.8 * unit);
  if (!pts.length) return;
  const x0 = pts[0][0], x1 = Math.max(pts[pts.length - 1][0], x0 + 1), ys = pts.map(p => p[1]);
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (y1 - y0 < 1e-9) { y0 -= 1; y1 += 1; }
  const m = (y1 - y0) * .06; y0 -= m; y1 += m;
  const px = v => x + pad.l + (v - x0) / (x1 - x0) * (w - pad.l - pad.r), py = v => y + h - pad.b - (v - y0) / (y1 - y0) * (h - pad.t - pad.b);
  ctx.font = `${1.05 * unit}px ${PLOT.font}`; ctx.lineWidth = 1;
  ticks(y0, y1, 4).forEach(v => {
    ctx.strokeStyle = PLOT.rule; ctx.beginPath(); ctx.moveTo(px(x0), py(v)); ctx.lineTo(px(x1), py(v)); ctx.stroke();
    ctx.fillStyle = PLOT.ink2; ctx.textAlign = 'right'; ctx.textBaseline = 'middle'; ctx.fillText(label(v), px(x0) - .6 * unit, py(v));
  });
  ticks(x0, x1, 5).forEach(v => {
    ctx.fillStyle = PLOT.ink2; ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillText(label(v), px(v), y + h - pad.b + .6 * unit);
  });
  const reach = x0 + (x1 - x0) * Math.max(0, Math.min(1, progress)), shown = pts.filter(p => p[0] <= reach);
  if (!shown.length) return;
  ctx.save(); ctx.beginPath(); ctx.rect(px(x0) - 2, y, px(reach) - px(x0) + 4, h); ctx.clip();
  const line = (points, width, alpha) => {
    ctx.strokeStyle = PLOT.accent; ctx.globalAlpha = alpha; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.beginPath(); points.forEach((p, i) => i ? ctx.lineTo(px(p[0]), py(p[1])) : ctx.moveTo(px(p[0]), py(p[1]))); ctx.stroke(); ctx.globalAlpha = 1;
  };
  const mean = rolling(pts);
  line(shown, Math.max(1, .1 * unit), .28);
  line(mean.filter(p => p[0] <= reach), Math.max(2, .26 * unit), 1);
  ctx.restore();
  // The best, once the curve has reached it; the head of the trend with its value.
  if (spec.best && spec.best[0] <= reach) {
    const bx = px(spec.best[0]), by = py(spec.best[1]);
    ctx.save(); ctx.setLineDash([.5 * unit, .5 * unit]); ctx.strokeStyle = PLOT.ok; ctx.globalAlpha = .6; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(px(x0), by); ctx.lineTo(px(x1), by); ctx.stroke(); ctx.restore();
    ctx.fillStyle = PLOT.ok; ctx.beginPath(); ctx.arc(bx, by, .45 * unit, 0, 2 * Math.PI); ctx.fill();
    ctx.font = `${1.05 * unit}px ${PLOT.font}`; ctx.textAlign = bx > x + w * .7 ? 'right' : 'left'; ctx.textBaseline = 'bottom';
    ctx.fillText(`best ${label(spec.best[1])} @ ${spec.best[0]}`, bx + (ctx.textAlign === 'right' ? -.7 : .7) * unit, by - .5 * unit);
  }
  const head = mean.filter(p => p[0] <= reach).pop();
  if (head) {
    ctx.fillStyle = PLOT.ink; ctx.beginPath(); ctx.arc(px(head[0]), py(head[1]), .32 * unit, 0, 2 * Math.PI); ctx.fill();
  }
}
function plot({title = '', subtitle = '', panels = [], progress = 1, layout = 'row', alpha = 1} = {}) {
  const unit = Math.min(W, H * 16 / 9) / 64;
  ctx.globalAlpha = 1; ctx.fillStyle = PLOT.bg; ctx.fillRect(0, 0, W, H);
  ctx.globalAlpha = alpha;
  const margin = 3.2 * unit, top = 9.4 * unit;
  ctx.fillStyle = PLOT.ink; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  ctx.font = `600 ${2.6 * unit}px ${PLOT.font}`; ctx.fillText(title, margin, margin + 2.2 * unit);
  ctx.fillStyle = PLOT.ink2; ctx.font = `${1.3 * unit}px ${PLOT.font}`; ctx.fillText(subtitle, margin, margin + 4.2 * unit);
  const n = Math.max(1, panels.length), area = [margin, top, W - 2 * margin, H - top - margin], gap = 2.4 * unit;
  panels.forEach((spec, i) => {
    const box = layout === 'col'
      ? [area[0], area[1] + i * (area[3] + gap) / n, area[2], (area[3] + gap) / n - gap]
      : [area[0] + i * (area[2] + gap) / n, area[1], (area[2] + gap) / n - gap, area[3]];
    panel(spec, box, progress, unit);
  });
  ctx.globalAlpha = 1;
  return true;
}

function image(type = 'png', quality = .92) {
  return out.toDataURL(type === 'jpeg' ? 'image/jpeg' : 'image/png', quality).split(',')[1];
}

window.cadexHero = {available: viewer.available, size, load, fitCamera, shot, rollout, rolloutFrame, plot, image,
                    stats: () => viewer.stats(), viewer};
