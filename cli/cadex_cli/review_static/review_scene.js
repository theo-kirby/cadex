// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
// Common inspection/capture scene. Public poses, bounds and cameras are mm,
// Z-up, xyzw. One uniform conversion to metres; no component enlargement.
import * as THREE from './three.module.js';
import {createEnvironment, KEY_DIR} from './environment.js';
import {parseStl} from './stl.js';
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
// Section and explode (DASHBOARD.md §24). A section clips the solids at the plane and offset of
// the `cadex section` cut it shows, keeping the side below the offset; the leader lines are the
// engine's exploded-view segments, in the page's `--muted`.
const SECTION_NORMALS = {XY:[0,0,1], XZ:[0,1,0], YZ:[1,0,0]};
const LEADER = {color:0x9aa3ad, opacity:.85};
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
export const MESH_LINES = {angle:2, strength:.22, max:1};
// Smooth shading (ADR-601): a vertex normal averages the facets around it that turn by less than
// the engine's CREASE_DEGREES (CadexStudio.py), so a fillet or a bore reads smooth and an edge
// that turns further stays crisp.
export const CREASE_DEGREES = 40;
// Physical finishes (ADR-601), keyed by the manifest's `finish` (and, for hardware, its catalog
// family). The role colour stays the base colour; a finish only says how the surface takes light.
// `colour` is the fallback when a part carries none; `env` is how much of the studio it reflects
// (a metal is mostly reflection; a plastic mostly its own colour under the lights).
export const FINISHES = {
  printed:  {roughness:.55, metalness:0, clearcoat:.08, clearcoatRoughness:.5, sheen:.2, sheenRoughness:.6, env:.4},
  purchased:{roughness:.42, metalness:0, clearcoat:.1, clearcoatRoughness:.35, env:.45},
  board:    {roughness:.45, metalness:0, clearcoat:.3, clearcoatRoughness:.3, env:.45, colour:'#1f6b3c'},
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

// A small procedural studio for reflections (ADR-601): a dim box room, y up, lit by a large soft
// panel overhead, a key panel to one side, a cooler fill and a rim behind, prefiltered once into
// a PMREM. Nothing of it is drawn; the solids only see it in their reflections and ambient light.
function studioEnvironment(renderer) {
  const room=new THREE.Scene(), box=new THREE.BoxGeometry(1,1,1), made=[];
  const add=(colour,intensity,scale,position,side=THREE.FrontSide)=> {
    const m=new THREE.MeshBasicMaterial({color:new THREE.Color(colour).multiplyScalar(intensity),side,toneMapped:false});
    const mesh=new THREE.Mesh(box,m); mesh.scale.set(...scale); mesh.position.set(...position); room.add(mesh); made.push(m);
  };
  add(0x9a9a9a,.35,[16,9,16],[0,3.5,0],THREE.BackSide);    // walls, ceiling and floor
  add(0x202020,1,[16,.1,16],[0,-.9,0]);                    // a darker floor, so the lower half reads as ground
  add(0xffffff,3.5,[6,.1,4],[0,7.8,0]);                     // the overhead softbox
  add(0xfff4e8,9,[.1,3,4],[-7.8,3,1.5]);                    // key, warm, to one side
  add(0xdfe8ff,3.5,[.1,2.4,5],[7.8,2.5,-1]);                // fill, cool, opposite
  add(0xffffff,6,[5,1.6,.1],[0,3.5,-7.8]);                  // rim strip behind
  const pmrem=new THREE.PMREMGenerator(renderer), target=pmrem.fromScene(room,.03);
  pmrem.dispose(); box.dispose(); made.forEach(m=>m.dispose());
  return target.texture;
}

export function create(canvas) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true}); }
  catch (_) { return {available:false, clear(){}, fit(){}, load(){return Promise.reject(new Error('WebGL unavailable'));}, stats(){return {available:false, components:0, triangles:0, showing:'nothing drawn', proxies:{shown:false,drawn:0,listed:0}};}, setProxies(){}, showProxies(){return false;}, setSection(){return null;}, setLines(){return 0;}, showLines(){return false;}, setPoses(){}, setGhost(){return 0;}, loadGhost(){return Promise.resolve(0);}, toScreen(){return null;}, setOnDraw(){}, setStyle(){return 'shaded';}, style(){return 'shaded';}, setMeshLines(){return {shown:false,strength:0};}, setReflections(){return 0;}, draw(){}}; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene(), world = new THREE.Group(), model = new THREE.Group();
  world.rotation.x = -Math.PI/2; scene.add(world); world.add(model);
  const camera = new THREE.PerspectiveCamera(55, 1, .0001, 800);
  // Key, hemisphere and opposite fill; the environment sets their intensities and ground tints
  // from its one dark palette (ADR-331) when it is built over them.
  const hemi = new THREE.HemisphereLight(0xffffff, 0x2a2a2a, 1.6);
  const sun = new THREE.DirectionalLight(0xffffff, 2.7);
  sun.castShadow = true; sun.shadow.mapSize.set(2048,2048);
  const fill = new THREE.DirectionalLight(0xdfe6ff,1.0); fill.position.set(-12,6,-9);
  scene.add(hemi, sun, sun.target, fill);
  const environment = createEnvironment({scene,world,camera,renderer,lights:{hemi,sun,fill}}, {labels:true});
  let envMap=null; try { envMap=studioEnvironment(renderer); } catch (_) { envMap=null; }
  let reflections=REFLECTIONS.strength;
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
    meshes.forEach(m=>{m.material.clippingPlanes=section?[clipPlane]:null; m.material.clipShadows=true; m.material.needsUpdate=true;});
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
  let style='shaded', target=null, edges=null, lineTarget=null;
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
  const resolvePass=new THREE.ShaderMaterial({
    uniforms:{tEdges:{value:null}, tLines:{value:null}, strength:{value:0}, paper:{value:new THREE.Vector3()}, ink:{value:new THREE.Vector3()}},
    vertexShader:fullscreen,
    fragmentShader:`uniform sampler2D tEdges; uniform sampler2D tLines; uniform float strength; uniform vec3 paper, ink; varying vec2 vUv;
      void main(){
        vec3 under=mix(paper,ink,strength*texture2D(tLines,vUv).r);
        gl_FragColor=vec4(mix(under,ink,texture2D(tEdges,vUv).r),1.);
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
      if (target) {target.depthTexture.dispose(); target.dispose(); edges.dispose(); lineTarget.dispose();}
      target=new THREE.WebGLRenderTarget(w,h,{depthTexture:new THREE.DepthTexture(w,h),minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter});
      // Linear filtering at each canvas pixel's centre is the mean of its 2x2 block.
      edges=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,depthBuffer:false});
      lineTarget=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter});
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
    scene.background=background; scene.fog=fog; scene.overrideMaterial=null;
    world.children.forEach((o,i)=>{o.visible=shown[i];});
    const u=edgePass.uniforms;
    u.tNormal.value=target.texture; u.tDepth.value=target.depthTexture;
    u.texel.value.set(1/w,1/h); u.near.value=camera.near; u.far.value=camera.far;
    passQuad.material=edgePass; renderer.setRenderTarget(edges); renderer.render(passScene,passCamera);
    renderer.setRenderTarget(null);
    const r=resolvePass.uniforms;
    r.tEdges.value=edges.texture; r.tLines.value=lineTarget.texture; r.strength.value=lines?meshLines.strength:0;
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
    if (style==='wireframe') {paintWireframe(); if (onDraw) onDraw(); return;}
    renderer.render(scene,camera);
    if (onDraw) onDraw();
    if (clock===null) return;
    paintClock(canvas.clientWidth||canvas.width,canvas.clientHeight||canvas.height);
    renderer.autoClear=false; renderer.clearDepth(); renderer.render(hud,hudCamera); renderer.autoClear=true;
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
    const top=worldTop(), low=b.min[2], slack=Math.max(2,.02*(b.max[2]-b.min[2]));
    floorSource=top===null?'design':top<=low+slack?'world':'design';
    return (floorSource==='world'?top:low)/1000;
  }
  function frameBounds(b) {
    bounds=JSON.parse(JSON.stringify(b)); floorZ=matZ(b);
    const focus=new THREE.Vector3(b.center[0]/1000,b.center[2]/1000,-b.center[1]/1000);
    sun.target.position.copy(focus); sun.position.copy(focus).add(new THREE.Vector3(...KEY_DIR).normalize().multiplyScalar(20));
    const h=Math.max(.01,b.radius/1000*1.2);
    Object.assign(sun.shadow.camera,{left:-h,right:h,top:h,bottom:-h,near:.1,far:40+h*2});
    sun.shadow.camera.updateProjectionMatrix();
    // Two shadow-map texels of normal offset: a flat face lit at a grazing angle no longer
    // shades itself in stripes (acne), and a part still meets its shadow.
    sun.shadow.normalBias=h/512;
    staged='';
  }
  // The camera's clip planes (ADR-600): near is a fixed fraction of the camera's distance, so the
  // depth buffer's precision scales with the shot and the mat never z-fights the design at any
  // zoom; far is the stage's, which follows the floor (environment.js), so the mat never pops.
  const NEAR_FRACTION=.002;
  function draw() {
    const w=canvas.clientWidth||canvas.width,h=canvas.clientHeight||canvas.height;
    if (renderer.domElement.width!==Math.floor(w*renderer.getPixelRatio()) || renderer.domElement.height!==Math.floor(h*renderer.getPixelRatio())) renderer.setSize(w,h,false);
    camera.aspect=w/h;
    const d=c.distance/1000, t=c.target.map(x=>x/1000), cp=Math.cos(c.pitch);
    camera.position.set(t[0]+d*cp*Math.cos(c.yaw),t[2]+d*Math.sin(c.pitch),-t[1]-d*cp*Math.sin(c.yaw));
    camera.lookAt(t[0],t[2],-t[1]);
    const key=JSON.stringify([d,w/h,floorZ]);
    if (key!==staged) {stage=environment.setStage({camDist:d, floorZ}); staged=key;}
    camera.near=Math.min(1,Math.max(1e-5,d*NEAR_FRACTION)); camera.far=Math.max(stage.far,d*4);
    camera.updateProjectionMatrix();
    // The presentation floor is front-sided: orbiting underneath remains a CAD inspection.
    paint();
  }
  function fit() {
    if (!bounds) return;
    // Frame the bounding sphere in the narrower field of view: a canvas at least as wide as it is tall frames by
    // the vertical one (as it always has), a portrait one — a stage between two wide sidebars — by the horizontal.
    const w=canvas.clientWidth||canvas.width,h=canvas.clientHeight||canvas.height,tanV=Math.tan(55*Math.PI/360);
    const half=Math.min(Math.atan(tanV),Math.atan(tanV*Math.min(1,w/h)));
    c={yaw:.8,pitch:.5,distance:bounds.radius/Math.sin(half)*1.15,target:bounds.center.slice()};
    draw();
  }
  function clear() {
    disposeProxies(); proxyGeoms=[]; setLines([]);
    meshes.forEach(m=> {
      model.remove(m); m.geometry.dispose(); m.material.dispose(); m.userData.meshLines?.geometry.dispose();
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
      sheen:f.sheen||0, sheenRoughness:f.sheenRoughness||1, sheenColor:0xffffff,
      envMap, envMapIntensity:f.env*reflections, side:THREE.DoubleSide});
    let board=null;
    if (finish==='board'&&entry.board) {
      board=boardColours(entry.positions, entry.board, colour);
      g.setAttribute('color',new THREE.Float32BufferAttribute(board.colours,3));
      m.vertexColors=true; m.color.set(0xffffff);
      board={chip:board.chip, pad:board.pad};
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
      const m=new THREE.Mesh(g,mat);
      m.userData.mmBounds=new THREE.Box3().setFromArray(entry.positions);
      m.userData.world=entry.world===true; m.userData.finish=finish; m.userData.env=FINISHES[finish].env; m.userData.colour=colour; m.userData.board=board;
      m.visible=!hidden;
      m.castShadow=true;m.receiveShadow=true;pose(m,entry.placement);
      meshes.set(entry.name,m);model.add(m);triangleCount+=entry.positions.length/9;
    });
    updateBounds();if(bounds)frameBounds(bounds);applySection();fit();
    return entries.map((e,i)=>({name:e.name,triangles:e.positions.length/9,color:[16,8,0].map(shift=>(colourOf(e,i)>>shift)&255)}));
  }
  async function load(manifest,fetchImpl=window.fetch.bind(window)) {
    const entries=await Promise.all((manifest?.components||[]).filter(e=>e.mesh).map(async e=> {
      const r=await fetchImpl(e.mesh);if(!r.ok)throw new Error('mesh HTTP '+r.status);
      return {...e, positions:parseStl(await r.arrayBuffer())};
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
    const tanV=Math.tan(FOV*Math.PI/360), tanH=tanV*w/h, d=height/(2*tanV*Math.max(.001,fraction));
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
  // The picked solid glows faintly; null clears it. Never set by a capture.
  function highlight(name) {picked=meshes.has(name)?name:null; meshes.forEach((m,n)=>{if(m.material.emissive)m.material.emissive.setHex(n===picked?0x3a3a3a:0);}); draw(); return picked;}
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);press=pointers.size===1?[e.clientX,e.clientY]:null;panning=pointers.size===1&&(e.shiftKey||e.button===1);if(pointers.size===2){pinch=span();mid=centre();}e.preventDefault();});
  canvas.addEventListener('pointermove',e=>{
    const p=pointers.get(e.pointerId);if(!p)return;
    if(press&&Math.hypot(e.clientX-press[0],e.clientY-press[1])>=5)press=null;
    if(pointers.size===1&&panning)pan(e.clientX-p[0],e.clientY-p[1]);
    else if(pointers.size===1){c.yaw-=(e.clientX-p[0])*.01;c.pitch=Math.max(-1.5,Math.min(1.5,c.pitch+(e.clientY-p[1])*.01));}
    pointers.set(e.pointerId,[e.clientX,e.clientY]);
    if(pointers.size===2){const s=span(),m=centre();if(mid)pan(m[0]-mid[0],m[1]-mid[1]);if(s>0&&pinch>0)zoom(pinch/s);pinch=s;mid=m;}
    draw();
  });
  const lift=e=>{
    if (e.type==='pointerup'&&press&&pointers.size===1&&Math.hypot(e.clientX-press[0],e.clientY-press[1])<5&&onPick) onPick(pick(e.clientX,e.clientY));
    press=null; pointers.delete(e.pointerId);pinch=0;mid=null;panning=false;
  };
  canvas.addEventListener('pointerup',lift);canvas.addEventListener('pointercancel',lift);
  canvas.addEventListener('mousedown',e=>{if(e.button===1)e.preventDefault();});  // no middle-click autoscroll
  canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(e.deltaY*.0015));draw();},{passive:false});
  window.addEventListener('resize',draw);
  // The reflections' strength: a multiple (0..REFLECTIONS.max) of each finish's own.
  function setReflections(value) {
    const v=Number(value); if (Number.isFinite(v)) reflections=Math.max(0,Math.min(REFLECTIONS.max,v));
    meshes.forEach(m=>{m.material.envMapIntensity=m.userData.env*reflections;}); draw(); return reflections;
  }
  return {available:true,load,install,clear,fit,draw,setPoses,setGhost,loadGhost,boundsOver,frameBounds,setCamera,setClock,follow,modelPixels,nonBackgroundPixels,setProxies,showProxies,
    setSection,setLines,showLines,setStyle,style:()=>style,setMeshLines,meshLines:()=>({...meshLines}),setReflections,reflections:()=>reflections,
    pick,screenPoint,toScreen,setOnDraw:fn=>{onDraw=typeof fn==='function'?fn:null;},highlight,picked:()=>picked,setOnPick:fn=>{onPick=typeof fn==='function'?fn:null;},
    camera:()=>JSON.parse(JSON.stringify(c)),stats:()=>({available:true,components:meshes.size,triangles:triangleCount,bounds,
      world:[...meshes].filter(([,m])=>m.userData.world).map(([n])=>n),style:STYLE,render_style:style,stage,showing:showing(),
      proxies:{shown:proxiesShown,drawn:proxiesDrawn,listed:proxyGeoms.length}, ghost:ghost.children.map(m=>m.name),
      colours:Object.fromEntries([...meshes].map(([n,m])=>[n,'#'+m.userData.colour.getHexString()])),
      hidden_world:[...meshes].filter(([,m])=>m.userData.world&&!m.visible).map(([n])=>n),
      floor:{z_mm:floorZ*1000, source:floorSource, pitch_mm:(stage?.pitch??1)*1000},
      clip:{near:camera.near, far:camera.far},
      finishes:Object.fromEntries([...meshes].map(([n,m])=>[n,m.userData.finish])),
      boards:Object.fromEntries([...meshes].filter(([,m])=>m.userData.board).map(([n,m])=>[n,{...m.userData.board}])),
      reflections:{strength:reflections, environment:!!envMap},
      mesh_lines:{...meshLines, drawn:meshLineCount()},
      section:section&&{...section}, leaders:{drawn:leaders?leaders.geometry.attributes.position.count/2:0,shown:!!(leaders&&leaders.visible)},
      poses:Object.fromEntries([...meshes].map(([n,m])=>[n,{position_mm:m.position.toArray().map(v=>v*1000),rotation_xyzw:m.quaternion.toArray()}]))}),
    png:()=>{draw();return canvas.toDataURL('image/png').split(',')[1];}};
}
