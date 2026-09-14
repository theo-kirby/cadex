// Adapted from neural-whoop, copyright 2026 Theo, MIT.
// See REFERENCE-LICENSE.txt; modifications copyright 2026 Cadex Authors.
import * as THREE from "./three.module.js";
const FALLBACK_TILE = {
  tileA: "#1c1c1c", tileB: "#232323", line: "#3a3a3a", dot: "#444444",
  label: "rgba(150,150,150,0.22)",
};

// Human label for a grid pitch in metres ("1 METER" / "50 CM" / "10 CM"). Baked into the tile, so
// the grid states its own scale — which is the whole point of drawing the airframe at true size.
export function pitchLabel(pitch) {
  if (pitch >= 1) return pitch === 1 ? "1 METER" : `${+pitch.toFixed(2)} METERS`;
  return `${Math.round(pitch * 100)} CM`;
}

// The set of grid pitches we snap to. A hero shot frames ~0.4 m of world, an arena shot ~30 m, and
// the grid has to stay legible across both: pick the coarsest pitch that still puts a handful of
// lines across the frame (see `chooseGridPitch`).
const PITCH_LADDER = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10];

// Grid pitch (m) for a shot that spans `span` metres of world: the coarsest ladder step that still
// draws at least `want` divisions across the frame. This is what makes the room self-scaling —
// the same code gives a 82 mm product shot a 5 cm grid and a giant arena a 5 m grid, so "how big
// is the drone" reads the same way at every framing.
export function chooseGridPitch(span, want = 5) {
  const target = Math.max(1e-4, span) / Math.max(1, want);
  let best = PITCH_LADDER[0];
  for (const p of PITCH_LADDER) if (p <= target) best = p;
  return best;
}

// A "prototype map" greybox tile texture: a 2·pitch square block (checkerboard of two greys) with
// gridlines every `pitch` metres, optional finer `minor` lines inside them, intersection dots at
// the half-pitch, and "<pitch>" / "PROTOTYPE" labels baked along the lines. `palette`
// (tileA/tileB/line/dot/label, optional minorLine) themes it; `repeatX`/`repeatY` tile it to cover
// the surface (per-axis, though the only surface left is the square floor). All feature sizes are fractions
// of the block, so a 5 cm grid looks exactly like a 1 m grid, just smaller. Returns a
// THREE.CanvasTexture (RepeatWrapping, sRGB).
function greyboxTexture(palette = FALLBACK_TILE, repeatX = 1, repeatY = 1, labels = true,
                        { pitch = 1, minor = 0 } = {}) {
  // Sub-divided grids need the extra texel budget; a plain 2-line block does not. A hero shot is
  // close enough to the floor to magnify a block several times, so this is the difference between
  // a crisp mesh and mush.
  const S = minor > 0 ? 2048 : 512, M = S / 2;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = S;
  const ctx = canvas.getContext("2d");
  const { tileA, tileB, line, dot, label } = palette;

  // Checkerboard: tileA on the (0,0)/(M,M) diagonal, tileB on the off-diagonal.
  ctx.fillStyle = tileA; ctx.fillRect(0, 0, S, S);
  ctx.fillStyle = tileB; ctx.fillRect(M, 0, M, M); ctx.fillRect(0, M, M, M);

  const px = S / (2 * pitch);                 // px per metre in this block
  const drawLines = (step, width, style) => {
    ctx.strokeStyle = style; ctx.lineWidth = width;
    for (let p = 0; p <= S + 0.5; p += step) {
      ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, S); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(S, p); ctx.stroke();
    }
  };
  // Minor subdivisions first (thinner + fainter), then the pitch lines over the top. Two densities
  // is what reads as a measured surface rather than a checkerboard: the fine mesh gives the eye a
  // texture right under the airframe while the pitch lines still carry the number.
  if (minor > 0 && minor < pitch) {
    drawLines(minor * px, Math.max(1, S / 512), palette.minorLine || dot);
  }
  // Gridlines every `pitch` (0/M/S; edge lines straddle the seam and complete on the tile next
  // door, so the repeat is continuous).
  drawLines(M, (5 * S) / 512, line);
  // Half-pitch dots on the lines (mark x half, half x mark) — dropped when minor lines already
  // subdivide the block, where they'd just be noise on top of the mesh.
  if (!(minor > 0 && minor < pitch)) {
    ctx.fillStyle = dot;
    const marks = [0, M, S], halves = [M / 2, (3 * M) / 2], r = (5 * S) / 512;
    const dotAt = (x, y) => { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); };
    for (const a of marks) for (const b of halves) { dotAt(a, b); dotAt(b, a); }
  }

  // Labels along the lines (faint), repeated every block like the reference. Read correctly (not
  // mirrored) on the floor, which is built as a front-facing plane below. `labels: false` drops
  // them for a clean product shot — the grid still carries the scale.
  if (labels) {
    const k = S / 512;
    ctx.fillStyle = label;
    ctx.font = `bold ${34 * k}px system-ui, -apple-system, sans-serif`;
    ctx.textBaseline = "alphabetic";
    ctx.save(); ctx.translate(24 * k, M - 16 * k); ctx.fillText(pitchLabel(pitch), 0, 0); ctx.restore();
    ctx.save(); ctx.translate(M - 16 * k, S - 24 * k); ctx.rotate(-Math.PI / 2);
    ctx.fillText("PROTOTYPE", 0, 0); ctx.restore();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.repeat.set(repeatX, repeatY);
  return tex;
}

