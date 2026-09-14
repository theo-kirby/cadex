// Adapted from neural-whoop, copyright 2026 Theo, MIT.
// See REFERENCE-LICENSE.txt; modifications copyright 2026 Cadex Authors.
// Greybox environment manager — the single owner of a scene's stage floor plus its scene chrome
// (background, fog, light intensities). Both views in the repo build one over their `view`: the
// review dashboard's viewport and the headless video capturer. There is exactly ONE environment —
// a fogged cyclorama — and ONE palette, the reference's dark one (ADR-331): no walled variant and
// no light theme, so a clip and the dashboard cannot show different places.
//
// `createEnvironment(view, { labels })` -> { setStage, setSize, setFog, dispose }.
// `labels: false` builds the floor without the baked pitch / "PROTOTYPE" text (the grid still
// carries the scale) — a clean backdrop for a product shot.
//   - the palette is applied once at construction: scene.background / fog / ground tint / light
//     intensities from PALETTE.scene, the floor texture from PALETTE.tile;
//   - setStage is THE entry point: give it the shot's camera distance and it derives fog, then the
//     floor size from the fog, then the grid subdivision from the framing — and returns what it
//     derived, so a caller can report the numbers rather than recompute them;
//   - setSize / setFog are the primitives setStage drives; call them directly only to override one
//     axis of the derivation.
//   - dispose tears the whole thing down (floor geometry + texture + the extra fill light).

import * as THREE from "./three.module.js";
import { buildStageFloor, chooseGridPitch, resizeStageFloor } from "./floor.js";
export const KEY_DIR = [0.22, 1.0, 0.15];

// The derivation constants behind `setStage`. Every one of these used to be a hard-coded number
// inside web/capture/capture.js, reachable only via `--preset hero`; naming them here is what makes
// "the video look" and "the Studio look" the same object rather than two that resemble each other.
//
//   fog*      — the fade, from the camera's standoff: near at 1.5x the subject distance (so the
//               subject itself is never fogged), far at 14x (so mid-ground reads as depth rather
//               than haze). The Min floors keep an extreme close-up from fogging its own floor out.
//   footprintFogMul — the floor runs to 4x the fog's far distance, which is the invariant that
//               matters: the plane's own EDGE is always well past the point it has faded to
//               background, so no shot can ever catch the stage ending.
//   grid*     — the metre pitch is kept honest (that label is the scale reference) and a finer mesh
//               is chosen from the shot's own framing, so an 82 mm airframe sits on something it
//               can be read against instead of on 1/12 of a bare metre square. A wide arena shot
//               resolves the subdivision to "coarser than the tile", i.e. none.
export const STAGE_LOOK = {
  fogNearMul: 1.5, fogNearMin: 1.0, fogFarMul: 14, fogFarMin: 6.0,
  footprintFogMul: 4, gridPitch: 1, gridSpanMul: 2.5, gridWant: 5,
  keyDir: KEY_DIR, exposure: 0.95,
};

// A vertical sky gradient as an equirectangular background. It is unconditional now: with the
// walled room gone, EVERY scene has a horizon, and a flat fill above it reads as "the render ran
// out" rather than as space. The gradient's HORIZON stop is exactly the flat background colour, so
// the fogged floor still fades into it seamlessly and only the empty upper half gains shape.
function skyGradient(bg, top) {
  const canvas = document.createElement("canvas");
  canvas.width = 8; canvas.height = 256;
  const ctx = canvas.getContext("2d");
  // flipY (the default) puts canvas y=0 at v=1, i.e. straight up; the midpoint is the horizon.
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, top);
  g.addColorStop(0.5, bg);
  g.addColorStop(1, bg);
  ctx.fillStyle = g; ctx.fillRect(0, 0, 8, 256);
  const tex = new THREE.CanvasTexture(canvas);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// The one environment palette (tile texture + scene chrome): the reference's near-black void, whose
