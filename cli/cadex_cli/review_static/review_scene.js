// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
// Common inspection/capture scene. Public poses, bounds and cameras are mm,
// Z-up, xyzw. One uniform conversion to metres; no component enlargement.
import * as THREE from './three.module.js';
import {createEnvironment, PALETTE as STAGE} from './environment.js';
import {prototypeMaterial, GRID_PITCH} from './floor.js';
import {parseStl} from './stl.js';
import {LOOKS, MATCAPS, LIGHTING, OCCLUSION, createLooks, createOcclusion, createOutline, addDetail, detailSwitch} from './shading.js';
export const STYLE = 'cadex-prototype-dark-v1';
const PALETTE = [0x5b9dcd, 0xde8f47, 0x6ab270, 0xc468b4, 0xdcc85a, 0x7878c8, 0xc86e6e, 0x6ebebe];
const FOV = 55;
// The timer overlay (DASHBOARD.md §10): the reference's caption pill, bottom left, drawn
// INSIDE the WebGL frame so a capture's png() and the viewport bake the same pixels. Panel and
// line are the reference's caption chip; the ink is the page's `--ink`; the type is the page's
// `--font` at 3.2 % of the frame height (16 px in a 512 px video), never below `--fs-0`.
const CLOCK = {panel:'rgba(20,22,26,0.72)', line:'rgba(244,245,247,0.22)', ink:'#ededed',
  font:'system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif', size:.032, minSize:12, margin:.042};
// The follow rig's declared defaults, the reference's own: the subject's standing height fills
// `fraction` of the frame height; it rests `subject_y` below centre (headroom); the camera anchor
// is a Hann-smoothed track with half-window `smooth_frames`; the subject may lead the anchor by at
// most `max_drift` of the half-frame before the soft limiter pulls the anchor after it.
export const FOLLOW = {fraction:.22, subject_y:-.06, max_drift:.26, smooth_frames:4};
// Collision proxies (DASHBOARD.md §11): the simulation's contact shapes, drawn as outlines in
// the page's `--warn` through the solids, and only while the labelled toggle is on. Never in a
// recording, never by default: what the viewer shows is the tessellated solid.
const PROXY = {color:0xffe08a, opacity:.9};
// A training body's primitives over the CAD it carries (ADR-838): a colour no part is drawn in.
const PRIMITIVE = {color:0x35c4ff, opacity:.8};
// Section and explode (DASHBOARD.md §24). A section clips the solids at the plane and offset of
// the `cadex section` cut it shows, keeping the side below the offset; the leader lines are the
// engine's exploded-view segments, in the page's `--muted`.
const SECTION_NORMALS = {XY:[0,0,1], XZ:[0,1,0], YZ:[1,0,0]};
const LEADER = {color:0x9aa3ad, opacity:.85};
// The trail (ADR-770): its opacity, a ribbon's fainter; its colours are Settings' (trailcolours.js).
const TRAIL = {opacity:.8, ribbon:.25};
// Terrain (ADR-734, ADR-743): the course a free base stands on, drawn as one ground in the mat's
// own prototype material. `pitch_mm` is its finest sample spacing and `samples` the most it takes
// over its extent before the spacing grows; a step's face is `wall_mm` either side of its edge,
// for up to `breaks` distinct corner lines a side; the surface runs `margin_mm` past a box course's extent and
// eases a heightfield down to the mat over `blend_mm`; the frame's reach along it.
const TERRAIN = {pitch_mm:25, samples:120000, wall_mm:.5, breaks:512, margin_mm:500, blend_mm:1500, reach_mm:10000, far_mm:2500, behind_mm:300, ahead_mm:1500};
// Render styles (ADR-534, ADR-602). 'shaded' is the lit stage every capture uses and the
// viewport's default; 'wireframe' (called 'hairline' until ADR-602) is a diagram: silhouettes and
// creases in ink on flat paper, and no floor, shadow or fog, with an optional soft layer of the
// tessellation's own edges under them. The page passes its own paper and ink so the diagram
// follows the theme.
const STYLES = ['shaded','wireframe'];
const WIREFRAME = {paper:'#fbfbf9', ink:'#1c1c1c'};
// The mesh lines (ADR-602): every edge where two facets turn by more than `angle` degrees, so a
// curved face shows its facets and a flat one stays clean, drawn at `strength` of the ink over
// the paper, hidden where a solid is in front of them.
export const MESH_LINES = {angle:2, strength:.12, max:1};
// Smooth shading (ADR-601): a vertex normal averages the facets around it that turn by less than
// the engine's CREASE_DEGREES (CadexStudio.py), so a fillet or a bore reads smooth and an edge
// that turns further stays crisp.
export const CREASE_DEGREES = 40;
// Physical finishes (ADR-601), keyed by the manifest's `finish` (and, for hardware, its catalog
// family). The role colour stays the base colour; a finish only says how the surface takes light.
// `colour` is the fallback when a part carries none; `env` is how much of the studio it reflects
// (a metal is mostly reflection; a plastic mostly its own colour under the lights).
export const FINISHES = {
  printed:  {roughness:.46, metalness:0, clearcoat:0, clearcoatRoughness:.5, env:.9},
  purchased:{roughness:.45, metalness:0, clearcoat:.1, clearcoatRoughness:.35, env:.9},
  board:    {roughness:.45, metalness:0, clearcoat:.3, clearcoatRoughness:.3, env:.9, colour:'#1f6b3c'},
  black_oxide:{roughness:.4, metalness:.85, env:1, colour:'#2a2b2e'},
  steel:    {roughness:.28, metalness:.92, env:1, colour:'#c4c8ce'},
  brass:    {roughness:.32, metalness:.92, env:1, colour:'#c9a24a'},
};
// Hardware by catalog family: fasteners are black oxide, bearings and the like bright steel,
// heat-set inserts brass.
const HARDWARE = {bolt:'black_oxide', screw:'black_oxide', nut:'black_oxide', standoff:'black_oxide',
  washer:'steel', bearing:'steel', bushing:'steel', shaft:'steel', dowel:'steel', heat_insert:'brass', insert:'brass'};
// A board's own geometry, when the manifest carries it: the chip and the pads, coloured per facet.
const BOARD = {chip:'#18191b', pad:'#c9ccd0', ring:.6, tolerance:.05};
// The reflections' default strength (environment-map intensity); the page may scale it.
export const REFLECTIONS = {strength:1, max:2};

// Crease-angle vertex normals for a triangle soup (`mm`: 9 floats a triangle, as parsed from STL).
// Corners at bit-identical positions are one vertex; a corner's normal is the mean of the unit
// normals of the facets at its vertex that lie within `degrees` of its own facet's, each weighted
// by its corner angle there -- so how a face was split into triangles does not tilt the normal
// (an area weight, as the engine's CPU renderer uses, would lean towards the side cut in two).
export function creaseNormals(mm, degrees=CREASE_DEGREES) {
  const corners=(mm.length/3)|0, faces=(corners/3)|0, limit=Math.cos(degrees*Math.PI/180);
  const face=new Float32Array(faces*3), angle=new Float32Array(corners), out=new Float32Array(corners*3);
  for (let f=0;f<faces;f++) {
    const o=f*9, ax=mm[o+3]-mm[o], ay=mm[o+4]-mm[o+1], az=mm[o+5]-mm[o+2], bx=mm[o+6]-mm[o], by=mm[o+7]-mm[o+1], bz=mm[o+8]-mm[o+2];
    face[f*3]=ay*bz-az*by; face[f*3+1]=az*bx-ax*bz; face[f*3+2]=ax*by-ay*bx;
    // Each corner's interior angle, the weight its facet's normal carries at that vertex.
    for (let k=0;k<3;k++) {
      const p=o+3*k, q=o+3*((k+1)%3), r=o+3*((k+2)%3);
      const ux=mm[q]-mm[p], uy=mm[q+1]-mm[p+1], uz=mm[q+2]-mm[p+2], vx=mm[r]-mm[p], vy=mm[r+1]-mm[p+1], vz=mm[r+2]-mm[p+2];
      const len=Math.hypot(ux,uy,uz)*Math.hypot(vx,vy,vz);
      angle[f*3+k]=len?Math.acos(Math.max(-1,Math.min(1,(ux*vx+uy*vy+uz*vz)/len))):0;
    }
  }
  // Weld: an open-addressed table over the coordinates' float bits (+0 for -0).
  const bits=new Uint32Array(new Float32Array(mm.length).map((v,i)=>mm[i]+0).buffer);
  let size=1; while (size<corners*2) size<<=1;
  const table=new Int32Array(size).fill(-1), vertex=new Int32Array(corners); let unique=0;
  const first=new Int32Array(corners);
  for (let c=0;c<corners;c++) {
    const x=bits[c*3], y=bits[c*3+1], z=bits[c*3+2];
    let h=(Math.imul(x,73856093)^Math.imul(y,19349663)^Math.imul(z,83492791))&(size-1);
    for (;;) {
      const s=table[h];
      if (s<0) {table[h]=c; first[unique]=c; vertex[c]=unique++; break;}
      if (bits[s*3]===x&&bits[s*3+1]===y&&bits[s*3+2]===z) {vertex[c]=vertex[s]; break;}
      h=(h+1)&(size-1);
    }
  }
  // The corners at each vertex, as one flat list.
  const start=new Int32Array(unique+1);
  for (let c=0;c<corners;c++) start[vertex[c]+1]++;
  for (let v=0;v<unique;v++) start[v+1]+=start[v];
  const fill=start.slice(0,unique), list=new Int32Array(corners);
  for (let c=0;c<corners;c++) list[fill[vertex[c]]++]=c;
  for (let c=0;c<corners;c++) {
    const f=(c/3)|0, nx=face[f*3], ny=face[f*3+1], nz=face[f*3+2], nl=Math.hypot(nx,ny,nz)||1;
    let sx=0, sy=0, sz=0;
    for (let k=start[vertex[c]], e=start[vertex[c]+1];k<e;k++) {
      const g=(list[k]/3)|0, gx=face[g*3], gy=face[g*3+1], gz=face[g*3+2], gl=Math.hypot(gx,gy,gz);
      if (!gl || (nx*gx+ny*gy+nz*gz)/(nl*gl)<limit) continue;
      const a=angle[list[k]]/gl;
      sx+=gx*a; sy+=gy*a; sz+=gz*a;
    }
    const sl=Math.hypot(sx,sy,sz);
    if (sl>0) {out[c*3]=sx/sl; out[c*3+1]=sy/sl; out[c*3+2]=sz/sl;}
    else {out[c*3]=nx/nl; out[c*3+1]=ny/nl; out[c*3+2]=nz/nl;}
  }
  return out;
}

// The finish a part is drawn with: the manifest's `finish`, its hardware family's metal, or --
// before the manifest carried a finish -- printed unless the supplier says purchased.
export function finishOf(entry) {
  const finish=entry.finish||(entry.supplier==='purchased'?'purchased':'printed');
  if (finish==='hardware') {
    const family=String(entry.catalog?.family||'').toLowerCase();
    return HARDWARE[family]||(/insert/.test(family)?'brass':/bear|wash|bush|shaft|dowel|pin/.test(family)?'steel':'black_oxide');
  }
  return FINISHES[finish]?finish:'printed';
}

// Per-facet colours for a board from its own geometry (`board`, mm, the mesh's own frame): a
// facet whose corners all lie in the chip's box is the chip, one whose corners all lie within a
// pad's radius plus a ring (across the board's face) is tin, the rest the solder mask. A facet
// is coloured whole, so a long facet from a pad's rim to the board's edge never smears. Returns
// {colours (linear RGB per corner), chip, pad} facet counts.
export function boardColours(mm, board, base) {
  const corners=(mm.length/3)|0, colours=new Float32Array(corners*3);
  const mask=new THREE.Color(base), chipC=new THREE.Color(BOARD.chip), padC=new THREE.Color(BOARD.pad);
  const chip=board&&board.chip&&Array.isArray(board.chip.origin)&&Array.isArray(board.chip.size)?board.chip:null;
  const pads=(board&&Array.isArray(board.pads)?board.pads:[]).filter(p=>Array.isArray(p.origin)&&p.origin.length===3&&p.dia_mm>0);
  // The board's face normal is its thinnest axis.
  const lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity];
  for (let c=0;c<corners;c++) for (let j=0;j<3;j++) {const v=mm[c*3+j]; if(v<lo[j])lo[j]=v; if(v>hi[j])hi[j]=v;}
  const ext=hi.map((v,j)=>v-lo[j]), up=ext.indexOf(Math.min(...ext)), [u,w]=[0,1,2].filter(j=>j!==up);
  const t=BOARD.tolerance;
  const inChip=c=>chip&&[0,1,2].every(j=>{const a=chip.origin[j], b=a+chip.size[j], v=mm[c*3+j]; return v>=Math.min(a,b)-t&&v<=Math.max(a,b)+t;});
  const onPad=c=>pads.some(p=>Math.hypot(mm[c*3+u]-p.origin[u],mm[c*3+w]-p.origin[w])<=p.dia_mm/2+BOARD.ring);
  let chips=0, padFacets=0;
  for (let f=0;f<corners/3;f++) {
    const c=f*3; let col=mask;
    if (inChip(c)&&inChip(c+1)&&inChip(c+2)) {col=chipC; chips++;}
    else if (onPad(c)&&onPad(c+1)&&onPad(c+2)) {col=padC; padFacets++;}
    for (let k=0;k<3;k++) {colours[(c+k)*3]=col.r; colours[(c+k)*3+1]=col.g; colours[(c+k)*3+2]=col.b;}
  }
  return {colours, chip:chips, pad:padFacets};
}

