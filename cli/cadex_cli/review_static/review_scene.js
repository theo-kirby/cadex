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
// The timer overlay (REVIEW-DESIGN.md §10): the reference's caption pill, bottom left, drawn
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
// Collision proxies (REVIEW-DESIGN.md §11): the simulation's contact shapes, drawn as outlines in
// the page's `--warn` through the solids, and only while the labelled toggle is on. Never in a
// recording, never by default: what the viewer shows is the tessellated solid.
const PROXY = {color:0xffe08a, opacity:.9};

export function create(canvas) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true}); }
  catch (_) { return {available:false, clear(){}, fit(){}, load(){return Promise.reject(new Error('WebGL unavailable'));}, stats(){return {available:false, components:0, triangles:0, showing:'nothing drawn', proxies:{shown:false,drawn:0,listed:0}};}, setProxies(){}, showProxies(){return false;}}; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
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
  function paint() {
    renderer.render(scene,camera);
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
    // Bounds in model-local simulator coordinates, not the rotated scene.
    const box = new THREE.Box3();
    meshes.forEach(m=> {m.updateMatrix(); const matrix=m.matrix.clone(); matrix.elements[12]*=1000;matrix.elements[13]*=1000;matrix.elements[14]*=1000; const b=m.userData.mmBounds.clone().applyMatrix4(matrix);box.union(b);});
    if (box.isEmpty()) {bounds=null; return;}
    const min=box.min.toArray(), max=box.max.toArray();
    bounds={min,max,center:min.map((v,i)=>(v+max[i])/2),radius:Math.hypot(...min.map((v,i)=>max[i]-v))/2 || 1};
  }
  function frameBounds(b) {
    bounds=JSON.parse(JSON.stringify(b)); floorZ=b.min[2]/1000 - Math.max(b.radius/1000*1e-5,1e-7);
    const focus=new THREE.Vector3(b.center[0]/1000,b.center[2]/1000,-b.center[1]/1000);
    sun.target.position.copy(focus); sun.position.copy(focus).add(new THREE.Vector3(...KEY_DIR).normalize().multiplyScalar(20));
    const h=Math.max(.01,b.radius/1000*1.2);
    Object.assign(sun.shadow.camera,{left:-h,right:h,top:h,bottom:-h,near:.1,far:40+h*2});
    sun.shadow.camera.updateProjectionMatrix(); sun.shadow.normalBias=h/2048;
    staged='';
  }
  function draw() {
    const w=canvas.clientWidth||canvas.width,h=canvas.clientHeight||canvas.height;
    if (renderer.domElement.width!==Math.floor(w*renderer.getPixelRatio()) || renderer.domElement.height!==Math.floor(h*renderer.getPixelRatio())) renderer.setSize(w,h,false);
    camera.aspect=w/h;
    const d=c.distance/1000, t=c.target.map(x=>x/1000), cp=Math.cos(c.pitch);
    camera.position.set(t[0]+d*cp*Math.cos(c.yaw),t[2]+d*Math.sin(c.pitch),-t[1]-d*cp*Math.sin(c.yaw));
    camera.lookAt(t[0],t[2],-t[1]); camera.near=Math.max(.00001,(bounds?.radius||1)/1000*.001); camera.far=Math.max(800,d*60);
    camera.updateProjectionMatrix();
    const key=JSON.stringify([d,w/h,floorZ]);
    if (key!==staged) {stage=environment.setStage({camDist:d, floorZ}); staged=key;}
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
    disposeProxies(); proxyGeoms=[];
    meshes.forEach(m=> {model.remove(m); m.geometry.dispose();m.material.dispose();});
    meshes.clear(); bounds=null;triangleCount=0;draw();
  }
  // The proxies to offer: the manifest's `collision.geoms`, each in its component's frame.
  // They are built against the installed solids and stay hidden until showProxies(true).
  function setProxies(geoms) {proxyGeoms=Array.isArray(geoms)?geoms.map(g=>JSON.parse(JSON.stringify(g))):[]; buildProxies(); draw();}
  function showProxies(flag) {proxiesShown=!!flag; proxyLines.forEach(l=>{l.visible=proxiesShown;}); draw(); return proxiesShown;}
  function showing() {return proxiesShown&&proxiesDrawn?'tessellated solids with collision proxies':'tessellated solids';}
  function install(entries) {
    clear();
    entries.forEach((entry,i)=> {
      const g=new THREE.BufferGeometry();
      g.setAttribute('position',new THREE.Float32BufferAttribute(entry.positions.map(v=>v*.001),3));
      g.computeVertexNormals();g.computeBoundingBox();
      const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:PALETTE[i%PALETTE.length],roughness:.72,metalness:.05,side:THREE.DoubleSide}));
      m.userData.mmBounds=new THREE.Box3().setFromArray(entry.positions);
      m.castShadow=true;m.receiveShadow=true;pose(m,entry.placement);
      meshes.set(entry.name,m);model.add(m);triangleCount+=entry.positions.length/9;
    });
    updateBounds();if(bounds)frameBounds(bounds);fit();
    return entries.map((e,i)=>({name:e.name,triangles:e.positions.length/9,color:[16,8,0].map(shift=>(PALETTE[i%PALETTE.length]>>shift)&255)}));
  }
  async function load(manifest,fetchImpl=window.fetch.bind(window)) {
    const entries=await Promise.all((manifest?.components||[]).filter(e=>e.mesh).map(async e=> {
      const r=await fetchImpl(e.mesh);if(!r.ok)throw new Error('mesh HTTP '+r.status);
      return {...e, positions:parseStl(await r.arrayBuffer())};
    }));
    return install(entries);
  }
  function setPoses(poses) {meshes.forEach((m,n)=>pose(m,poses[n]));draw();}
  // Exact bounds of the installed solids, in mm simulator coordinates, at each pose set in
  // `frames` (a list of {name: placement}): every vertex of every solid is transformed, so a
  // rotated part's box is its own and not its rotated box's. Leaves the last poses applied.
  function boundsOver(frames) {
    const v=new THREE.Vector3();
    return frames.map(poses=> {
      const lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity];
      meshes.forEach((m,n)=> {
        pose(m,poses[n]); m.updateMatrix(); const a=m.geometry.attributes.position;
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
  // The follow rig (REVIEW-DESIGN.md §10; the reference's `--shot follow`). `track` is the
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
    // a grid cannot turn an empty-model regression green and the overlay is never counted.
    draw();const gl=renderer.getContext(),W=canvas.width,H=canvas.height,a=new Uint8Array(W*H*4),b=new Uint8Array(a.length);
    gl.readPixels(0,0,W,H,gl.RGBA,gl.UNSIGNED_BYTE,a);
    model.visible=false;paint();gl.readPixels(0,0,W,H,gl.RGBA,gl.UNSIGNED_BYTE,b);
    model.visible=true;draw();let n=0,x0=W,y0=H,x1=-1,y1=-1;
    for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12){n++;const p=i>>2,x=p%W,y=H-1-((p-x)/W);x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
    return {count:n,box:n?[x0,y0,x1,y1]:null,width:W,height:H};
  }
  function nonBackgroundPixels() {return modelPixels().count;}
  // Orbit and zoom by pointer events, so a mouse and a finger drive the same
  // camera (REVIEW-DESIGN.md §5): one pointer orbits, two pinch, the wheel
  // zooms. The canvas captures the pointer, so a drag that leaves it still
  // orbits, and its `touch-action: none` keeps the page from scrolling.
  const pointers=new Map(); let pinch=0;
  const zoom=f=>{c.distance=Math.max((bounds?.radius||1)*.2,c.distance*f);};
  const span=()=>{const [a,b]=[...pointers.values()];return Math.hypot(a[0]-b[0],a[1]-b[1]);};
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);if(pointers.size===2)pinch=span();e.preventDefault();});
  canvas.addEventListener('pointermove',e=>{
    const p=pointers.get(e.pointerId);if(!p)return;
    if(pointers.size===1){c.yaw-=(e.clientX-p[0])*.01;c.pitch=Math.max(-1.5,Math.min(1.5,c.pitch+(e.clientY-p[1])*.01));}
    pointers.set(e.pointerId,[e.clientX,e.clientY]);
    if(pointers.size===2){const s=span();if(s>0&&pinch>0)zoom(pinch/s);pinch=s;}
    draw();
  });
  const lift=e=>{pointers.delete(e.pointerId);pinch=0;};
  canvas.addEventListener('pointerup',lift);canvas.addEventListener('pointercancel',lift);
  canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(e.deltaY*.0015));draw();},{passive:false});
  window.addEventListener('resize',draw);
  return {available:true,load,install,clear,fit,draw,setPoses,boundsOver,frameBounds,setCamera,setClock,follow,modelPixels,nonBackgroundPixels,setProxies,showProxies,
    camera:()=>JSON.parse(JSON.stringify(c)),stats:()=>({available:true,components:meshes.size,triangles:triangleCount,bounds,style:STYLE,stage,showing:showing(),
      proxies:{shown:proxiesShown,drawn:proxiesDrawn,listed:proxyGeoms.length}}),
    png:()=>{draw();return canvas.toDataURL('image/png').split(',')[1];}};
}
