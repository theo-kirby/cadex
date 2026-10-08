// Adapted from neural-whoop, copyright 2026 Theo, MIT.
// See REFERENCE-LICENSE.txt; modifications copyright 2026 Cadex Authors.
import * as THREE from "./three.module.js";
const FALLBACK_TILE = {
  tileA: "#1c1c1c", tileB: "#232323", line: "#3a3a3a",
  label: "rgba(150,150,150,0.22)",
};

// The mat's grid is true size and nothing else (ADR-600): one square every metre, at every zoom
// and every framing, in the viewport, its capture and the engine's studio renders alike. It used
// to step a finer mesh (5, 10, 20 cm) and half-pitch dots in and out with the framing, which read
// as layers of grid sliding over each other while zooming; a metre is now always a metre.
// `CadexStudio` draws its floor at the same pitch with the same line fraction
// (cli/tests/test_scene_palette.py holds the two together).
export const GRID_PITCH = 1;
// A major line is this fraction of the pitch wide (5 texels of a 256-texel pitch).
export const LINE_FRACTION = 5 / 256;
const LABEL = "1 METER";

// A "prototype map" greybox tile texture: a 2·pitch square block (checkerboard of two greys) with
// a gridline every metre and "1 METER" / "PROTOTYPE" labels baked along the lines. `palette`
// (tileA/tileB/line/label) themes it; `repeatX`/`repeatY` tile it to cover the surface. Returns
// a THREE.CanvasTexture (RepeatWrapping, sRGB). The texture is 2048 texels a block, so the line
// and the label stay crisp under a hero shot that magnifies one tile many times.
function greyboxTexture(palette = FALLBACK_TILE, repeatX = 1, repeatY = 1, labels = true) {
  const S = 2048, M = S / 2;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = S;
  const ctx = canvas.getContext("2d");
  const { tileA, tileB, line, label } = palette;

  // Checkerboard: tileA on the (0,0)/(M,M) diagonal, tileB on the off-diagonal.
  ctx.fillStyle = tileA; ctx.fillRect(0, 0, S, S);
  ctx.fillStyle = tileB; ctx.fillRect(M, 0, M, M); ctx.fillRect(0, M, M, M);

  // Gridlines every metre (0/M/S; edge lines straddle the seam and complete on the tile next
  // door, so the repeat is continuous).
  ctx.strokeStyle = line; ctx.lineWidth = LINE_FRACTION * M;
  for (let p = 0; p <= S + 0.5; p += M) {
    ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, S); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(S, p); ctx.stroke();
  }

  // Labels along the lines (faint), repeated every block like the reference. Read correctly (not
  // mirrored) on the floor, which is built as a front-facing plane below. `labels: false` drops
  // them for a clean product shot — the grid still carries the scale.
  if (labels) {
    const k = S / 512;
    ctx.fillStyle = label;
    ctx.font = `bold ${34 * k}px system-ui, -apple-system, sans-serif`;
    ctx.textBaseline = "alphabetic";
    ctx.save(); ctx.translate(24 * k, M - 16 * k); ctx.fillText(LABEL, 0, 0); ctx.restore();
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
// "prototype map" squares a metre on a side (see greyboxTexture). Returns a THREE.Group (added
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
//
// The mat is pushed back in depth (polygon offset) rather than lowered under the design: a part
// standing exactly on z=floorZ draws over it at any zoom, with no z-fighting and no visible gap.
// It takes no environment reflection — it is the room, not a thing in it.
export function buildStageFloor(world, { size = 10, floorZ = 0, palette = FALLBACK_TILE,
                                         labels = true } = {}) {
  const group = new THREE.Group();
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.MeshStandardMaterial({
      map: greyboxTexture(palette, 1, 1, labels),
      roughness: 1, metalness: 0, side: THREE.FrontSide, envMapIntensity: 0,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 4,
    }));
  floor.receiveShadow = true;
  floor.userData.pitch = GRID_PITCH;
  group.add(floor);
  resizeStageFloor(group, { size, floorZ });

  world.add(group);
  return group;
}

// Resize a floor built by buildStageFloor without repainting its texture. The grid is anchored
// to the world origin, not to the plane's corner: a block corner sits on x = y = 0 and every
// line sits on a whole metre, whatever the floor's size. The viewer
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