// The stage floor (sim frame): a single `size`×`size` greybox plane resting on z=floorZ, tiled into
// "prototype map" squares at `pitch` metres (see greyboxTexture). Returns a THREE.Group (added
// under `world`) holding one FRONT-facing (DoubleSide) plane a hair above z=floorZ — the surface
// people read, so its baked "PROTOTYPE" / pitch text reads correctly rather than mirrored. Dispose
// the group (geometry + texture) to tear it down.
//
// There are no walls and no ceiling, anywhere, in any view. This used to be a bounded room with a
// BackSide box over it and a `walls: false` escape hatch for the concept renders; the box is gone
// because a corner or a ceiling seam sweeping through a moving frame was the single biggest thing
// that made a travelling shot read as wrong, and keeping two backdrops meant the Studio and the
// video could drift apart. The floor alone, run out past the scene fog (environment.js::setStage
// sizes it from the fade), is a cyclorama: the ground and its contact shadow are still there, so
// the drone is visibly IN a place, and nothing bounds the frame.
export function buildStageFloor(world, { size = 10, floorZ = 0, palette = FALLBACK_TILE,
                                         labels = true, pitch = 1, minor = 0 } = {}) {
  const group = new THREE.Group();
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.MeshStandardMaterial({
      map: greyboxTexture(palette, 1, 1, labels, { pitch, minor }),
      roughness: 1, metalness: 0, side: THREE.FrontSide,
    }));
  floor.receiveShadow = true;
  floor.userData.pitch = pitch;
  group.add(floor);
  resizeStageFloor(group, { size, floorZ });

  world.add(group);
  return group;
}

// Resize a floor built by buildStageFloor without repainting its texture. The grid is anchored
// to the world origin, not to the plane's corner: a block corner sits on x = y = 0 and every
// `pitch` line sits on a whole multiple of `pitch` metres, whatever the floor's size. The viewer
// grows the floor with the fog as the camera pulls back, so a grid laid from the corner slid
// under the model on every zoom step and its "1 METER" lines stopped being where a metre is.
export function resizeStageFloor(group, { size, floorZ }) {
  const floor = group.children[0], pitch = floor.userData.pitch, block = 2 * pitch;
  floor.scale.set(size, size, 1);
  floor.position.set(0, 0, floorZ);
  // uv' = uv·repeat + offset, and uv = (x + size/2) / size across the plane, so this offset puts
  // tile coordinate x / block at world x.
  const repeat = size / block, offset = -(size / 2) / block;
  const map = floor.material.map;
  map.repeat.set(repeat, repeat);
  map.offset.set(offset - Math.floor(offset), offset - Math.floor(offset));
  floor.userData.size = size;
  return group;
}

