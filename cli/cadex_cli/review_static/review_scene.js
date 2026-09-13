// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
// Common inspection/capture scene. Public poses, bounds and cameras are mm,
// Z-up, xyzw. One uniform conversion to metres; no component enlargement.
import * as THREE from './three.module.js';
import {createEnvironment, KEY_DIR} from './environment.js';
import {parseStl} from './stl.js';
export const STYLE = 'cadex-prototype-light-v1';
const PALETTE = [0x5b9dcd, 0xde8f47, 0x6ab270, 0xc468b4, 0xdcc85a, 0x7878c8, 0xc86e6e, 0x6ebebe];

export function create(canvas) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true}); }
  catch (_) { return {available:false, clear(){}, fit(){}, load(){return Promise.reject(new Error('WebGL unavailable'));}, stats(){return {available:false, components:0, triangles:0};}}; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  const scene = new THREE.Scene(), world = new THREE.Group(), model = new THREE.Group();
  world.rotation.x = -Math.PI/2; scene.add(world); world.add(model);
  const camera = new THREE.PerspectiveCamera(55, 1, .0001, 800);
  const hemi = new THREE.HemisphereLight(0xffffff, 0xbfc4cc, 2.2);
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.castShadow = true; sun.shadow.mapSize.set(2048,2048);
  const fill = new THREE.DirectionalLight(0xdfe6ff,1.1); fill.position.set(-12,6,-9);
  scene.add(hemi, sun, sun.target, fill);
  const environment = createEnvironment({scene,world,camera,renderer,lights:{hemi,sun,fill}}, {labels:true});
  let bounds=null, triangleCount=0, staged='', stage=null;
  let c={yaw:.8,pitch:.5,distance:100,target:[0,0,0]}, floorZ=0;
  const meshes = new Map();
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
    renderer.render(scene,camera);
  }
  function fit() {
    if (!bounds) return;
    c={yaw:.8,pitch:.5,distance:bounds.radius/Math.sin(55*Math.PI/360)*1.15,target:bounds.center.slice()};
    draw();
  }
  function clear() {
    meshes.forEach(m=> {model.remove(m); m.geometry.dispose();m.material.dispose();});
    meshes.clear(); bounds=null;triangleCount=0;draw();
  }
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
  function setCamera(value) {c=JSON.parse(JSON.stringify(value));draw();}
  function nonBackgroundPixels() {
    // Count model pixels against the exact same environment-only render, so
    // a grid cannot turn an empty-model regression green.
    draw();const gl=renderer.getContext(),a=new Uint8Array(canvas.width*canvas.height*4),b=new Uint8Array(a.length);
    gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,a);
    model.visible=false;renderer.render(scene,camera);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,b);
    model.visible=true;draw();let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12)n++;return n;
  }
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
  return {available:true,load,install,clear,fit,draw,setPoses,frameBounds,setCamera,nonBackgroundPixels,
    camera:()=>JSON.parse(JSON.stringify(c)),stats:()=>({available:true,components:meshes.size,triangles:triangleCount,bounds,style:STYLE,stage}),
    png:()=>{draw();return canvas.toDataURL('image/png').split(',')[1];}};
}