// scene background is also the review page's `--bg` (docs/REVIEW-DESIGN.md §4), so the viewport is
// a window onto the place the videos are captured in rather than a lighter card inside the chrome.
// The light "prototype map" palette that used to sit beside it was removed under ADR-331, not kept
// behind a switch.
//
// The `fogNear`/`fogFar` here are only the FIRST-PAINT fallback: they hold from createEnvironment
// until the first `setStage`, which derives the real fade from the shot's own standoff. They are
// arena-sized on purpose, so a scene that has not been staged yet still shows something.
export const PALETTE = {
  tile: { tileA: "#1c1c1c", tileB: "#232323", line: "#3a3a3a", dot: "#444444",
          minorLine: "#303030", label: "rgba(150,150,150,0.22)" },
  scene: {
    bg: 0x141414, sky: "#070707", fogNear: 40, fogFar: 130,
    hemiIntensity: 1.6, hemiGround: 0x2a2a2a, sunIntensity: 2.7, fillIntensity: 1.0,
    roomFillIntensity: 1.2, roomFillGround: 0x9a9a9a,
  },
};

export function createEnvironment(view, { labels = true } = {}) {
  let size = { footprint: 10, floorZ: 0, pitch: 1, minor: 0 };
  let fogOverride = null;                 // {near, far} set by setFog; survives restaging
  let room = null;

  // An extra hemisphere fill so the greybox floor reads even; its intensity and ground colour come
  // from the palette like the view's own lights.
  const roomFill = new THREE.HemisphereLight(0xffffff, PALETTE.scene.roomFillGround, PALETTE.scene.roomFillIntensity);
  view.scene.add(roomFill);

  function disposeObj(root) {
    if (!root) return;
    root.traverse((o) => {
      o.geometry?.dispose?.();
      const m = o.material;
      if (Array.isArray(m)) m.forEach((mm) => { mm?.map?.dispose?.(); mm?.dispose?.(); });
      else if (m) { m.map?.dispose?.(); m.dispose?.(); }
    });
    view.world.remove(root);
  }

  function rebuildRoom() {
    disposeObj(room);
    room = buildStageFloor(view.world, {
      size: size.footprint, floorZ: size.floorZ,
      pitch: size.pitch, minor: size.minor,
      palette: PALETTE.tile, labels,
    });
  }

  function applyChrome() {
    const s = PALETTE.scene;
    view.scene.background?.dispose?.();
    view.scene.background = skyGradient(`#${s.bg.toString(16).padStart(6, "0")}`, s.sky);
    view.scene.fog = new THREE.Fog(
      s.bg, fogOverride ? fogOverride.near : s.fogNear, fogOverride ? fogOverride.far : s.fogFar);
    if (view.ground) view.ground.material.color.setHex(s.bg);
    const L = view.lights || {};
    if (L.hemi) { L.hemi.intensity = s.hemiIntensity; L.hemi.groundColor.setHex(s.hemiGround); }
    if (L.sun) L.sun.intensity = s.sunIntensity;
    if (L.fill) L.fill.intensity = s.fillIntensity;
    roomFill.intensity = s.roomFillIntensity;
    roomFill.groundColor.setHex(s.roomFillGround);
  }

  function setSize(sz = {}) {
    const next = {
      footprint: sz.footprint ?? size.footprint,
      floorZ: sz.floorZ ?? size.floorZ,
      pitch: sz.pitch ?? size.pitch,
      minor: sz.minor ?? size.minor,
    };
    const repaint = !room || next.pitch !== size.pitch || next.minor !== size.minor;
    size = next;
    // A zoom changes the floor's size on nearly every frame; only a change of grid repaints the
    // texture, and the grid stays anchored to the world origin either way (floor.js).
    if (repaint) rebuildRoom();
    else resizeStageFloor(room, { size: size.footprint, floorZ: size.floorZ });
  }

  // Override the palette's fog distances (metres). The palette defaults are sized for a whole arena;
  // a close product shot needs the ground to fade within a couple of metres so it reads as a
  // cyclorama rather than a floor that just stops. `null` restores the palette's own values.
  function setFog(f) {
    fogOverride = f ? { near: f.near, far: f.far } : null;
    applyChrome();
  }

  // Set up the whole stage for a shot at `camDist` metres from its subject, and RETURN what was
  // derived. One call, one chain of consequences: fog comes from the standoff, the floor's size
  // comes from the fog, and the grid's subdivision comes from the framing.
  //
  // This is the fix for a specific bug, not just tidying. Sizing the floor to the COURSE (what the
  // Studio used to do) and leaving fog at the palette's fixed [40, 150] worked only because walls
  // bounded the view; with the walls gone, a 10 m floor inside 40 m of clear air shows its own
  // edge as a hard horizon line. Deriving the size from the fade makes "you can never see the
  // stage end" true by construction, at any scale, in the dashboard and in a video alike.
  //
  //   camDist   metres from the camera to what it is looking at — the ONE number a caller must
  //             supply, because everything else is a consequence of it.
  //   camReach  how far the camera itself stands from the origin; the floor is grown to cover it.
  //             Defaults to the live camera's own horizontal distance.
  //   frameSpan metres of world the frame spans vertically, for the grid subdivision. Defaults to
  //             the live camera's FOV applied to camDist.
  //   fog / gridPitch / gridMinor / roomSize   explicit overrides for any one derived value.
  function setStage({ camDist, camReach = null, frameSpan = null, fog = null,
                      gridPitch = null, gridMinor = null, roomSize = null, floorZ = 0 } = {}) {
    const d = Math.max(1e-3, Number(camDist) || 0);
    const L = STAGE_LOOK;

    const span = frameSpan ?? (2 * Math.tan(THREE.MathUtils.degToRad(view.camera.fov) / 2) * d);
    const reach = camReach ?? 2 * (Math.hypot(view.camera.position.x, view.camera.position.z) + 0.6);

    let [fogNear, fogFar] = fog
      ?? [Math.max(L.fogNearMin, L.fogNearMul * d), Math.max(L.fogFarMin, L.fogFarMul * d)];
    // The fade must COMPLETE inside the frustum, or the far plane clips a floor that is still
    // partly visible and you get the hard horizon back by another route. Only bites on the giant
    // arena presets (a 60 m course wants a 806 m fade against the camera's 800 m far plane).
    if (!fog) fogFar = Math.min(fogFar, 0.9 * view.camera.far);
    const footprint = roomSize ?? Math.max(L.footprintFogMul * fogFar, reach);

    const pitch = gridPitch ?? L.gridPitch;
    const autoMinor = chooseGridPitch(span * L.gridSpanMul, L.gridWant);
    const minor = gridMinor ?? (autoMinor <= pitch / 2 ? autoMinor : 0);

    setFog({ near: fogNear, far: fogFar });
    setSize({ footprint, floorZ, pitch, minor });
    return { roomSize: footprint, fog: { near: fogNear, far: fogFar }, pitch, minor, frameSpan: span };
  }

  function dispose() {
    disposeObj(room);
    room = null;
    view.scene.remove(roomFill);
  }

  applyChrome();
  rebuildRoom();
  // Stage once at construction, from wherever the camera currently is. Without this the FIRST
  // paint — a viewport before its model has loaded — is a 10 m slab floating inside the palette's
  // arena-sized fog, showing its own edge as a hard horizon: exactly what the walls used to hide.
  // Callers restage as soon as they know what they are looking at (the viewer on every fit and
  // orbit, the capturer once per clip); this only has to be right enough that the floor outruns
  // its own fade.
  setStage({ camDist: Math.max(1, view.camera.position.length()) });
  return { setStage, setSize, setFog, dispose };
}