// The rooms the solids reflect, and are lit by, are shading.js's lighting setups (ADR-676); the
// first was ADR-601's procedural studio, which is Studio's room still.

export function create(canvas, {labels=true}={}) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true}); }
  catch (_) { return {available:false, clear(){}, fit(){}, load(){return Promise.reject(new Error('WebGL unavailable'));}, stats(){return {available:false, components:0, triangles:0, showing:'nothing drawn', proxies:{shown:false,drawn:0,listed:0}};}, setProxies(){}, showProxies(){return false;}, setSection(){return null;}, setLines(){return 0;}, showLines(){return false;}, setPoses(){}, setTrail(){return 0;}, setTrailStyle(){return 'off';}, setTrailColours(){return null;}, showTrail(){return null;}, footfalls(){return [];}, centreAt(){return null;}, followTo(){return null;}, setGhost(){return 0;}, loadGhost(){return Promise.resolve(0);}, toScreen(){return null;}, setOnDraw(){}, setStyle(){return 'shaded';}, style(){return 'shaded';}, setMeshLines(){return {shown:false,strength:0};}, setReflections(){return 0;}, setLook(){return 'studio';}, setFov(){return 55;}, setOcclusion(){return false;}, setDetail(){return false;}, setHidden(){return [];}, setHeat(){return false;}, select(){return [];}, highlight(){return null;}, parts(){return [];}, fitTo(){return false;}, screenBox(){return null;}, draw(){}}; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  // Soft shadows (ADR-676): a variance shadow map, blurred, so a shadow's edge widens with its
  // distance from what casts it, as under a real softbox, instead of the old hard cut-out.
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const STAGE_EXPOSURE = 0.95;
  renderer.toneMappingExposure = STAGE_EXPOSURE;
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene(), world = new THREE.Group(), model = new THREE.Group();
  world.rotation.x = -Math.PI/2; scene.add(world); world.add(model);
  const camera = new THREE.PerspectiveCamera(FOV, 1, .0001, 800);
  // Key, hemisphere and opposite fill; the environment sets their intensities and ground tints
  // from its one dark palette (ADR-331) when it is built over them.
  const hemi = new THREE.HemisphereLight(0xffffff, 0x2a2a2a, 1.6);
  const sun = new THREE.DirectionalLight(0xffffff, 2.7);
  sun.castShadow = true; sun.shadow.mapSize.set(2048,2048); sun.shadow.radius = 10; sun.shadow.blurSamples = 16;
  const fill = new THREE.DirectionalLight(0xdfe6ff,1.0); fill.position.set(-12,6,-9);
  scene.add(hemi, sun, sun.target, fill);
  // `labels: false` is the product shot's clean mat (the hero page, ADR-677): the grid without its text.
  const environment = createEnvironment({scene,world,camera,renderer,lights:{hemi,sun,fill}}, {labels});
  // The look (ADR-676): a lighting setup or a matcap, occlusion and surface detail.
  const looks=createLooks(renderer), occlusion=createOcclusion(renderer), outline=createOutline(renderer);
  let look='studio', occluded=true, detailed=true, keyDir=LIGHTING.studio.key.dir;
  let envMap=looks.environment(look);
  let reflections=REFLECTIONS.strength;
  // Which parts the page hides and which it has selected, by name; both outlive a reload of the model.
  const hiddenNames=new Set(); let selectedNames=[];
  let bounds=null, triangleCount=0, staged='', stage=null;
  let c={yaw:.8,pitch:.5,distance:100,target:[0,0,0]}, floorZ=0;
  const meshes = new Map();
  // The proxies: outline children of the solid they belong to, so setPoses moves both.
  const proxyLines=[]; let proxyGeoms=[], proxiesShown=false, proxiesDrawn=0;
  function proxyGeometry(g) {
    const s=(g.size_mm||[]).map(v=>v*.001);
    switch (g.type) {
      case 'box': return new THREE.BoxGeometry(2*s[0],2*s[1],2*s[2]);
      case 'sphere': return new THREE.SphereGeometry(s[0],16,12);
      case 'capsule': {const geo=new THREE.CapsuleGeometry(s[0],2*s[1],4,16); geo.rotateX(Math.PI/2); return geo;}
      case 'cylinder': {const geo=new THREE.CylinderGeometry(s[0],s[0],2*s[1],24,1); geo.rotateX(Math.PI/2); return geo;}
      case 'mesh': {const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(g.vertices_mm.map(v=>v*.001),3)); geo.setIndex(g.faces); return geo;}
      default: return null;
    }
  }
  function disposeProxies() {
    proxyLines.forEach(l=>{l.parent&&l.parent.remove(l);l.geometry.dispose();l.material.dispose();});
    proxyLines.length=0; proxiesDrawn=0;
  }
  function buildProxies() {
    disposeProxies();
    proxyGeoms.forEach(g=> {
      const owner=meshes.get(g.component); if (!owner||!g.drawn||!g.pos_mm||!g.rotation_xyzw) return;
      const geo=proxyGeometry(g); if (!geo) return;
      const line=new THREE.LineSegments(new THREE.EdgesGeometry(geo,1),new THREE.LineBasicMaterial({color:PROXY.color,transparent:true,opacity:PROXY.opacity,depthTest:false,toneMapped:false}));
      geo.dispose(); line.renderOrder=1; line.visible=proxiesShown;
      line.position.fromArray(g.pos_mm).multiplyScalar(.001); line.quaternion.fromArray(g.rotation_xyzw);
      owner.add(line); proxyLines.push(line); proxiesDrawn++;
    });
  }
  // The section: one clipping plane shared by every solid's material, in scene coordinates.
  const clipPlane=new THREE.Plane(); let section=null;
  function applySection() {
    if (section) {
      model.updateMatrixWorld(true);
      clipPlane.set(new THREE.Vector3(...SECTION_NORMALS[section.plane]).negate(), section.offset_mm*.001).applyMatrix4(model.matrixWorld);
    }
    meshes.forEach(m=>Object.values(m.userData.materials||{parts:m.material}).forEach(mat=>{mat.clippingPlanes=section?[clipPlane]:null; mat.clipShadows=true; mat.needsUpdate=true;}));
    lineMaterial.clippingPlanes=section?[clipPlane]:null; lineMaterial.needsUpdate=true;
  }
  function setSection(plane, offset) {
    section=(plane in SECTION_NORMALS&&Number.isFinite(offset))?{plane,offset_mm:offset}:null;
    applySection(); draw(); return section&&{...section};
  }
  // The leader lines: model-frame segments, hidden until showLines(true).
  let leaders=null;
  function setLines(segments) {
    if (leaders) {model.remove(leaders); leaders.geometry.dispose(); leaders.material.dispose(); leaders=null;}
    const flat=(segments||[]).flatMap(l=>[...l.start_mm,...l.end_mm]).map(v=>v*.001);
    if (flat.length) {
      const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(flat,3));
      leaders=new THREE.LineSegments(geo,new THREE.LineBasicMaterial({color:LEADER.color,transparent:true,opacity:LEADER.opacity,toneMapped:false}));
      leaders.visible=false; model.add(leaders);
    }
    draw(); return flat.length/6;
  }
  function showLines(flag) {if (leaders) leaders.visible=!!flag; draw(); return !!(leaders&&leaders.visible);}
  // The course the design stands on (ADR-734), drawn as one ground (ADR-743): a single surface
  // sampled from the served course -- the highest box top over each point, or the plane, for a box
  // course; the grid, run out over TERRAIN.blend_mm to the mat, for a heightfield -- in the mat's
  // own material. The sample lines take every box corner's x and y on both sides of it
  // (TERRAIN.wall_mm), so a step's face is a wall and not a ramp. A box course's surface runs over
  // its run-out (ADR-745) and ends at its plane, where the mat lies, so the two meet without a
  // seam. It is the stage, not the
  // design: it sizes, picks and outlines nothing. setTerrain(null) removes it.
  const ground=new THREE.Group(); world.add(ground);
  let terrain=null, terrainMaterial=null, surface=null;
  // The box's axes in the world (its rotation's columns): a world vector's local components are
  // its dot with each.
  const axesOf=b=> {
    const [qx,qy,qz,qw]=b.rotation_xyzw;
    return [[1-2*(qy*qy+qz*qz),2*(qx*qy+qz*qw),2*(qx*qz-qy*qw)],[2*(qx*qy-qz*qw),1-2*(qx*qx+qz*qz),2*(qy*qz+qx*qw)],
            [2*(qx*qz+qy*qw),2*(qy*qz-qx*qw),1-2*(qx*qx+qy*qy)]];
  };
  // The highest point of a box (centre, xyzw rotation, half-extents; mm) on the vertical line at
  // (x, y), or -Infinity: the line, in the box's own frame, clipped to each of its three slabs.
  const boxTop=(b,x,y)=> {
    const dx=x-b.centre_mm[0], dy=y-b.centre_mm[1], R=axesOf(b);
    let lo=-Infinity, hi=Infinity;
    for (let i=0;i<3;i++) {
      const o=R[i][0]*dx+R[i][1]*dy-R[i][2]*b.centre_mm[2], d=R[i][2], h=b.half_mm[i];
      if (Math.abs(d)<1e-12) {if (Math.abs(o)>h) return -Infinity; continue;}
      const a=(-h-o)/d, c=(h-o)/d; lo=Math.max(lo,Math.min(a,c)); hi=Math.min(hi,Math.max(a,c));
    }
    return lo<=hi?hi:-Infinity;
  };
  // The top of a dome's sphere (centre, radius; mm) over (x, y), or -Infinity off it (ADR-744).
  const domeTop=(d,x,y)=> {
    const reach=d.radius_mm*d.radius_mm-(x-d.centre_mm[0])**2-(y-d.centre_mm[1])**2;
    return reach>=0?d.centre_mm[2]+Math.sqrt(reach):-Infinity;
  };
  const corners=b=>[-1,1].flatMap(i=>[-1,1].flatMap(j=>[-1,1].map(k=> {
    const v=new THREE.Vector3(i*b.half_mm[0],j*b.half_mm[1],k*b.half_mm[2]).applyQuaternion(new THREE.Quaternion().fromArray(b.rotation_xyzw));
    return [v.x+b.centre_mm[0],v.y+b.centre_mm[1]];
  })));
  // A sorted axis of samples: every `pitch` across [lo, hi], and each break on both sides of it.
  const axis=(lo,hi,pitch,breaks)=> {
    const n=Math.max(1,Math.ceil((hi-lo)/pitch)), at=[];
    for (let k=0;k<=n;k++) at.push(lo+(hi-lo)*k/n);
    breaks.forEach(v=>{if (v>lo&&v<hi) at.push(v-TERRAIN.wall_mm,v+TERRAIN.wall_mm);});
    at.sort((a,b)=>a-b);
    return at.filter((v,i)=>i===0||v-at[i-1]>.01);
  };
  // The surface: sample axes and the height (mm) at each of their crossings, row-major by y.
  function sampleSurface(block) {
    let x0=block.x_range_mm[0], x1=block.x_range_mm[1], y0=block.y_range_mm[0], y1=block.y_range_mm[1], height, bx=[], by=[], run, far=null;
    if (block.kind==='boxes') {
      const boxes=block.boxes||[], domes=block.domes||[], plane=block.plane_z_mm??block.lowest_mm;
      const exact=(x,y,skip)=>domes.reduce((z,d)=>Math.max(z,domeTop(d,x,y)),boxes.reduce((z,b)=>b===skip?z:Math.max(z,boxTop(b,x,y)),plane));
      // ADR-745: the course's ground runs on past its extent (its run-out boxes reach 50 m), so the
      // surface is fine over the extent and what stands near it, coarse over the flat run-out past
      // that (exact there too: it is planar between breaks), and eased to the plane past its end.
      const [ex0,ex1]=block.x_range_mm, [ey0,ey1]=block.y_range_mm, near=(v,lo,hi)=>v>=lo-TERRAIN.reach_mm&&v<=hi+TERRAIN.reach_mm;
      let ox0=x0, ox1=x1, oy0=y0, oy1=y1;
      boxes.forEach(b=>corners(b).forEach(([x,y])=> {
        bx.push(x); by.push(y); ox0=Math.min(ox0,x); ox1=Math.max(ox1,x); oy0=Math.min(oy0,y); oy1=Math.max(oy1,y);
        if (near(x,ex0,ex1)) {x0=Math.min(x0,x); x1=Math.max(x1,x);}
        if (near(y,ey0,ey1)) {y0=Math.min(y0,y); y1=Math.max(y1,y);}
      }));
      // A box turned about x or y (a ramp, a rock's stone) meets the ground under it in a line along
      // the other axis: that line is a break too, so the crease is drawn where it is.
      boxes.forEach(b=> {
        const R=axesOf(b); if (R.every(a=>Math.abs(Math.abs(a[0])+Math.abs(a[1])+Math.abs(a[2])-1)<1e-9)) return;
        const z0=exact(b.centre_mm[0],b.centre_mm[1],b);
        R.forEach((a,i)=>[-1,1].forEach(sign=> {
          const h=sign*b.half_mm[i], dz=a[2]*(z0-b.centre_mm[2]);
          if (Math.abs(a[2])<1e-9) return;
          if (Math.abs(a[1])<1e-9&&Math.abs(a[0])>1e-9) bx.push(b.centre_mm[0]+(h-dz)/a[0]);
          if (Math.abs(a[0])<1e-9&&Math.abs(a[1])>1e-9) by.push(b.centre_mm[1]+(h-dz)/a[1]);
        }));
      });
      // A dome is smooth, so it adds no breaks; only its foot on the plane widens the extent.
      domes.forEach(d=>{const r=Math.sqrt(Math.max(0,d.radius_mm**2-(plane-d.centre_mm[2])**2));
        x0=Math.min(x0,d.centre_mm[0]-r); x1=Math.max(x1,d.centre_mm[0]+r); y0=Math.min(y0,d.centre_mm[1]-r); y1=Math.max(y1,d.centre_mm[1]+r);});
      ox0=Math.min(ox0,x0); ox1=Math.max(ox1,x1); oy0=Math.min(oy0,y0); oy1=Math.max(oy1,y1);
      // Shared edges are one break; a course with more than `breaks` a side gets sloped faces.
      const once=a=>[...new Set(a.map(v=>Math.round(v*100)/100))];
      bx=once(bx); by=once(by);
      if (bx.length>TERRAIN.breaks) bx=[];
      if (by.length>TERRAIN.breaks) by=[];
      // A course with no run-out (an export's, a hand-made one) is exact everywhere: past its boxes
      // it is the plane.
      const runout=ox0<x0-TERRAIN.blend_mm||ox1>x1+TERRAIN.blend_mm||oy0<y0-TERRAIN.blend_mm||oy1>y1+TERRAIN.blend_mm;
      height=(x,y)=> {
        const cx=Math.min(ox1,Math.max(ox0,x)), cy=Math.min(oy1,Math.max(oy0,y));
        if (!runout||(cx===x&&cy===y)) return exact(x,y);
        const edge=exact(cx,cy), t=Math.min(1,Math.hypot(x-cx,y-cy)/TERRAIN.blend_mm), s=t*t*(3-2*t);
        return edge+(plane-edge)*s;
      };
      run=TERRAIN.margin_mm;
      if (runout) far=[ox0,ox1,oy0,oy1];
    } else {
      const {rows,columns,heights_mm:h}=block.grid, [gx0,gx1]=block.x_range_mm, [gy0,gy1]=block.y_range_mm, mat=block.lowest_mm-50;
      for (let k=0;k<columns;k++) bx.push(gx0+(gx1-gx0)*k/(columns-1));
      for (let r=0;r<rows;r++) by.push(gy0+(gy1-gy0)*r/(rows-1));
      // Inside, the grid's own vertices; outside, its edge eased down to the mat over blend_mm.
      height=(x,y)=> {
        const cx=Math.min(gx1,Math.max(gx0,x)), cy=Math.min(gy1,Math.max(gy0,y));
        const k=Math.round((cx-gx0)/(gx1-gx0)*(columns-1)), r=Math.round((cy-gy0)/(gy1-gy0)*(rows-1)), edge=h[r*columns+k];
        const t=Math.min(1,Math.hypot(x-cx,y-cy)/TERRAIN.blend_mm), s=t*t*(3-2*t);
        return edge+(mat-edge)*s;
      };
      run=TERRAIN.blend_mm;
    }
    x0-=run; x1+=run; y0-=run; y1+=run;
    const pitch=Math.max(TERRAIN.pitch_mm,Math.sqrt((x1-x0)*(y1-y0)/TERRAIN.samples));
    // A heightfield's samples are its own vertices over its extent, exactly as it is triangulated,
    // and the run-out's past them.
    const own=(a,lo,hi,grid)=>a.filter(v=>v<lo).concat(grid,a.filter(v=>v>hi));
    // Past the fine span, a box course's run-out at TERRAIN.far_mm to its end and the blend past it.
    const outer=(lo,hi,a,b,breaks)=>far
      ? [...new Set([...axis(Math.min(lo,a)-TERRAIN.blend_mm,lo,TERRAIN.far_mm,breaks),...axis(lo,hi,pitch,breaks),
                     ...axis(hi,Math.max(hi,b)+TERRAIN.blend_mm,TERRAIN.far_mm,breaks)])].sort((p,q)=>p-q)
      : axis(lo,hi,pitch,breaks);
    const xs=block.kind==='boxes'?outer(x0,x1,far&&far[0],far&&far[1],bx):own(axis(x0,x1,pitch,[]),bx[0],bx.at(-1),bx);
    const ys=block.kind==='boxes'?outer(y0,y1,far&&far[2],far&&far[3],by):own(axis(y0,y1,pitch,[]),by[0],by.at(-1),by);
    const z=new Float64Array(xs.length*ys.length);
    ys.forEach((y,r)=>xs.forEach((x,k)=>{z[r*xs.length+k]=height(x,y);}));
    return {xs,ys,z};
  }
  // The drawn height at (x, y), mm, read off the surface's own triangles (each cell split on its
  // (0,0)-(1,1) diagonal, as drawn), or null off the surface.
  function groundAt(x,y) {
    if (!surface) return null;
    const {xs,ys,z}=surface, n=xs.length;
    const find=(a,v)=>{let lo=0,hi=a.length-1; if (v<a[0]||v>a[hi]) return -1; while (hi-lo>1) {const m=(lo+hi)>>1; if (a[m]<=v) lo=m; else hi=m;} return lo;};
    const k=find(xs,x), r=find(ys,y);
    if (k<0||r<0) return null;
    const u=(x-xs[k])/(xs[k+1]-xs[k]), v=(y-ys[r])/(ys[r+1]-ys[r]);
    const z00=z[r*n+k], z10=z[r*n+k+1], z01=z[(r+1)*n+k], z11=z[(r+1)*n+k+1];
    return u>=v?z00+u*(z10-z00)+v*(z11-z10):z00+v*(z01-z00)+u*(z11-z01);
  }
  function setTerrain(block) {
    const had=!!terrain;
    ground.children.slice().forEach(o=>{ground.remove(o); o.geometry.dispose();});
    terrain=block&&((block.kind==='boxes'&&Array.isArray(block.boxes))||(block.kind==='heightfield'&&block.grid))?block:null;
    surface=terrain?sampleSurface(terrain):null;
    // One material, and one 2048-texel canvas, for the whole course: the mat's own palette, so
    // where the course lies at the plane it is the mat.
    if (!terrainMaterial) terrainMaterial=prototypeMaterial({palette:STAGE.tile, labels});
    if (surface) {
      const {xs,ys,z}=surface, n=xs.length, at=new Float32Array((n-1)*(ys.length-1)*18), uv=new Float32Array(at.length/3*2);
      const tile=2*GRID_PITCH*1000; let o=0;
      const corner=(k,r)=>[xs[k]*.001,ys[r]*.001,z[r*n+k]*.001];
      const face=(a,b,c)=> {
        // World-anchored uvs in blocks: a facet takes the two world axes it is most nearly flat
        // along, so its grid lines sit on the mat's whole metres and a wall's are not smeared.
        const ux=b[0]-a[0], uy=b[1]-a[1], uz=b[2]-a[2], vx=c[0]-a[0], vy=c[1]-a[1], vz=c[2]-a[2];
        const nx=Math.abs(uy*vz-uz*vy), ny=Math.abs(uz*vx-ux*vz), nz=Math.abs(ux*vy-uy*vx);
        [a,b,c].forEach(p=> {
          const [s,t]=nz>=nx&&nz>=ny?[p[0],p[1]]:nx>=ny?[p[1],p[2]]:[p[0],p[2]];
          uv[o/3*2]=s*1000/tile; uv[o/3*2+1]=t*1000/tile; at[o]=p[0]; at[o+1]=p[1]; at[o+2]=p[2]; o+=3;
        });
      };
      for (let r=0;r+1<ys.length;r++) for (let k=0;k+1<n;k++) {
        const p00=corner(k,r), p10=corner(k+1,r), p01=corner(k,r+1), p11=corner(k+1,r+1);
        face(p00,p10,p11); face(p00,p11,p01);
      }
      const geo=new THREE.BufferGeometry();
      geo.setAttribute('position',new THREE.BufferAttribute(at,3));
      geo.setAttribute('normal',new THREE.BufferAttribute(creaseNormals(at),3));
      geo.setAttribute('uv',new THREE.BufferAttribute(uv,2));
      const m=new THREE.Mesh(geo,terrainMaterial); m.receiveShadow=true; m.name='ground'; ground.add(m);
    }
    // A course arriving where there was none is framed; a course swapped for another (a playback's
    // own) keeps the person's camera.
    if (bounds) {frameBounds(bounds); if (terrain&&!had) fit();}
    // The trail lies on the ground, so it is laid again on a new one.
    if (trailCourse) buildTrail();
    if (targetCourse) buildTargets();
    draw(); return terrain?(terrain.boxes||[]).length+(terrain.domes||[]).length||1:0;
  }
  // The timer: one textured quad in an orthographic overlay scene, painted after the stage.
  const hud=new THREE.Scene(), hudCamera=new THREE.OrthographicCamera(0,1,1,0,-1,1);
  const clockCanvas=document.createElement('canvas'), clockTexture=new THREE.CanvasTexture(clockCanvas);
  clockTexture.colorSpace=THREE.SRGBColorSpace;
  const clockMesh=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:clockTexture,transparent:true,depthTest:false,depthWrite:false,toneMapped:false}));
  hud.add(clockMesh); let clock=null, clockKey='';
  function paintClock(w,h) {
    const r=renderer.getPixelRatio(), text=clock.toFixed(2)+' s', size=Math.max(CLOCK.minSize,Math.round(h*CLOCK.size));
    const key=JSON.stringify([text,w,h,r]); if (key!==clockKey) {
      clockKey=key; const ctx=clockCanvas.getContext('2d'), font=`600 ${size*r}px ${CLOCK.font}`;
      ctx.font=font; ctx.letterSpacing=`${.12*size*r}px`;
      const tw=Math.ceil(ctx.measureText(text).width+.12*size*r), px=Math.round(.7*size*r), py=Math.round(.4*size*r), line=1.5*r;
      clockCanvas.width=tw+2*px+2*line; clockCanvas.height=size*r+2*py+2*line;
      const W=clockCanvas.width, H=clockCanvas.height, rad=H/2;
      ctx.font=font; ctx.letterSpacing=`${.12*size*r}px`; ctx.textBaseline='middle';
      ctx.beginPath(); ctx.moveTo(rad,line); ctx.lineTo(W-rad,line); ctx.arc(W-rad,rad,rad-line,-Math.PI/2,Math.PI/2);
      ctx.lineTo(rad,H-line); ctx.arc(rad,rad,rad-line,Math.PI/2,3*Math.PI/2); ctx.closePath();
      ctx.fillStyle=CLOCK.panel; ctx.fill(); ctx.strokeStyle=CLOCK.line; ctx.lineWidth=line; ctx.stroke();
      ctx.fillStyle=CLOCK.ink; ctx.fillText(text,px+line,H/2);
      clockTexture.needsUpdate=true;
      clockMesh.scale.set(W/r,H/r,1);
      clockMesh.position.set(CLOCK.margin*h+W/(2*r),CLOCK.margin*h+H/(2*r),0);
    }
    hudCamera.right=w; hudCamera.top=h; hudCamera.updateProjectionMatrix();
  }
  // The wireframe pass (ADR-534; 'hairline' until ADR-602): the solids' view normals and depth go
  // to an offscreen target at twice the canvas's resolution, an edge pass marks ink wherever either
  // jumps between neighbouring pixels -- the silhouettes against depth, the creases against the
  // facets' own normals (flat, so smooth shading never softens a crease) -- with a hard threshold,
  // and the canvas takes the average of each 2x2 block. So a line is crisp and one pixel wide and
  // its stair-steps are smoothed, rather than a soft threshold's grey halo. A tessellated fillet's
  // facets turn by less than the crease threshold, so a curved face stays clean of ink.
  //
  // The mesh lines (ADR-602) are a second, optional layer under the ink: each solid's facet edges
  // that turn by more than MESH_LINES.angle, on their own layer, drawn into a third target over a
  // depth-only prepass of the solids (pushed back a hair, so a line on a surface wins and a line
  // behind one loses), and mixed in at `strength` of the ink.
  const SUPERSAMPLE=2, LINES_LAYER=1;
  let style='shaded', target=null, edges=null, lineTarget=null, heatTarget=null;
  const heatMaterials=new Map();
  function heatMaterial(hex) {
    if (!heatMaterials.has(hex)) heatMaterials.set(hex,new THREE.MeshBasicMaterial({color:hex, side:THREE.DoubleSide, toneMapped:false}));
    return heatMaterials.get(hex);
  }
  let meshLines={shown:true, strength:MESH_LINES.strength};
  const paper=new THREE.Color(), ink=new THREE.Color();
  const normals=new THREE.MeshNormalMaterial({side:THREE.DoubleSide, flatShading:true});
  const prepass=new THREE.MeshBasicMaterial({colorWrite:false, side:THREE.DoubleSide, polygonOffset:true, polygonOffsetFactor:1, polygonOffsetUnits:1});
  const lineMaterial=new THREE.LineBasicMaterial({color:0xffffff, toneMapped:false});
  const fullscreen='varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }';
  const edgePass=new THREE.ShaderMaterial({
    uniforms:{tNormal:{value:null}, tDepth:{value:null}, texel:{value:new THREE.Vector2()}, near:{value:.01}, far:{value:100}},
    vertexShader:fullscreen,
    fragmentShader:`uniform sampler2D tNormal; uniform sampler2D tDepth; uniform vec2 texel; uniform float near, far;
      varying vec2 vUv;
      float lin(vec2 uv){ float z=texture2D(tDepth,uv).x*2.-1.; return 2.*near*far/(far+near-z*(far-near)); }
      vec3 nrm(vec2 uv){ return texture2D(tNormal,uv).xyz*2.-1.; }
      void main(){
        vec3 n0=nrm(vUv); float d0=lin(vUv), e=0.;
        vec2 o[4]; o[0]=vec2(1.,0.); o[1]=vec2(-1.,0.); o[2]=vec2(0.,1.); o[3]=vec2(0.,-1.);
        for (int i=0;i<4;i++) {
          vec2 uv=vUv+o[i]*texel; float d=lin(uv);
          // Only the nearer side of a depth jump is inked, so a silhouette is one line, not two.
          if (1.-dot(n0,nrm(uv))>.2) e=1.;
          if (d>d0 && (d-d0)/d0>.025) e=1.;
        }
        gl_FragColor=vec4(e,e,e,1.);
      }`,
    depthTest:false, depthWrite:false, toneMapped:false});
  // The heat view (setHeat) carries into the diagram: a heated part's face is washed in its colour
  // and its lines are drawn in it, over the same paper and ink.
  const resolvePass=new THREE.ShaderMaterial({
    uniforms:{tEdges:{value:null}, tLines:{value:null}, tHeat:{value:null}, heated:{value:0}, strength:{value:0}, paper:{value:new THREE.Vector3()}, ink:{value:new THREE.Vector3()}},
    vertexShader:fullscreen,
    fragmentShader:`uniform sampler2D tEdges; uniform sampler2D tLines; uniform sampler2D tHeat; uniform float heated, strength; uniform vec3 paper, ink; varying vec2 vUv;
      void main(){
        vec4 h=heated>.5?texture2D(tHeat,vUv):vec4(0.);
        vec3 tint=h.a>0.?pow(h.rgb/h.a,vec3(1./2.2)):ink;
        vec3 face=mix(paper,tint,.32*h.a), line=mix(ink,tint,h.a);
        vec3 under=mix(face,line,strength*texture2D(tLines,vUv).r);
        gl_FragColor=vec4(mix(under,line,texture2D(tEdges,vUv).r),1.);
      }`,
    depthTest:false, depthWrite:false, toneMapped:false});
  const passScene=new THREE.Scene(), passCamera=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
  const passQuad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),edgePass);
  passScene.add(passQuad);
  function srgb(colour, vector) {const c=colour.clone().convertLinearToSRGB(); vector.set(c.r,c.g,c.b);}
  function setColours({paper:p=null, ink:k=null}={}) {paper.set(p||WIREFRAME.paper); ink.set(k||WIREFRAME.ink);}
  setColours();
  // Each solid's mesh lines, built the first time they are drawn and kept with the solid.
  function buildMeshLines() {
    meshes.forEach(m=> {
      if (m.userData.meshLines) return;
      const line=new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry,MESH_LINES.angle),lineMaterial);
      line.layers.set(LINES_LAYER); line.raycast=()=>{}; m.add(line); m.userData.meshLines=line;
    });
  }
  function meshLineCount() {let n=0; meshes.forEach(m=>{if(m.userData.meshLines)n+=m.userData.meshLines.geometry.attributes.position.count/2;}); return n;}
  function paintWireframe() {
    const size=renderer.getDrawingBufferSize(new THREE.Vector2());
    // At most 16 Mpx offscreen, so a large high-DPI canvas does not run a small GPU out of memory.
    const limit=renderer.capabilities.maxTextureSize;
    const scale=Math.max(1,Math.min(SUPERSAMPLE,limit/size.x,limit/size.y,Math.sqrt(16e6/(size.x*size.y))));
    const w=Math.floor(size.x*scale), h=Math.floor(size.y*scale);
    if (!target||target.width!==w||target.height!==h) {
      if (target) {target.depthTexture.dispose(); target.dispose(); edges.dispose(); lineTarget.dispose(); heatTarget.dispose();}
      target=new THREE.WebGLRenderTarget(w,h,{depthTexture:new THREE.DepthTexture(w,h),minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter});
      // Linear filtering at each canvas pixel's centre is the mean of its 2x2 block.
      edges=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,depthBuffer:false});
      lineTarget=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter});
      heatTarget=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter});
    }
    const background=scene.background, fog=scene.fog, shown=world.children.map(o=>o.visible);
    scene.background=null; scene.fog=null; scene.overrideMaterial=normals;
    world.children.forEach(o=>{if(o!==model)o.visible=false;});
    renderer.setRenderTarget(target); renderer.setClearColor(0x000000,0); renderer.clear(); renderer.render(scene,camera);
    const lines=meshLines.shown&&meshLines.strength>0;
    if (lines) {
      buildMeshLines();
      renderer.setRenderTarget(lineTarget); renderer.clear();
      scene.overrideMaterial=prepass; renderer.render(scene,camera);
      scene.overrideMaterial=null; camera.layers.set(LINES_LAYER);
      renderer.autoClear=false; renderer.render(scene,camera); renderer.autoClear=true;
      camera.layers.set(0);
    }
    // The heat: every solid's depth first, pushed back a hair, then each heated solid in its
    // colour, so a part in front of a heated one still hides it.
    const heated=!!heat&&meshes.size>0;
    if (heated) {
      renderer.setRenderTarget(heatTarget); renderer.setClearColor(0x000000,0); renderer.clear();
      scene.overrideMaterial=prepass; renderer.render(scene,camera); scene.overrideMaterial=null;
      const swapped=[];
      meshes.forEach((m,n)=> {
        const h=m.userData.world?null:heat[n];
        swapped.push([m,m.material,m.visible]);
        if (h==null) m.visible=false; else m.material=heatMaterial(h);
      });
      renderer.autoClear=false; renderer.render(scene,camera); renderer.autoClear=true;
      swapped.forEach(([m,material,visible])=>{m.material=material; m.visible=visible;});
    }
    scene.background=background; scene.fog=fog; scene.overrideMaterial=null;
    world.children.forEach((o,i)=>{o.visible=shown[i];});
    const u=edgePass.uniforms;
    u.tNormal.value=target.texture; u.tDepth.value=target.depthTexture;
    u.texel.value.set(1/w,1/h); u.near.value=camera.near; u.far.value=camera.far;
    passQuad.material=edgePass; renderer.setRenderTarget(edges); renderer.render(passScene,passCamera);
    renderer.setRenderTarget(null);
    const r=resolvePass.uniforms;
    r.tEdges.value=edges.texture; r.tLines.value=lineTarget.texture; r.strength.value=lines?meshLines.strength:0;
    r.tHeat.value=heatTarget.texture; r.heated.value=heated?1:0;
    srgb(paper,r.paper.value); srgb(ink,r.ink.value);
    passQuad.material=resolvePass; renderer.render(passScene,passCamera);
  }
  function setStyle(name, colours={}) {
    // A stored choice from before ADR-602 still means the diagram.
    if (name==='hairline') name='wireframe';
    if (STYLES.includes(name)) style=name;
    setColours(colours); draw();
    return style;
  }
  // The mesh lines' switch and strength (0..MESH_LINES.max of the ink); either may be left out.
  function setMeshLines({shown=meshLines.shown, strength=meshLines.strength}={}) {
    const s=Number(strength);
    meshLines={shown:!!shown, strength:Number.isFinite(s)?Math.max(0,Math.min(MESH_LINES.max,s)):meshLines.strength};
    draw(); return {...meshLines};
  }
  let onDraw=null;
  function paint() {
    if (style==='wireframe') {paintWireframe(); paintOutline(); if (onDraw) onDraw(); return;}
    renderer.render(scene,camera);
    if (occluded&&meshes.size&&model.visible) paintOcclusion();
    paintOutline();
    if (onDraw) onDraw();
    if (clock===null) return;
    paintClock(canvas.clientWidth||canvas.width,canvas.clientHeight||canvas.height);
    renderer.autoClear=false; renderer.clearDepth(); renderer.render(hud,hudCamera); renderer.autoClear=true;
  }
  // Occlusion over the frame just drawn: the solids and the mat, without the ghost, the lines or
  // the timer. Its radius follows the design's size, capped by the camera's distance.
  function paintOcclusion() {
    const size=(bounds?.radius||100)*.001, radius=Math.max(1e-4,Math.min(OCCLUSION.radius*size,OCCLUSION.maxRadius*c.distance*.001));
    const lines=[];
    occlusion.apply(scene,camera,{radius, distance:c.distance*.001, clipping:section?[clipPlane]:null, hide:on=> {
      if (on) {ghost.visible=false; trail.visible=false; scene.traverse(o=>{if((o.isLine||o.isPoints)&&o.visible){o.visible=false;lines.push(o);}});}
      else {ghost.visible=true; trail.visible=true; lines.forEach(o=>{o.visible=true;}); lines.length=0;}
    }});
  }
  // The selection's outline (ADR-676), over everything but the timer.
  function paintOutline() {
    if (!selectedNames.length||!model.visible) return;
    const solids=[...meshes.values()].filter(m=>m.visible), chosen=selectedNames.map(n=>meshes.get(n)).filter(m=>m&&m.visible);
    outline.apply(scene,camera,chosen,solids,section?[clipPlane]:null);
  }
  function pose(mesh,p) {
    if (!p) return;
    mesh.position.fromArray(p.position_mm).multiplyScalar(.001);
    mesh.quaternion.fromArray(p.rotation_xyzw);
  }
  function updateBounds() {
    model.updateMatrixWorld(true);
    // Bounds in model-local simulator coordinates, not the rotated scene. A part the engine calls
    // world geometry (a task floor) is the stage, not the design, so it sizes nothing unless it is all there is.
    const box = new THREE.Box3(), design=[...meshes.values()].filter(m=>!m.userData.world);
    (design.length?design:[...meshes.values()]).forEach(m=> {m.updateMatrix(); const matrix=m.matrix.clone(); matrix.elements[12]*=1000;matrix.elements[13]*=1000;matrix.elements[14]*=1000; const b=m.userData.mmBounds.clone().applyMatrix4(matrix);box.union(b);});
    if (box.isEmpty()) {bounds=null; return;}
    const min=box.min.toArray(), max=box.max.toArray();
    bounds={min,max,center:min.map((v,i)=>(v+max[i])/2),radius:Math.hypot(...min.map((v,i)=>max[i]-v))/2 || 1};
  }
  // The highest point of the world geometry the viewport does not draw, mm, at its current pose;
  // null when there is none.
  function worldTop() {
    const hidden=[...meshes.values()].filter(m=>m.userData.world&&!m.visible), v=new THREE.Vector3();
    if (!hidden.length) return null;
    let top=-Infinity;
    hidden.forEach(m=> {
      m.updateMatrix(); const a=m.geometry.attributes.position;
      for (let i=0;i<a.count;i++) top=Math.max(top,v.fromBufferAttribute(a,i).applyMatrix4(m.matrix).z);
    });
    return top*1000;
  }
  // Where the mat lies (ADR-600): on the top of the design's own floor -- the world geometry, which
  // is never drawn beside it -- so the design stands on the mat as it stands on that floor; with
  // no world geometry, under the design's lowest point. World geometry that rises above the
  // design's lowest point by more than a floor could (2 mm, or 2 % of the design's height) is more
  // than a floor, and the mat stays under the design. The mat is pushed back in depth rather than
  // lowered (floor.js), so a part resting exactly on it never z-fights.
  let floorSource='design';
  function matZ(b) {
    if (terrain) {floorSource='terrain'; return (terrain.plane_z_mm??terrain.lowest_mm-50)/1000;}
    const top=worldTop(), low=b.min[2], slack=Math.max(2,.02*(b.max[2]-b.min[2]));
    floorSource=top===null?'design':top<=low+slack?'world':'design';
    return (floorSource==='world'?top:low)/1000;
  }
  // The key light looks at a point of the design, mm, from its own direction and distance; the
  // shadow camera, which it carries, then hugs the design wherever the design has moved to.
  let sunReach=1;
  function aimSun(center) {
    const focus=new THREE.Vector3(center[0]/1000,center[2]/1000,-center[1]/1000);
    sun.target.position.copy(focus); sun.position.copy(focus).add(new THREE.Vector3(...keyDir).normalize().multiplyScalar(sunReach));
  }
  function frameBounds(b) {
    bounds=JSON.parse(JSON.stringify(b)); floorZ=matZ(b);
    const focus=new THREE.Vector3(b.center[0]/1000,b.center[2]/1000,-b.center[1]/1000);
    // The shadow camera hugs the design (ADR-676): its depth range is the design's own, so the
    // soft (variance) map keeps its precision at any scale and never streaks. It is wide enough
    // for a shadow cast at the lowest key any lighting setup uses.
    const h=Math.max(.01,b.radius/1000*1.7), reach=4*h;
    sunReach=reach; aimSun(b.center);
    Object.assign(sun.shadow.camera,{left:-h,right:h,top:h,bottom:-h,near:reach-2*h,far:reach+2*h});
    sun.shadow.camera.updateProjectionMatrix();
    sun.shadow.normalBias=0;
    staged='';
  }
  // The camera's clip planes (ADR-600): near is a fixed fraction of the camera's distance, so the
  // depth buffer's precision scales with the shot and the mat never z-fights the design at any
  // zoom; far is the stage's, which follows the floor (environment.js), so the mat never pops.
  const NEAR_FRACTION=.002;
  let stageFloor={roomSize:0, far:1, centre:[0,0]};
  function draw() {
    // A canvas with no layout box (its editor on the hidden shelf) keeps its buffer: canvas.width is
    // already in device pixels, so sizing from it would multiply by the pixel ratio on every draw
    // until a high-DPI phone runs out of GPU memory and loses the context.
    const ratio=renderer.getPixelRatio(), laid=canvas.clientWidth>0&&canvas.clientHeight>0;
    const w=laid?canvas.clientWidth:canvas.width/ratio,h=laid?canvas.clientHeight:canvas.height/ratio;
    if (laid&&(renderer.domElement.width!==Math.floor(w*ratio) || renderer.domElement.height!==Math.floor(h*ratio))) renderer.setSize(w,h,false);
    camera.aspect=w/h;
    const d=c.distance/1000, t=c.target.map(x=>x/1000), cp=Math.cos(c.pitch);
    camera.position.set(t[0]+d*cp*Math.cos(c.yaw),t[2]+d*Math.sin(c.pitch),-t[1]-d*cp*Math.sin(c.yaw));
    camera.lookAt(t[0],t[2],-t[1]);
    const key=JSON.stringify([d,w/h,floorZ]);
    if (key!==staged) {stage=environment.setStage({camDist:d, floorZ, centre:[t[0],t[1]]}); staged=key;}
    // The ground never ends (ADR-742): the mat is centred on the target and reaches the design
    // wherever a rollout has carried it, so a long run is over drawn ground at every frame.
    const at=centreAt(null);
    stageFloor=environment.setCentre([t[0],t[1]], at?Math.hypot(at[0]/1000-t[0],at[1]/1000-t[1]):0);
    camera.near=Math.min(1,Math.max(1e-5,d*NEAR_FRACTION)); camera.far=Math.max(stageFloor.far,d*4);
    camera.updateProjectionMatrix();
    // The presentation floor is front-sided: orbiting underneath remains a CAD inspection.
    paint();
  }
  function fit() {
    if (!bounds) return;
    // With parts hidden, Fit frames what is shown.
    if (hiddenNames.size&&fitTo([...meshes.keys()].filter(n=>meshes.get(n).visible&&!meshes.get(n).userData.world))) return;
    // Frame the bounding sphere in the narrower field of view: a canvas at least as wide as it is tall frames by
    // the vertical one (as it always has), a portrait one — a stage between two wide sidebars — by the horizontal.
    const w=canvas.clientWidth||canvas.width,h=canvas.clientHeight||canvas.height,tanV=Math.tan(camera.fov*Math.PI/360);
    const half=Math.min(Math.atan(tanV),Math.atan(tanV*Math.min(1,w/h)));
    // On a course (ADR-734) the frame takes in the ground just behind the design and TERRAIN.ahead_mm
    // of it ahead along +x, where courses run, so the first step or ramp is in the shot.
    let b=bounds;
    if (terrain) {
      const min=[b.min[0]-TERRAIN.behind_mm,b.min[1],Math.min(b.min[2],terrain.lowest_mm)], max=[b.max[0]+TERRAIN.ahead_mm,b.max[1],b.max[2]];
      b={min,max,center:min.map((v,i)=>(v+max[i])/2),radius:Math.hypot(...min.map((v,i)=>max[i]-v))/2};
    }
    c={yaw:.8,pitch:.5,distance:b.radius/Math.sin(half)*1.15,target:b.center.slice()};
    draw();
  }
  function clear() {
    disposeProxies(); proxyGeoms=[]; setLines([]); trailCourse=null; disposeTrail(); targetCourse=null; disposeTargets();
    meshes.forEach(m=> {
      model.remove(m); m.geometry.dispose(); Object.values(m.userData.materials).forEach(mat=>mat.dispose()); m.userData.meshLines?.geometry.dispose(); m.userData.outline?.geometry.dispose(); m.userData.outline?.material.dispose();
    });
    meshes.clear(); clearGhost(); bounds=null;triangleCount=0;picked=null;draw();
  }
  // The proxies to offer: the manifest's `collision.geoms`, each in its component's frame.
  // They are built against the installed solids and stay hidden until showProxies(true).
  function setProxies(geoms) {proxyGeoms=Array.isArray(geoms)?geoms.map(g=>JSON.parse(JSON.stringify(g))):[]; buildProxies(); draw();}
  function showProxies(flag) {proxiesShown=!!flag; proxyLines.forEach(l=>{l.visible=proxiesShown;}); draw(); return proxiesShown;}
  function showing() {return proxiesShown&&proxiesDrawn?'tessellated solids with collision proxies':'tessellated solids';}
  // A part's colour is its appearance role's (ADR-522) when the manifest gives one, as `look`
  // and the concept sheet paint it; a design with no assembly keeps the index palette.
  const colourOf=(entry,i)=>/^#[0-9A-Fa-f]{6}$/.test(entry.color||'')?parseInt(entry.color.slice(1),16):PALETTE[i%PALETTE.length];
  // A part's material (ADR-601): physical, from its finish, over its role colour, reflecting the
  // studio. A board with its own geometry is coloured per facet: solder mask, chip and tin.
  function material(entry, i, g) {
    const finish=finishOf(entry), f=FINISHES[finish], hex=/^#[0-9A-Fa-f]{6}$/.test(entry.color||'');
    const colour=new THREE.Color(hex||!f.colour?colourOf(entry,i):parseInt(f.colour.slice(1),16));
    const m=new THREE.MeshPhysicalMaterial({color:colour, roughness:f.roughness, metalness:f.metalness,
      clearcoat:f.clearcoat||0, clearcoatRoughness:f.clearcoatRoughness||0,
      envMap, envMapIntensity:f.env*reflections, side:THREE.DoubleSide});
    addDetail(m, f.metalness>.5?'metal':finish==='printed'?'printed':finish==='board'?'board':'purchased');
    let board=null;
    if (finish==='board'&&entry.board) {
      board=boardColours(entry.positions, entry.board, colour);
      g.setAttribute('color',new THREE.Float32BufferAttribute(board.colours,3));
      m.vertexColors=true; m.color.set(0xffffff);
      board={chip:board.chip, pad:board.pad};
    } else if (entry.colours) {
      // A training body carrying CAD (ADR-838): each part in its own colour.
      g.setAttribute('color',new THREE.Float32BufferAttribute(entry.colours,3));
      m.vertexColors=true; m.color.set(0xffffff);
    }
    return {m, finish, colour, board};
  }
  function install(entries) {
    clear();
    // The design's own floor and world geometry is never drawn beside a design (ADR-600): the mat
    // stands in for it, at its top. A model that is nothing but world geometry is drawn as it is.
    const design=entries.some(e=>e.world!==true);
    entries.forEach((entry,i)=> {
      const g=new THREE.BufferGeometry(), hidden=design&&entry.world===true;
      g.setAttribute('position',new THREE.Float32BufferAttribute(entry.positions.map(v=>v*.001),3));
      if (!hidden) g.setAttribute('normal',new THREE.Float32BufferAttribute(creaseNormals(entry.positions),3));
      g.computeBoundingBox();
      const {m:mat, finish, colour, board}=material(entry,i,g);
      // Its matcap twin (ADR-676) shares the page's one baked sphere; a look swaps between them.
      const twin=new THREE.MeshMatcapMaterial({color:0xffffff, side:THREE.DoubleSide, vertexColors:!!entry.colours});
      const m=new THREE.Mesh(g,mat);
      m.userData.materials={parts:mat, matcap:twin};
      m.userData.mmBounds=new THREE.Box3().setFromArray(entry.positions);
      m.userData.world=entry.world===true; m.userData.finish=finish; m.userData.env=FINISHES[finish].env; m.userData.colour=colour; m.userData.board=board; m.userData.tinted=!!entry.colours;
      m.visible=!hidden&&!(entry.world!==true&&hiddenNames.has(entry.name));
      m.castShadow=true;m.receiveShadow=true;pose(m,entry.placement);
      if (entry.outline?.length) {
        // The primitive the body trained as, outlined over its CAD (ADR-838); it moves with it.
        const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.Float32BufferAttribute(entry.outline.map(v=>v*.001),3));
        const line=new THREE.LineSegments(new THREE.EdgesGeometry(pg,20),new THREE.LineBasicMaterial({color:PRIMITIVE.color,transparent:true,opacity:PRIMITIVE.opacity,depthTest:false,toneMapped:false}));
        pg.dispose(); line.renderOrder=1; m.add(line); m.userData.outline=line;
      }
      meshes.set(entry.name,m);model.add(m);triangleCount+=entry.positions.length/9;
    });
    selectedNames=selectedNames.filter(n=>meshes.has(n)&&!meshes.get(n).userData.world);
    applyLook(); applySelection();
    updateBounds();if(bounds)frameBounds(bounds);applySection();fit();
    return entries.map((e,i)=>({name:e.name,triangles:e.positions.length/9,color:[16,8,0].map(shift=>(colourOf(e,i)>>shift)&255)}));
  }
  async function stlOf(url,fetchImpl) {const r=await fetchImpl(url);if(!r.ok)throw new Error('mesh HTTP '+r.status);return parseStl(await r.arrayBuffer());}
  // A body that carries CAD (ADR-838): its accepted parts, each placed in the body's frame and
  // in its own colour, are the solid; the primitive it trained as is kept as its outline.
  async function carried(e,primitive,fetchImpl) {
    const parts=await Promise.all(e.cad.map(async p=>({p, mm:await stlOf(p.mesh,fetchImpl)})));
    const positions=[], colours=[], v=new THREE.Vector3(), q=new THREE.Quaternion(), t=new THREE.Vector3(), c=new THREE.Color();
    parts.forEach(({p,mm},i)=> {
      q.fromArray(p.placement.rotation_xyzw); t.fromArray(p.placement.position_mm); c.setHex(colourOf(p,i));
      for (let k=0;k<mm.length;k+=3) {v.set(mm[k],mm[k+1],mm[k+2]).applyQuaternion(q).add(t); positions.push(v.x,v.y,v.z); colours.push(c.r,c.g,c.b);}
    });
    const first=e.cad[0]||{};
    return {...e, finish:first.finish, supplier:first.supplier, color:first.color, positions, colours, outline:primitive};
  }
  async function load(manifest,fetchImpl=window.fetch.bind(window)) {
    // A body with no primitive of its own may still carry CAD.
    const entries=await Promise.all((manifest?.components||[]).filter(e=>e.mesh||e.cad?.length).map(async e=> {
      const positions=e.mesh?await stlOf(e.mesh,fetchImpl):null;
      return e.outline&&e.cad?.length ? carried(e,positions,fetchImpl) : {...e, positions};
    }));
    return install(entries);
  }
  function setPoses(poses) {meshes.forEach((m,n)=>pose(m,poses[n]));draw();}
  // A ghost (the revision timeline's previous revision, ADR-547): translucent, unlit and
  // unshadowed, beside the model rather than in it, so it sizes, picks and outlines nothing
  // and a wireframe diagram leaves it out. World geometry has no ghost, as it has no solid.
  // setGhost([]) removes it.
  const ghost=new THREE.Group(); world.add(ghost);
  function clearGhost() {ghost.children.slice().forEach(m=>{ghost.remove(m);m.geometry.dispose();m.material.dispose();});}
  function setGhost(entries, colour=0x9a9a9a, opacity=.2) {
    clearGhost();
    (entries||[]).filter(entry=>entry.world!==true).forEach(entry=>{
      const g=new THREE.BufferGeometry();
      g.setAttribute('position',new THREE.Float32BufferAttribute(entry.positions.map(v=>v*.001),3));
      const m=new THREE.Mesh(g,new THREE.MeshBasicMaterial({color:colour,transparent:true,opacity,depthWrite:false,side:THREE.DoubleSide}));
      m.name=entry.name; m.renderOrder=1; pose(m,entry.placement); ghost.add(m);
    });
    draw();
    return ghost.children.length;
  }
  async function loadGhost(components,fetchImpl=window.fetch.bind(window),colour,opacity) {
    const entries=await Promise.all((components||[]).filter(e=>e.mesh).map(async e=> {
      const r=await fetchImpl(e.mesh);if(!r.ok)throw new Error('mesh HTTP '+r.status);
      return {...e, positions:parseStl(await r.arrayBuffer())};
    }));
    return setGhost(entries,colour,opacity);
  }
  // The trail (ADR-770): where the design has been on the rollout shown, on the ground under it,
  // up to the time shown. setTrail gives the course -- the design's centre at each frame and, for
  // footprints, its footfalls -- and each view draws it in its own style: a line, a dashed line,
  // dots along the way, a broad ribbon, or a dot where each foot came down. Its colours are
  // Settings' (setTrailColours): one colour, white by default, or a ramp by age from the oldest of
  // the trail shown to the newest. Like the ghost it is beside the model, so it sizes, picks and
  // outlines nothing, and the wireframe diagram and occlusion leave it out.
  const trail=new THREE.Group(); trail.renderOrder=2; world.add(trail);
  let trailCourse=null, trailStyle='off', trailEnds=[], trailAt=Infinity, trailTimes=null, trailT0=0;
  let trailColours={mode:'solid', solid:'#ffffff', stops:['#2a2a2a','#ffffff']}, trailRamp=null;
  const TRAIL_STYLES=['off','line','dashed','dots','ribbon','footprints'];
  function groundZ(x,y) {const g=groundAt(x,y); return g===null?floorZ*1000:g;}
  function disposeTrail() {trail.children.slice().forEach(o=>{trail.remove(o); o.geometry.dispose(); o.material.dispose();}); trailEnds=[]; trailTimes=null;}
  // The ramp as 256 linear colours, mixed in sRGB as the heat colours are.
  function buildRamp() {
    const stops=(trailColours.mode==='age'?trailColours.stops:[trailColours.solid,trailColours.solid]).map(h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255));
    trailRamp=new Float32Array(256*3); const c=new THREE.Color();
    for (let k=0;k<256;k++) {
      const t=k/255, n=stops.length-1, at=Math.min(n-1,Math.floor(t*n)), f=t*n-at, x=stops[at], y=stops[at+1];
      c.setRGB(x[0]+(y[0]-x[0])*f,x[1]+(y[1]-x[1])*f,x[2]+(y[2]-x[2])*f,THREE.SRGBColorSpace);
      trailRamp[3*k]=c.r; trailRamp[3*k+1]=c.g; trailRamp[3*k+2]=c.b;
    }
  }
  buildRamp();
  // Each vertex its colour: the one colour, or its age along the trail shown, newest at 1.
  function paintTrail(count) {
    const m=trail.children[0]; if (!m||!trailTimes) return;
    const col=m.geometry.attributes.color, a=col.array, age=trailColours.mode==='age';
    // One colour is painted once, over every vertex; by age, as far as is shown, every time.
    if (!age) {if (m.userData.painted) return; count=a.length/3; m.userData.painted=true;}
    const span=Math.max(1e-6,Math.min(trailAt,trailTimes[trailTimes.length-1])-trailT0);
    for (let i=0;i<count;i++) {
      const k=age?Math.max(0,Math.min(255,Math.round(255*(trailTimes[i]-trailT0)/span))):255;
      a[3*i]=trailRamp[3*k]; a[3*i+1]=trailRamp[3*k+1]; a[3*i+2]=trailRamp[3*k+2];
    }
    col.needsUpdate=true;
  }
  function buildTrail() {
    disposeTrail();
    if (!trailCourse||trailStyle==='off'||!bounds) return;
    const size=Math.max(20,Math.hypot(bounds.max[0]-bounds.min[0],bounds.max[1]-bounds.min[1])), lift=Math.max(.4,size*.003);
    const out=[], when=[]; const at=(x,y)=>[x*.001,y*.001,(groundZ(x,y)+lift)*.001];
    let now=0;
    const tri=(a,b,c)=>{out.push(...a,...b,...c); when.push(now,now,now);};
    const end=t=>trailEnds.push({t,count:out.length/3});
    const disc=(cx,cy,r,n=14)=> {
      const p=k=>{const a=2*Math.PI*k/n; return at(cx+r*Math.cos(a),cy+r*Math.sin(a));};
      const mid=at(cx,cy); for (let k=0;k<n;k++) tri(mid,p(k),p(k+1));
    };
    const {times,path,prints}=trailCourse;
    trailT0=times.length?times[0]:0;
    if (trailStyle==='footprints') {
      (prints||[]).forEach(f=>{now=f.t; disc(f.p[0],f.p[1],Math.max(1.5,f.w*.45)); end(f.t);});
    } else if (trailStyle==='dots') {
      const step=size*.22, r=Math.max(1.5,size*.025); let since=Infinity;
      path.forEach((p,i)=> {
        now=times[i];
        if (i) since+=Math.hypot(p[0]-path[i-1][0],p[1]-path[i-1][1]);
        if (since>=step) {disc(p[0],p[1],r,12); since=0;}
        end(times[i]);
      });
    } else {
      // A flat strip along the course, its width the style's; a dashed one leaves every other dash out.
      const half=(trailStyle==='ribbon'?size*.18:Math.max(1.5,size*.012)), dash=size*.1;
      const side=i=> {
        const a=path[Math.max(0,i-1)], b=path[Math.min(path.length-1,i+1)], dx=b[0]-a[0], dy=b[1]-a[1], n=Math.hypot(dx,dy);
        return n>1e-6?[-dy/n,dx/n]:null;
      };
      let normal=[0,1], run=0;
      const edge=i=> {const s=side(i); if (s) normal=s; return [at(path[i][0]+normal[0]*half,path[i][1]+normal[1]*half),at(path[i][0]-normal[0]*half,path[i][1]-normal[1]*half)];};
      let prev=path.length?edge(0):null;
      if (path.length) end(times[0]);
      for (let i=1;i<path.length;i++) {
        const step=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]), next=edge(i);
        if (trailStyle!=='dashed'||Math.floor(run/dash)%2===0) {
          // The segment's older edge takes the older time, so a ramp runs smoothly along it.
          out.push(...prev[0],...prev[1],...next[1],...prev[0],...next[1],...next[0]);
          when.push(times[i-1],times[i-1],times[i],times[i-1],times[i],times[i]);
        }
        run+=step; prev=next; end(times[i]);
      }
    }
    if (!out.length) return;
    const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(out,3));
    geo.setAttribute('color',new THREE.Float32BufferAttribute(new Float32Array(out.length),3));
    trailTimes=Float32Array.from(when);
    const m=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({vertexColors:true, transparent:true,
      opacity:trailStyle==='ribbon'?TRAIL.ribbon:TRAIL.opacity, depthWrite:false, side:THREE.DoubleSide,
      polygonOffset:true, polygonOffsetFactor:-2, polygonOffsetUnits:-2, toneMapped:false}));
    m.renderOrder=2; m.raycast=()=>{}; trail.add(m);
    applyTrailAt();
  }
  function applyTrailAt() {
    const m=trail.children[0]; if (!m) return;
    let lo=-1, hi=trailEnds.length;
    while (hi-lo>1) {const mid=(lo+hi)>>1; if (trailEnds[mid].t<=trailAt+1e-9) lo=mid; else hi=mid;}
    const count=lo<0?0:trailEnds[lo].count;
    m.geometry.setDrawRange(0,count);
    paintTrail(count);
  }
  // The course: {times_s, path_mm: [[x, y, z]] at each time, prints: [{t, p, w}]}, or null.
  function setTrail(course) {
    trailCourse=course&&Array.isArray(course.path_mm)&&Array.isArray(course.times_s)?
      {times:course.times_s, path:course.path_mm, prints:Array.isArray(course.prints)?course.prints:[]}:null;
    buildTrail(); draw(); return trailEnds.length;
  }
  function setTrailStyle(name) {if (TRAIL_STYLES.includes(name)&&name!==trailStyle) {trailStyle=name; buildTrail(); draw();} return trailStyle;}
  // {mode: 'solid'|'age', solid: '#rrggbb', stops: ['#rrggbb', ...]}, oldest to newest.
  function setTrailColours(c) {
    const hex=v=>/^#[0-9a-f]{6}$/i.test(String(v||''));
    if (c&&(c.mode==='solid'||c.mode==='age')&&hex(c.solid)&&Array.isArray(c.stops)&&c.stops.length>=2&&c.stops.every(hex)) {
      trailColours={mode:c.mode, solid:c.solid, stops:c.stops.slice()}; buildRamp(); if (trail.children[0]) trail.children[0].userData.painted=false; applyTrailAt(); draw();
    }
    return {...trailColours, stops:trailColours.stops.slice()};
  }
  // Shows the trail as far as t seconds; it does not draw: the poses that move the design do.
  function showTrail(t) {trailAt=Number.isFinite(Number(t))?Number(t):Infinity; applyTrailAt(); return trailAt;}
  // Go-to-point targets (ADR-839): the episode's points on the ground, each coloured by its
  // commanded speed (slowest green, fastest orange, over the episode's own range). The point lit
  // now is bright, with a beacon over it; the ones to come are dim; the ones done are faint. A
  // point's disc is the hold's 0.15 m and its outer line the 0.3 m reach; while it is held a ring
  // between them fills clockwise from the top as the hold runs. Beside the model like the trail:
  // it sizes, picks and outlines nothing.
  const targets=new THREE.Group(); targets.renderOrder=3; world.add(targets);
  const TARGET={hold_m:.15, reach_m:.3, ring:[.19,.25], beacon_m:.5, lit:.95, next:.38, done:.1,
                ramp:['#4fd1a5','#ffd166','#ff7a45']};
  let targetCourse=null, targetMarks=[], targetState=null;
  function disposeTargets() {
    targets.children.slice().forEach(g=>{targets.remove(g); g.traverse(o=>{if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose();});});
    targetMarks=[];
  }
  function speedColour(t) {
    const n=TARGET.ramp.length-1, at=Math.min(n-1,Math.floor(t*n)), f=t*n-at;
    return new THREE.Color(TARGET.ramp[at]).lerp(new THREE.Color(TARGET.ramp[at+1]),f);
  }
  function buildTargets() {
    disposeTargets();
    const pts=targetCourse||[]; if (!pts.length) return;
    const speeds=pts.map(p=>p.speed_mps), lo=Math.min(...speeds), hi=Math.max(...speeds);
    pts.forEach((p,i)=> {
      const x=p.xy_m[0]*1000, y=p.xy_m[1]*1000, colour=speedColour(hi>lo?(p.speed_mps-lo)/(hi-lo):1);
      const mat=()=>new THREE.MeshBasicMaterial({color:colour, transparent:true, depthWrite:false, side:THREE.DoubleSide,
        toneMapped:false, polygonOffset:true, polygonOffsetFactor:-3, polygonOffsetUnits:-3});
      const mark=new THREE.Group(); mark.position.set(x*.001,y*.001,(groundZ(x,y)+2)*.001);
      const disc=new THREE.Mesh(new THREE.CircleGeometry(TARGET.hold_m,48),mat());
      const reach=new THREE.Mesh(new THREE.RingGeometry(TARGET.reach_m-.014,TARGET.reach_m,72),mat());
      const track=new THREE.Mesh(new THREE.RingGeometry(TARGET.ring[0],TARGET.ring[1],72),mat());
      const fill=new THREE.Mesh(new THREE.BufferGeometry(),mat());
      const beacon=new THREE.Mesh(new THREE.CylinderGeometry(.012,.012,TARGET.beacon_m,10),mat());
      beacon.rotation.x=Math.PI/2; beacon.position.z=TARGET.beacon_m/2;
      [disc,reach,track,fill,beacon].forEach(m=>{m.raycast=()=>{}; m.renderOrder=3; mark.add(m);});
      targets.add(mark);
      targetMarks.push({disc,reach,track,fill,beacon,hold:p.hold_s>0,filled:-1});
    });
    showTargets(targetState);
  }
  // The episode's points, [{xy_m, speed_mps, hold_s, band}], or null to remove them.
  function setTargets(points) {
    targetCourse=Array.isArray(points)&&points.length?points.map(p=>({...p, xy_m:p.xy_m.slice()})):null;
    targetState=null; buildTargets(); draw(); return targetMarks.length;
  }
  // The state at the time shown, {index, arrived, hold}; it does not draw: the poses do.
  function showTargets(s) {
    targetState=s&&Number.isFinite(Number(s.index))?{index:Number(s.index), arrived:!!s.arrived, hold:Number(s.hold)||0}:null;
    const at=targetState?targetState.index:0;
    targetMarks.forEach((m,i)=> {
      const o=i<at?TARGET.done:i===at?TARGET.lit:TARGET.next;
      m.disc.material.opacity=o; m.reach.material.opacity=i===at?TARGET.lit:o*.8;
      m.beacon.visible=i===at; m.track.visible=i===at&&m.hold; m.track.material.opacity=.22;
      const share=i===at&&targetState&&targetState.arrived&&m.hold?Math.round(Math.max(0,Math.min(1,targetState.hold))*64)/64:0;
      if (share!==m.filled) {
        m.fill.geometry.dispose();
        m.fill.geometry=share>0?new THREE.RingGeometry(TARGET.ring[0],TARGET.ring[1],72,1,Math.PI/2-2*Math.PI*share,2*Math.PI*share):new THREE.BufferGeometry();
        m.filled=share;
      }
      m.fill.visible=share>0; m.fill.material.opacity=TARGET.lit;
    });
    return targetState;
  }
  // Frames every point and the start from above, three-quarter on, for a whole-course look.
  function frameTargets() {
    if (!targetCourse) return null;
    const xs=[0,...targetCourse.map(p=>p.xy_m[0]*1000)], ys=[0,...targetCourse.map(p=>p.xy_m[1]*1000)];
    const min=[Math.min(...xs),Math.min(...ys)], max=[Math.max(...xs),Math.max(...ys)];
    const radius=Math.hypot(max[0]-min[0],max[1]-min[1])/2+400, tanV=Math.tan(camera.fov*Math.PI/360);
    c={yaw:.8,pitch:.95,distance:radius/Math.sin(Math.atan(tanV))*1.05,target:[(min[0]+max[0])/2,(min[1]+max[1])/2,floorZ*1000]};
    draw(); return c;
  }
  // Where the design's feet came down on a rollout (`frames`, each {name: placement}, at `times`):
  // a solid touches down when its lowest point comes within a hair of the ground under it and lifts
  // off when it rises clear (2.5 hairs, so a foot that chatters is one step), and each stance leaves
  // a footfall at its middle frame's contact patch, as wide as the solid's middle extent. A paw, its
  // toes and its shin all brush the ground together, so a footfall near one already kept (within
  // its width, a quarter second apart) is the same one; the solid on the ground most often over
  // the rollout -- the foot itself -- keeps it.
  function footfalls(frames, times) {
    if (!frames.length||!bounds) return [];
    const height=bounds.max[2]-bounds.min[2], hair=Math.max(2,.015*height), q=new THREE.Quaternion(), v=new THREE.Vector3();
    const size=Math.max(20,Math.hypot(bounds.max[0]-bounds.min[0],bounds.max[1]-bounds.min[1]));
    const solids=[];
    meshes.forEach((m,name)=> {
      if (m.userData.world||!m.visible) return;
      const a=m.geometry.attributes.position, step=Math.max(1,Math.floor(a.count/400)), pts=[];
      for (let i=0;i<a.count;i+=step) pts.push([a.getX(i)*1000,a.getY(i)*1000,a.getZ(i)*1000]);
      const b=m.userData.mmBounds, dims=[b.max.x-b.min.x,b.max.y-b.min.y,b.max.z-b.min.z].sort((x,y)=>x-y);
      solids.push({name, pts, w:Math.max(6,Math.min(dims[1],size*.1))});
    });
    const falls=[];
    solids.forEach(s=> {
      // Each frame: the lowest point's gap over the ground, and the patch within a hair of it.
      const contact=frames.map(poses=> {
        const p=poses[s.name]; if (!p) return null;
        q.fromArray(p.rotation_xyzw); let low=Infinity; const world=[];
        s.pts.forEach(pt=>{v.set(pt[0],pt[1],pt[2]).applyQuaternion(q); const w=[v.x+p.position_mm[0],v.y+p.position_mm[1],v.z+p.position_mm[2]]; world.push(w); if (w[2]<low) low=w[2];});
        const patch=world.filter(w=>w[2]<=low+hair), cx=patch.reduce((a,w)=>a+w[0],0)/patch.length, cy=patch.reduce((a,w)=>a+w[1],0)/patch.length;
        return {gap:low-groundZ(cx,cy), x:cx, y:cy};
      });
      const rank=contact.filter(c=>c&&c.gap<hair).length;
      const stance=(a,b)=>{const c=contact[Math.round((a+b)/2)]; falls.push({t:times[a], p:[c.x,c.y], w:s.w, solid:s.name, rank});};
      let start=-1;
      contact.forEach((c,k)=> {
        if (!c) return;
        if (start<0&&c.gap<hair) start=k;
        else if (start>=0&&c.gap>2.5*hair) {stance(start,k-1); start=-1;}
      });
      if (start>=0) stance(start,contact.length-1);
    });
    const kept=[];
    falls.sort((a,b)=>b.rank-a.rank||a.t-b.t).forEach(f=> {
      if (!kept.some(k=>Math.abs(k.t-f.t)<.25&&Math.hypot(k.p[0]-f.p[0],k.p[1]-f.p[1])<Math.max(k.w,f.w)*1.2)) kept.push(f);
    });
    return kept.map(({rank,...f})=>f).sort((a,b)=>a.t-b.t);
  }
  // Exact bounds of the installed solids, in mm simulator coordinates, at each pose set in
  // `frames` (a list of {name: placement}): every vertex of every solid is transformed, so a
  // rotated part's box is its own and not its rotated box's. World geometry the viewport does not
  // draw is posed but sizes nothing. Leaves the last poses applied.
  function boundsOver(frames) {
    const v=new THREE.Vector3();
    return frames.map(poses=> {
      const lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity];
      meshes.forEach((m,n)=> {
        pose(m,poses[n]); if (!m.visible) return;
        m.updateMatrix(); const a=m.geometry.attributes.position;
        for (let i=0;i<a.count;i++) {
          v.fromBufferAttribute(a,i).applyMatrix4(m.matrix);
          const p=[v.x*1000,v.y*1000,v.z*1000];
          for (let j=0;j<3;j++) {if(p[j]<lo[j])lo[j]=p[j]; if(p[j]>hi[j])hi[j]=p[j];}
        }
      });
      return {min:lo,max:hi};
    });
  }
  function setCamera(value) {c=JSON.parse(JSON.stringify(value));draw();}
  // The design's centre at a set of poses, mm: the mean of its shown solids' own box centres, each
  // carried by its pose (a solid the poses leave out keeps its own). One point a solid, so a
  // rollout's every frame costs little; the follow camera's track.
  function centreAt(poses) {
    const v=new THREE.Vector3(), q=new THREE.Quaternion(), sum=[0,0,0]; let n=0;
    meshes.forEach((m,name)=> {
      if (m.userData.world||!m.visible) return;
      const p=poses&&poses[name];
      m.userData.mmBounds.getCenter(v);
      if (p) v.applyQuaternion(q.fromArray(p.rotation_xyzw)).add(new THREE.Vector3(...p.position_mm));
      else v.applyQuaternion(m.quaternion).add(m.position.clone().multiplyScalar(1000));
      sum[0]+=v.x; sum[1]+=v.y; sum[2]+=v.z; n++;
    });
    return n?sum.map(x=>x/n):null;
  }
  // The follow camera (DASHBOARD.md §5): the camera's target and the key light move with a point
  // of the moving design, mm, by its motion since the last call, so the person's own orbit, zoom
  // and pan stay as they set them while the design runs. `snap` puts the target on the point;
  // null lets go. It does not draw: the poses that move the design do.
  let followed=null;
  function followTo(point,snap=false) {
    if (!point) {followed=null; return null;}
    if (snap) c.target=point.slice();
    else if (followed) c.target=c.target.map((x,i)=>x+point[i]-followed[i]);
    followed=point.slice(); aimSun(point);
    return c.target.slice();
  }
  // Simulation seconds on the timer overlay; null hides it (the viewport's resting state).
  function setClock(seconds) {clock=(seconds===null||seconds===undefined)?null:Number(seconds);}
  // The follow rig (DASHBOARD.md §10; the reference's `--shot follow`). `track` is the
  // subject's centre per output frame, mm, sim coordinates. The camera keeps the viewer's yaw and
  // pitch and ONE standoff — the distance at which `subject_height_mm` fills `fraction` of the frame
  // height — so orientation and apparent size are fixed by construction and only the ground
  // parallaxes past. Position and target translate together along a Hann-smoothed copy of the
  // track (symmetric, zero-phase: frame i is a pure function of the track, never of frame i-1);
  // the subject may lead that anchor by `max_drift` of the half-frame in each screen axis before
  // `l·tanh(d/l)` pulls the anchor after it, smoothly, so a whip can never carry the subject out of
  // frame. Returns the per-frame cameras and the declared and measured numbers.
  function follow(track, o={}) {
    const fraction=o.fraction??FOLLOW.fraction, subjectY=o.subject_y??FOLLOW.subject_y, maxDrift=o.max_drift??FOLLOW.max_drift;
    const W=Math.max(0,Math.round(o.smooth_frames??FOLLOW.smooth_frames));
    const height=o.subject_height_mm??(bounds?bounds.max[2]-bounds.min[2]:0);
    if (!(height>0)||!Array.isArray(track)||!track.length||!track.every(p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite))) throw new Error('follow needs a subject height and a finite track');
    const w=canvas.clientWidth||canvas.width, h=canvas.clientHeight||canvas.height;
    const tanV=Math.tan(camera.fov*Math.PI/360), tanH=tanV*w/h, d=height/(2*tanV*Math.max(.001,fraction));
    // Camera basis in sim coordinates (z up) for the fixed yaw and pitch: `dir` from subject to camera.
    const cp=Math.cos(c.pitch), dir=[cp*Math.cos(c.yaw),cp*Math.sin(c.yaw),Math.sin(c.pitch)];
    const right=[-Math.sin(c.yaw),Math.cos(c.yaw),0], up=[-dir[2]*right[1],dir[2]*right[0],right[1]*dir[0]-right[0]*dir[1]];
    const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2], axpy=(a,s,v)=>a.map((x,i)=>x+s*v[i]);
    const anchors=track.map((_,i)=> {
      const acc=[0,0,0]; let sum=0;
      for (let k=Math.max(0,i-W);k<=Math.min(track.length-1,i+W);k++) {const wt=.5*(1+Math.cos(Math.PI*(k-i)/(W+1))); for(let j=0;j<3;j++)acc[j]+=wt*track[k][j]; sum+=wt;}
      return acc.map(x=>x/sum);
    });
    const soft=(v,l)=>l*Math.tanh(v/l), limY=maxDrift*tanV*d, limX=limY*tanH/tanV;
    const floor=(bounds?bounds.min[2]:-Infinity)+60-d*Math.sin(c.pitch);   // the camera never sinks under the mat
    let worst=0, sizeMin=Infinity, sizeMax=0;
    const cameras=anchors.map((anchor,i)=> {
      const off=track[i].map((x,j)=>x-anchor[j]), dy=dot(off,up), dx=dot(off,right);
      let a=axpy(axpy(anchor,dy-soft(dy,limY),up),dx-soft(dx,limX),right);
      a[2]=Math.max(a[2],floor);
      worst=Math.max(worst,Math.abs(soft(dy,limY))/(tanV*d),Math.abs(soft(dx,limX))/(tanH*d));
      const target=axpy(a,-subjectY*tanV*d,up), eye=axpy(target,d,dir);
      const size=height/(2*tanV*Math.hypot(...track[i].map((x,j)=>x-eye[j])));
      sizeMin=Math.min(sizeMin,size); sizeMax=Math.max(sizeMax,size);
      return {yaw:c.yaw,pitch:c.pitch,distance:d,target};
    });
    return {cameras, fraction, subject_height_mm:height, standoff_mm:d, subject_y:subjectY, max_drift:maxDrift,
            smooth_frames:W, worst_drift_ndc:worst, size_min:sizeMin, size_max:sizeMax};
  }
  function modelPixels() {
    // Count model pixels, and box them, against the exact same environment-only render, so
    // a grid cannot turn an empty-model regression green and the overlay is never counted. World
    // geometry is left out of the model render, so a task floor's slab is never counted as the design.
    const world=[...meshes.values()].some(m=>!m.userData.world)?[...meshes.values()].filter(m=>m.userData.world&&m.visible):[];
    world.forEach(m=>{m.visible=false;});
    draw();const gl=renderer.getContext(),W=canvas.width,H=canvas.height,a=new Uint8Array(W*H*4),b=new Uint8Array(a.length);
    gl.readPixels(0,0,W,H,gl.RGBA,gl.UNSIGNED_BYTE,a);
    model.visible=false;paint();gl.readPixels(0,0,W,H,gl.RGBA,gl.UNSIGNED_BYTE,b);
    model.visible=true;world.forEach(m=>{m.visible=true;});draw();let n=0,x0=W,y0=H,x1=-1,y1=-1;
    for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12){n++;const p=i>>2,x=p%W,y=H-1-((p-x)/W);x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
    return {count:n,box:n?[x0,y0,x1,y1]:null,width:W,height:H};
  }
  function nonBackgroundPixels() {return modelPixels().count;}
  // Orbit, pan and zoom by pointer events, so a mouse and a finger drive the same
  // camera (DASHBOARD.md §5): one pointer orbits, shift- or middle-drag pans, two
  // fingers pan by their midpoint and pinch, the wheel zooms. The canvas captures
  // the pointer, so a drag that leaves it still moves the camera, and its
  // `touch-action: none` keeps the page from scrolling.
  const pointers=new Map(); let pinch=0, mid=null, panning=false;
  const zoom=f=>{c.distance=Math.max((bounds?.radius||1)*.2,c.distance*f);};
  const span=()=>{const [a,b]=[...pointers.values()];return Math.hypot(a[0]-b[0],a[1]-b[1]);};
  const centre=()=>{const [a,b]=[...pointers.values()];return [(a[0]+b[0])/2,(a[1]+b[1])/2];};
  // Pan (ADR-561): slide the target in the view plane so the point under the
  // pointer follows it, one canvas pixel being the field of view's mm per pixel at
  // the target's distance. Right and up are the camera's, in the model's z-up frame.
  function pan(dx,dy) {
    const h=canvas.clientHeight||canvas.height||1, mm=2*c.distance*Math.tan(camera.fov*Math.PI/360)/h;
    const sy=Math.sin(c.yaw), cy=Math.cos(c.yaw), sp=Math.sin(c.pitch), cp=Math.cos(c.pitch);
    const right=[-sy,cy,0], up=[-sp*cy,-sp*sy,cp];
    c.target=c.target.map((t,i)=>t-right[i]*dx*mm+up[i]*dy*mm);
  }
  // Picking (orun2 A1, ADR-505): a press and release that barely moved is a click, not an
  // orbit; it names the solid under it, or null, to the page's onPick.
  const raycaster=new THREE.Raycaster(), ndc=new THREE.Vector2(); let onPick=null, press=null, picked=null;
  function pick(x,y) {
    const r=canvas.getBoundingClientRect(); if(!r.width||!r.height) return null;
    draw(); model.updateMatrixWorld(true);
    raycaster.setFromCamera(ndc.set((x-r.left)/r.width*2-1,-((y-r.top)/r.height)*2+1),camera);
    const hit=raycaster.intersectObjects([...meshes.values()].filter(m=>m.visible),false)[0];
    if (!hit) return null;
    for (const [n,m] of meshes) if (m===hit.object) return n;
    return null;
  }
  // Where a solid's box centre lands on the page, in client pixels; null when it is not drawn.
  function screenPoint(name) {
    const m=meshes.get(name); if(!m) return null;
    draw(); model.updateMatrixWorld(true);
    const p=m.geometry.boundingBox.getCenter(new THREE.Vector3()).applyMatrix4(m.matrixWorld).project(camera), r=canvas.getBoundingClientRect();
    return [r.left+(p.x+1)/2*r.width, r.top+(1-p.y)/2*r.height];
  }
  // A point in mm, in a solid's own frame (or the model's, for null), as canvas pixels with
  // [0,0] top left; null when the solid is not drawn or the point is behind the camera. The
  // dimension overlay draws from it, so the anchors are the only thing in model space.
  const projected=new THREE.Vector3();
  function toScreen(name, point) {
    const frame=name===null||name===undefined?model:meshes.get(name);
    if (!frame||!Array.isArray(point)||point.length!==3||!point.every(Number.isFinite)) return null;
    frame.updateMatrixWorld(true);
    projected.fromArray(point).multiplyScalar(.001).applyMatrix4(frame.matrixWorld).project(camera);
    if (projected.z>1||projected.z<-1) return null;
    const w=canvas.clientWidth||canvas.width, h=canvas.clientHeight||canvas.height;
    return [(projected.x+1)/2*w, (1-projected.y)/2*h];
  }
  // The box, in canvas pixels with [0,0] top left, round every drawn vertex of the design at the
  // camera now (world geometry left out); null when nothing is in front of the camera. The hero
  // page frames its shots by it (ADR-677), tighter than a bounding sphere. With `names`, round
  // those parts alone (a close-up, ADR-792).
  function screenBox(names) {
    draw(); model.updateMatrixWorld(true);
    const w=canvas.clientWidth||canvas.width, h=canvas.clientHeight||canvas.height, v=new THREE.Vector3();
    const only=Array.isArray(names)?new Set(names):null;
    let x0=Infinity, y0=Infinity, x1=-Infinity, y1=-Infinity;
    meshes.forEach((m,n)=> {
      if (!m.visible||m.userData.world||(only&&!only.has(n))) return;
      const a=m.geometry.attributes.position;
      for (let i=0;i<a.count;i++) {
        v.fromBufferAttribute(a,i).applyMatrix4(m.matrixWorld).project(camera);
        if (v.z>1||v.z<-1) continue;
        const x=(v.x+1)/2*w, y=(1-v.y)/2*h;
        if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y;
      }
    });
    return x1>=x0?[x0,y0,x1,y1]:null;
  }
  // The selection glows in the page's --select; [] clears it. Never set by a capture. World
  // geometry is never selected. highlight(name) selects that one part (or none) and returns it.
  const SELECT={glow:0x0c1e36, tint:0xc8dcf6};
  function applySelection() {
    const on=new Set(selectedNames);
    meshes.forEach((m,n)=> {
      const {parts:p, matcap:t}=m.userData.materials;
      p.emissive.setHex(on.has(n)?SELECT.glow:0); t.color.setHex(on.has(n)?SELECT.tint:0xffffff);
    });
    picked=selectedNames.length?selectedNames[selectedNames.length-1]:null;
    applyHeat();
  }
  // The heat view (ADR-727; each viewport's Activations switch, ADR-770): a map of part name to
  // colour paints those parts in it, lit from within a little so a dark part still reads, and
  // every other part a quiet grey so the heat stands out; null gives every part its own colour
  // back. Over the selection, which still glows where it is.
  const HEAT={rest:0x4a4e56, glow:.32};
  let heat=null;
  function applyHeat() {
    const on=new Set(selectedNames), c=new THREE.Color();
    meshes.forEach((m,n)=> {
      if (m.userData.world) return;
      const {parts:p, matcap:t}=m.userData.materials, h=heat&&heat[n];
      if (!heat) { p.color.copy(m.userData.board||m.userData.tinted?c.setHex(0xffffff):m.userData.colour); p.vertexColors=!!(m.userData.board||m.userData.tinted); return; }
      p.color.setHex(h==null?HEAT.rest:h); p.vertexColors=false; t.color.setHex(h==null?HEAT.rest:h);
      if (h!=null&&!on.has(n)) p.emissive.setHex(h).multiplyScalar(HEAT.glow);
    });
  }
  function setHeat(map) {
    const had=!!heat; heat=map&&typeof map==='object'?map:null;
    if (had!==!!heat) meshes.forEach(m=>{if(!m.userData.world) m.userData.materials.parts.needsUpdate=true;});
    applySelection(); draw(); return !!heat;
  }
  function select(names) {
    const seen=new Set();
    selectedNames=(Array.isArray(names)?names:[]).filter(n=>meshes.has(n)&&!meshes.get(n).userData.world&&!seen.has(n)&&seen.add(n));
    applySelection(); draw(); return selectedNames.slice();
  }
  function highlight(name) {select(meshes.has(name)?[name]:[]); return picked;}
  // Hide the named parts and show every other (ADR-676): the page's outliner. World geometry
  // stays as ADR-600 has it. Returns the names hidden that are in the model.
  function setHidden(names) {
    hiddenNames.clear(); (Array.isArray(names)?names:[]).forEach(n=>hiddenNames.add(String(n)));
    meshes.forEach((m,n)=>{if(!m.userData.world) m.visible=!hiddenNames.has(n);});
    draw(); return [...meshes.keys()].filter(n=>hiddenNames.has(n)&&!meshes.get(n).userData.world);
  }
  // The parts as the outliner lists them, in the model's order, world geometry left out.
  function parts() {
    return [...meshes].filter(([,m])=>!m.userData.world).map(([n,m])=>({name:n, visible:m.visible, selected:selectedNames.includes(n),
      finish:m.userData.finish, colour:'#'+m.userData.colour.getHexString(), triangles:m.geometry.attributes.position.count/3}));
  }
  // The named parts' box at their poses now, mm, as `bounds` is; null when none is there.
  function boundsOf(names) {
    const box=new THREE.Box3(), v=new THREE.Vector3();
    (names||[]).forEach(n=> {
      const m=meshes.get(n); if (!m||m.userData.world) return;
      m.updateMatrix(); const a=m.geometry.attributes.position;
      for (let i=0;i<a.count;i++) box.expandByPoint(v.fromBufferAttribute(a,i).applyMatrix4(m.matrix).multiplyScalar(1000));
    });
    if (box.isEmpty()) return null;
    const min=box.min.toArray(), max=box.max.toArray();
    return {min,max,center:min.map((x,i)=>(x+max[i])/2)};
  }
  // Frame the named parts at their poses now, keeping the view's direction. False when none is there.
  function fitTo(names) {
    const box=new THREE.Box3(), v=new THREE.Vector3();
    (names||[]).forEach(n=> {
      const m=meshes.get(n); if (!m) return;
      m.updateMatrix(); const a=m.geometry.attributes.position;
      for (let i=0;i<a.count;i++) box.expandByPoint(v.fromBufferAttribute(a,i).applyMatrix4(m.matrix).multiplyScalar(1000));
    });
    if (box.isEmpty()) return false;
    const w=canvas.clientWidth||canvas.width,h=canvas.clientHeight||canvas.height,tanV=Math.tan(camera.fov*Math.PI/360);
    const half=Math.min(Math.atan(tanV),Math.atan(tanV*Math.min(1,w/h))), radius=Math.max(1,box.getSize(v).length()/2);
    c={yaw:c.yaw,pitch:c.pitch,distance:radius/Math.sin(half)*1.15,target:box.getCenter(v).toArray()};
    draw(); return true;
  }
  // The look (ADR-676): a lighting setup lights the physical materials from its room, its key and
  // its fill; a matcap puts every part in the one baked material. Unknown names keep the look.
  function applyLook() {
    const matcap=MATCAPS.includes(look), lighting=LIGHTING[matcap?'studio':look];
    envMap=looks.environment(matcap?'studio':look);
    const texture=matcap?looks.matcap(look):null;
    keyDir=lighting.key.dir; environment.setLighting(lighting);
    renderer.toneMappingExposure=lighting.exposure*STAGE_EXPOSURE;
    meshes.forEach(m=> {
      const {parts:p, matcap:t}=m.userData.materials;
      if (p.envMap!==envMap) {p.envMap=envMap; p.needsUpdate=true;}
      p.envMapIntensity=m.userData.env*reflections*lighting.env;
      if (t.matcap!==texture) {t.matcap=texture; t.needsUpdate=true;}
      m.material=matcap&&texture?t:p;
    });
    if (bounds) frameBounds(bounds);
    if (followed) aimSun(followed);
  }
  // The lens, as a vertical field of view in degrees (the viewport's is FOV): the hero page
  // shoots its product shots longer (ADR-677), so a design keeps its proportions.
  function setFov(degrees) {const d=Number(degrees); if (Number.isFinite(d)&&d>=10&&d<=90) {camera.fov=d; staged=''; draw();} return camera.fov;}
  function setLook(name) {if (LOOKS.includes(name)) {look=name; applyLook();} draw(); return look;}
  function setOcclusion(flag) {occluded=!!flag; draw(); return occluded;}
  function setDetail(flag) {detailed=!!flag; detailSwitch.value=detailed?1:0; draw(); return detailed;}
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);press=pointers.size===1?[e.clientX,e.clientY]:null;panning=pointers.size===1&&(e.shiftKey||e.button===1);if(pointers.size===2){pinch=span();mid=centre();}e.preventDefault();});
  canvas.addEventListener('pointermove',e=>{
    const p=pointers.get(e.pointerId);if(!p)return;
    if(press&&Math.hypot(e.clientX-press[0],e.clientY-press[1])>=5)press=null;
    if(pointers.size===1&&panning)pan(e.clientX-p[0],e.clientY-p[1]);
    else if(pointers.size===1){const lim=Math.max(1.5,Math.abs(c.pitch));c.yaw-=(e.clientX-p[0])*.01;c.pitch=Math.max(-lim,Math.min(lim,c.pitch+(e.clientY-p[1])*.01));}
    pointers.set(e.pointerId,[e.clientX,e.clientY]);
    if(pointers.size===2){const s=span(),m=centre();if(mid)pan(m[0]-mid[0],m[1]-mid[1]);if(s>0&&pinch>0)zoom(pinch/s);pinch=s;mid=m;}
    draw();
  });
  const lift=e=>{
    if (e.type==='pointerup'&&press&&pointers.size===1&&Math.hypot(e.clientX-press[0],e.clientY-press[1])<5&&onPick) onPick(pick(e.clientX,e.clientY),{add:e.shiftKey||e.ctrlKey||e.metaKey});
    press=null; pointers.delete(e.pointerId);pinch=0;mid=null;panning=false;
  };
  canvas.addEventListener('pointerup',lift);canvas.addEventListener('pointercancel',lift);
  canvas.addEventListener('mousedown',e=>{if(e.button===1)e.preventDefault();});  // no middle-click autoscroll
  canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(e.deltaY*.0015));draw();},{passive:false});
  window.addEventListener('resize',draw);
  // The reflections' strength: a multiple (0..REFLECTIONS.max) of each finish's own.
  function setReflections(value) {
    const v=Number(value); if (Number.isFinite(v)) reflections=Math.max(0,Math.min(REFLECTIONS.max,v));
    const lighting=LIGHTING[MATCAPS.includes(look)?'studio':look];
    meshes.forEach(m=>{m.userData.materials.parts.envMapIntensity=m.userData.env*reflections*lighting.env;}); draw(); return reflections;
  }
  applyLook();
  return {available:true,load,install,clear,fit,draw,setPoses,setTrail,setTrailStyle,setTrailColours,showTrail,setTargets,showTargets,frameTargets,targets:()=>({points:targetMarks.length,state:targetState}),footfalls,trail:()=>({style:trailStyle,at:trailAt,stops:trailEnds.length,shown:trail.children[0]?trail.children[0].geometry.drawRange.count:0}),centreAt,followTo,setGhost,loadGhost,boundsOver,frameBounds,setCamera,setClock,follow,modelPixels,nonBackgroundPixels,setProxies,showProxies,setTerrain,groundAt,
    setSection,setLines,showLines,setStyle,style:()=>style,setMeshLines,meshLines:()=>({...meshLines}),setReflections,reflections:()=>reflections,
    setLook,look:()=>look,setFov,setOcclusion,occlusion:()=>occluded,setDetail,detail:()=>detailed,
    setHidden,hidden:()=>[...hiddenNames],select,setHeat,heat:()=>heat&&{...heat},selected:()=>selectedNames.slice(),parts,boundsOf,fitTo,
    pick,screenPoint,screenBox,toScreen,setOnDraw:fn=>{onDraw=typeof fn==='function'?fn:null;},highlight,picked:()=>picked,setOnPick:fn=>{onPick=typeof fn==='function'?fn:null;},
    camera:()=>JSON.parse(JSON.stringify(c)),stats:()=>({available:true,components:meshes.size,triangles:triangleCount,bounds,outlined:[...meshes.values()].filter(m=>m.userData.outline).length,
      world:[...meshes].filter(([,m])=>m.userData.world).map(([n])=>n),style:STYLE,render_style:style,stage,showing:showing(),
      proxies:{shown:proxiesShown,drawn:proxiesDrawn,listed:proxyGeoms.length}, ghost:ghost.children.map(m=>m.name),
      colours:Object.fromEntries([...meshes].map(([n,m])=>[n,'#'+m.userData.colour.getHexString()])),
      hidden_world:[...meshes].filter(([,m])=>m.userData.world&&!m.visible).map(([n])=>n),
      floor:{z_mm:floorZ*1000, source:floorSource, pitch_mm:(stage?.pitch??1)*1000, centre_mm:stageFloor.centre.map(v=>v*1000), size_mm:stageFloor.roomSize*1000},
      terrain:terrain&&{kind:terrain.kind, boxes:(terrain.boxes||[]).length, domes:(terrain.domes||[]).length, course:terrain.course||null,
        surface:{meshes:ground.children.length, columns:surface.xs.length, rows:surface.ys.length, triangles:2*(surface.xs.length-1)*(surface.ys.length-1),
          x_range_mm:[surface.xs[0],surface.xs.at(-1)], y_range_mm:[surface.ys[0],surface.ys.at(-1)]}},
      clip:{near:camera.near, far:camera.far},
      finishes:Object.fromEntries([...meshes].map(([n,m])=>[n,m.userData.finish])),
      boards:Object.fromEntries([...meshes].filter(([,m])=>m.userData.board).map(([n,m])=>[n,{...m.userData.board}])),
      reflections:{strength:reflections, environment:!!envMap},
      look:{name:look, occlusion:occluded, detail:detailed, matcap:MATCAPS.includes(look)&&!!looks.matcap(look)},
      hidden:[...meshes].filter(([,m])=>!m.userData.world&&!m.visible).map(([n])=>n), selected:selectedNames.slice(),
      mesh_lines:{...meshLines, drawn:meshLineCount()},
      section:section&&{...section}, leaders:{drawn:leaders?leaders.geometry.attributes.position.count/2:0,shown:!!(leaders&&leaders.visible)},
      poses:Object.fromEntries([...meshes].map(([n,m])=>[n,{position_mm:m.position.toArray().map(v=>v*1000),rotation_xyzw:m.quaternion.toArray()}]))}),
    png:()=>{draw();return canvas.toDataURL('image/png').split(',')[1];}};
}
