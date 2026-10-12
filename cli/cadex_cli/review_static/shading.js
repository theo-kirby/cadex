// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
// The shaded viewport's look (ADR-676; docs/DASHBOARD.md §10): how the solids take light.
//
//   Looks      four lighting setups -- Studio (the default, and every capture's), Softbox,
//              Dramatic, Daylight -- and two matcaps, Aluminium and Clay, after Blender's viewport
//              shading. A lighting setup is a procedural room the solids reflect and are lit by
//              (image-based light), plus a key and a fill; a matcap replaces both with one baked
//              sphere, so every part reads as the one material whatever its finish.
//   Occlusion  screen-space ambient occlusion: where two surfaces meet, or a part stands on the
//              mat, less of the room reaches it. Multiplied over the frame after it is drawn.
//   Detail     the surface is not a perfect CAD skin: a printed part shows its layer lines where
//              they are big enough to see (they fade out before they would alias), every finish a
//              faint grain and a slow drift in roughness, so a face no longer reads as one flat value.
import * as THREE from './three.module.js';

export const LOOKS = ['studio', 'softbox', 'dramatic', 'daylight', 'aluminium', 'clay'];
export const MATCAPS = ['aluminium', 'clay'];
export const LOOK_LABELS = {studio:'Studio', softbox:'Softbox', dramatic:'Dramatic', daylight:'Daylight', aluminium:'Aluminium', clay:'Clay'};

// A room is a list of emissive boxes, y up, prefiltered once into a PMREM: [colour, intensity,
// size, position]. Nothing of it is drawn; the solids only see it in their reflections and their
// ambient light. The key and fill are directional lights (`dir`, y up, towards the light); `hemi`
// and `bounce` are the small flat ambient that remains, `floor` how much the mat is lifted so it
// reads alike under every setup, and `exposure` the tone mapper's.
const WALLS = (grey, intensity) => [grey, intensity, [16, 9, 16], [0, 3.5, 0], 'back'];
export const LIGHTING = {
  studio: {
    room: [WALLS(0x8a8a8a, .12), [0x161616, 1, [16, .1, 16], [0, -.9, 0]],
           [0xffffff, 4.2, [6, .1, 4], [0, 7.8, 0]], [0xfff1e2, 7, [.1, 3, 4], [-7.8, 3, 1.5]],
           [0xdfe8ff, 2.2, [.1, 2.4, 5], [7.8, 2.5, -1]], [0xffffff, 5, [5, 1.4, .1], [0, 3.2, -7.8]]],
    key: {colour: 0xfff3e8, intensity: 3, dir: [.75, .9, .55]},
    fill: {colour: 0xdfe6ff, intensity: .35, dir: [-.9, .45, -.7]},
    hemi: .18, bounce: .12, floor: .55, exposure: 1, env: 1,
  },
  softbox: {
    room: [WALLS(0xb4b4b4, .55), [0x3a3a3a, 1, [16, .1, 16], [0, -.9, 0]],
           [0xffffff, 5, [10, .1, 8], [0, 7.8, 0]], [0xffffff, 3, [.1, 5, 8], [-7.8, 3.5, 0]],
           [0xffffff, 3, [.1, 5, 8], [7.8, 3.5, 0]]],
    key: {colour: 0xffffff, intensity: 1.1, dir: [.2, 1, .25]},
    fill: {colour: 0xffffff, intensity: .3, dir: [-.6, .5, -.6]},
    hemi: .45, bounce: .35, floor: .5, exposure: .95, env: 1,
  },
  dramatic: {
    room: [WALLS(0x404040, .05), [0x080808, 1, [16, .1, 16], [0, -.9, 0]],
           [0xffe2c4, 12, [.1, 2.2, 2.6], [-7.8, 1.6, 2.5]], [0xdce6ff, 7, [6, .8, .1], [0, 2.4, -7.8]],
           [0xffffff, .8, [4, .1, 3], [0, 7.8, 0]]],
    key: {colour: 0xffd9b0, intensity: 4.2, dir: [-.95, .55, .5]},
    fill: {colour: 0xd0dcff, intensity: .7, dir: [.2, .5, -1]},
    hemi: .08, bounce: .05, floor: .45, exposure: 1.05, env: 1,
  },
  daylight: {
    room: [WALLS(0x8fa9c8, .55), [0x4a443c, 1, [16, .1, 16], [0, -.9, 0]],
           [0xbcd6ff, 2.4, [16, .1, 16], [0, 7.9, 0]], [0xfff0d8, 40, [.9, .9, .9], [-6.5, 6.2, 3.5]]],
    key: {colour: 0xfff0d8, intensity: 3.4, dir: [-.7, 1.05, .45]},
    fill: {colour: 0xa9c4ff, intensity: .5, dir: [.6, .7, -.5]},
    hemi: .3, bounce: .2, floor: .45, exposure: 1, env: 1,
  },
};
// The matcaps' spheres: a physical material lit by its own room, baked once into a texture.
const MATCAP_SPHERES = {
  aluminium: {colour: 0xdfe3e8, metalness: 1, roughness: .3, clearcoat: 0,
    room: [WALLS(0xc8c8c8, .85), [0x3a3a3a, 1, [16, .1, 16], [0, -.9, 0]],
           [0xffffff, 4, [10, .1, 8], [0, 7.8, 0]], [0xffffff, 3, [16, 1.2, .1], [0, 3.4, 7.9]],
           [0x6a6a6a, 1, [16, .6, .1], [0, 1.2, 7.9]], [0xf2f6ff, 2.5, [.1, 4, 8], [7.8, 3.5, 0]],
           [0xfff8f0, 2.5, [.1, 4, 8], [-7.8, 3.5, 0]]]},
  clay: {colour: 0xc4b9ab, metalness: 0, roughness: .62, clearcoat: .05,
    room: [WALLS(0x9a9a9a, .5), [0x2a2a2a, 1, [16, .1, 16], [0, -.9, 0]],
           [0xffffff, 4, [8, .1, 6], [0, 7.8, 0]], [0xfff4e8, 4, [.1, 4, 6], [-7.8, 4, 4]]]},
};
// Ambient occlusion: the radius is a share of the design's size, but never more than a share of
// the camera's distance, so a close-up does not darken half the frame; `strength` scales it.
export const OCCLUSION = {radius: .12, maxRadius: .08, strength: 1.6, samples: 16, fade: 3};
// Surface detail, per finish. `layer` is the printed layer height (mm); `grain` the micro relief's
// height (mm), `drift` the roughness's slow wander (±) and `tone` the colour's (± a share).
export const DETAIL = {
  printed: {layer: .2, bead: .035, grain: .008, drift: .16, tone: .06},
  purchased: {layer: 0, bead: 0, grain: .005, drift: .1, tone: .03},
  board: {layer: 0, bead: 0, grain: .004, drift: .1, tone: .04},
  metal: {layer: 0, bead: 0, grain: .002, drift: .12, tone: .02},
};

function roomEnvironment(renderer, panels) {
  const room = new THREE.Scene(), box = new THREE.BoxGeometry(1, 1, 1), made = [];
  panels.forEach(([colour, intensity, scale, position, side]) => {
    const m = new THREE.MeshBasicMaterial({color: new THREE.Color(colour).multiplyScalar(intensity),
      side: side === 'back' ? THREE.BackSide : THREE.FrontSide, toneMapped: false});
    const mesh = new THREE.Mesh(box, m); mesh.scale.set(...scale); mesh.position.set(...position);
    room.add(mesh); made.push(m);
  });
  const pmrem = new THREE.PMREMGenerator(renderer), target = pmrem.fromScene(room, .03);
  pmrem.dispose(); box.dispose(); made.forEach(m => m.dispose());
  return target.texture;
}

// One owner of the rooms and matcaps a renderer has built, each built the first time it is asked for.
export function createLooks(renderer) {
  const rooms = new Map(), matcaps = new Map();
  function environment(look) {
    if (!LIGHTING[look]) return null;
    if (!rooms.has(look)) {
      let tex = null; try { tex = roomEnvironment(renderer, LIGHTING[look].room); } catch (_) { tex = null; }
      rooms.set(look, tex);
    }
    return rooms.get(look);
  }
  // A lit physical sphere rendered once into a linear half-float texture, so the frame's tone
  // mapping treats it as it treats the lit solids.
  function matcap(name) {
    const spec = MATCAP_SPHERES[name]; if (!spec) return null;
    if (matcaps.has(name)) return matcaps.get(name);
    let texture = null;
    try {
      const env = roomEnvironment(renderer, spec.room), scene = new THREE.Scene(), size = 512;
      const geometry = new THREE.SphereGeometry(1, 128, 96);
      const material = new THREE.MeshPhysicalMaterial({color: spec.colour, metalness: spec.metalness, roughness: spec.roughness,
        clearcoat: spec.clearcoat, envMap: env, envMapIntensity: 1});
      scene.add(new THREE.Mesh(geometry, material));
      const key = new THREE.DirectionalLight(0xffffff, spec.metalness ? .6 : 1.6); key.position.set(-.6, .9, 1); scene.add(key);
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 10); camera.position.set(0, 0, 4);
      const target = new THREE.WebGLRenderTarget(size, size, {type: THREE.HalfFloatType, colorSpace: THREE.NoColorSpace,
        minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false});
      const previous = renderer.getRenderTarget(), clear = renderer.getClearColor(new THREE.Color()), alpha = renderer.getClearAlpha();
      renderer.setRenderTarget(target); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(scene, camera);
      renderer.setRenderTarget(previous); renderer.setClearColor(clear, alpha);
      geometry.dispose(); material.dispose(); env.dispose();
      texture = target.texture;
    } catch (_) { texture = null; }
    matcaps.set(name, texture);
    return texture;
  }
  return {environment, matcap};
}

// -- surface detail -----------------------------------------------------------------------
// A small 3D value noise and the bump of three's bumpmap chunk, on the part's own frame (metres),
// so the detail stays on the part as it moves.
const NOISE = `
  float cdxHash(vec3 p){ p=fract(p*0.3183099+.1); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
  float cdxNoise(vec3 x){
    vec3 i=floor(x), f=fract(x); f=f*f*(3.0-2.0*f);
    return mix(mix(mix(cdxHash(i+vec3(0,0,0)),cdxHash(i+vec3(1,0,0)),f.x), mix(cdxHash(i+vec3(0,1,0)),cdxHash(i+vec3(1,1,0)),f.x),f.y),
               mix(mix(cdxHash(i+vec3(0,0,1)),cdxHash(i+vec3(1,0,1)),f.x), mix(cdxHash(i+vec3(0,1,1)),cdxHash(i+vec3(1,1,1)),f.x),f.y), f.z);
  }
  // A feature of period p (metres) is kept while it spans more than a few pixels, then fades.
  float cdxFade(float phase){ return 1.0-smoothstep(.18,.42,fwidth(phase)); }
  float cdxHeight(vec3 p){
    float h=0.0;
    if (uCdxLayer>0.0) { float ph=p.z/uCdxLayer, t=abs(fract(ph)-.5)*2.0; h+=uCdxBead*(1.0-t*t)*cdxFade(ph); }
    if (uCdxGrain>0.0) { vec3 q=p*2600.0; h+=uCdxGrain*(cdxNoise(q)-.5)*cdxFade(q.x); }
    return h*uCdxDetail;
  }
  vec3 cdxBump(vec3 surf, vec3 n, float h, float faceDirection){
    vec3 sx=dFdx(surf), sy=dFdy(surf), r1=cross(sy,n), r2=cross(n,sx);
    float det=dot(sx,r1)*faceDirection;
    vec3 grad=sign(det)*(dFdx(h)*r1+dFdy(h)*r2);
    return normalize(abs(det)*n-grad);
  }`;

// The uniforms every detailed material shares, so the switch costs no recompile.
export const detailSwitch = {value: 1};

// Patch a MeshPhysicalMaterial with the detail of `kind` (a DETAIL key). Idempotent per material.
export function addDetail(material, kind) {
  const d = DETAIL[kind] || DETAIL.purchased;
  const uniforms = {uCdxDetail: detailSwitch, uCdxLayer: {value: d.layer * .001}, uCdxBead: {value: d.bead * .001},
                    uCdxGrain: {value: d.grain * .001}, uCdxDrift: {value: d.drift}, uCdxTone: {value: d.tone}};
  material.userData.detail = uniforms;
  material.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vCdxPos;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvCdxPos = position;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vCdxPos; uniform float uCdxDetail, uCdxLayer, uCdxBead, uCdxGrain, uCdxDrift, uCdxTone;${NOISE}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        diffuseColor.rgb *= 1.0 + uCdxDetail*uCdxTone*((cdxNoise(vCdxPos*30.0+7.0)-.5)*1.4 + (cdxNoise(vCdxPos*190.0)-.5)*.6);`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        roughnessFactor = clamp(roughnessFactor + uCdxDetail*uCdxDrift*((cdxNoise(vCdxPos*45.0)-.5)*1.4 + (cdxNoise(vCdxPos*420.0)-.5)*.6), .04, 1.0);`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        if (uCdxDetail > 0.0) normal = cdxBump(-vViewPosition, normal, cdxHeight(vCdxPos), faceDirection);`);
  };
  material.customProgramCacheKey = () => 'cadex-detail-v1';
  material.needsUpdate = true;
  return material;
}

// -- ambient occlusion ----------------------------------------------------------------------
const FULLSCREEN = 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }';

export function createOcclusion(renderer) {
  let target = null, aoA = null, aoB = null, w = 0, h = 0;
  const normals = new THREE.MeshNormalMaterial({side: THREE.DoubleSide});
  const occlude = new THREE.ShaderMaterial({
    uniforms: {tNormal: {value: null}, tDepth: {value: null}, proj: {value: new THREE.Matrix4()}, invProj: {value: new THREE.Matrix4()},
               radius: {value: .05}, strength: {value: OCCLUSION.strength}, size: {value: new THREE.Vector2()}, far: {value: 10}},
    vertexShader: FULLSCREEN,
    fragmentShader: `uniform sampler2D tNormal, tDepth; uniform mat4 proj, invProj; uniform float radius, strength, far; uniform vec2 size;
      varying vec2 vUv;
      vec3 viewAt(vec2 uv){ float d=texture2D(tDepth,uv).x; vec4 p=invProj*vec4(uv*2.-1., d*2.-1., 1.); return p.xyz/p.w; }
      void main(){
        float d=texture2D(tDepth,vUv).x;
        if (d>=1.) { gl_FragColor=vec4(1.); return; }
        vec3 P=viewAt(vUv), N=normalize(texture2D(tNormal,vUv).xyz*2.-1.);
        // The radius on screen, in uv, at this depth.
        float r=radius*proj[1][1]/max(1e-6,-P.z)*.5;
        float spin=6.2831853*fract(52.9829189*fract(dot(gl_FragCoord.xy, vec2(.06711056,.00583715))));
        float occ=0.;
        for (int i=0;i<${OCCLUSION.samples};i++) {
          float t=(float(i)+.5)/${OCCLUSION.samples}.0, a=spin+float(i)*2.3999632;
          vec2 off=vec2(cos(a),sin(a))*t*r*vec2(size.y/size.x,1.);
          vec3 v=viewAt(vUv+off)-P; float vv=dot(v,v), l=sqrt(vv)+1e-6;
          float fall=max(0.,1.-vv/(radius*radius));
          occ+=fall*max(0.,dot(v,N)/l-.08);
        }
        // Far past the subject the depth buffer is too coarse to trust: the occlusion fades out.
        occ*=1.-smoothstep(.5*far,far,-P.z);
        float ao=clamp(1.-strength*occ/${OCCLUSION.samples}.0*1.6,0.,1.);
        gl_FragColor=vec4(ao,ao,ao,1.);
      }`,
    depthTest: false, depthWrite: false, toneMapped: false});
  // A depth-aware blur, one axis a pass, so occlusion never bleeds across a silhouette.
  const blur = new THREE.ShaderMaterial({
    uniforms: {tAO: {value: null}, tDepth: {value: null}, step: {value: new THREE.Vector2()}, invProj: {value: new THREE.Matrix4()}},
    vertexShader: FULLSCREEN,
    fragmentShader: `uniform sampler2D tAO, tDepth; uniform vec2 step; uniform mat4 invProj; varying vec2 vUv;
      float viewZ(vec2 uv){ float d=texture2D(tDepth,uv).x; vec4 p=invProj*vec4(uv*2.-1., d*2.-1., 1.); return p.z/p.w; }
      void main(){
        float z0=viewZ(vUv), sum=0., wsum=0.;
        for (int i=-3;i<=3;i++) {
          vec2 uv=vUv+float(i)*step; float z=viewZ(uv);
          float w=exp(-float(i*i)/8.)*max(0.,1.-abs(z-z0)/(abs(z0)*.02+1e-5));
          sum+=texture2D(tAO,uv).r*w; wsum+=w;
        }
        float ao=wsum>0.?sum/wsum:1.; gl_FragColor=vec4(ao,ao,ao,1.);
      }`,
    depthTest: false, depthWrite: false, toneMapped: false});
  // The frame times the occlusion: dst*src.
  const compose = new THREE.ShaderMaterial({
    uniforms: {tAO: {value: null}},
    vertexShader: FULLSCREEN,
    fragmentShader: 'uniform sampler2D tAO; varying vec2 vUv; void main(){ gl_FragColor=vec4(vec3(texture2D(tAO,vUv).r),1.); }',
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.DstColorFactor, blendDst: THREE.ZeroFactor,
    blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor,
    depthTest: false, depthWrite: false, toneMapped: false, transparent: true});
  const passScene = new THREE.Scene(), passCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), occlude); passScene.add(quad);
  function size(width, height) {
    if (target && width === w && height === h) return;
    if (target) {target.depthTexture.dispose(); target.dispose(); aoA.dispose(); aoB.dispose();}
    w = width; h = height;
    target = new THREE.WebGLRenderTarget(w, h, {depthTexture: new THREE.DepthTexture(w, h), minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter});
    const opts = {minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false};
    aoA = new THREE.WebGLRenderTarget(w, h, opts); aoB = new THREE.WebGLRenderTarget(w, h, opts);
  }
  // Draw the occlusion of `scene` from `camera` and multiply it over what is on the canvas now.
  // `hide` is called with true before the solids-only pass and false after it.
  function apply(scene, camera, {radius, distance = 10, clipping = null, hide = () => {}} = {}) {
    const buffer = renderer.getDrawingBufferSize(new THREE.Vector2()), ratio = renderer.getPixelRatio();
    // At CSS resolution: the blur hides the difference, and a high-DPI canvas costs a quarter.
    size(Math.max(1, Math.floor(buffer.x / Math.max(1, ratio))), Math.max(1, Math.floor(buffer.y / Math.max(1, ratio))));
    const background = scene.background, fog = scene.fog, clear = renderer.getClearColor(new THREE.Color()), alpha = renderer.getClearAlpha();
    normals.clippingPlanes = clipping;
    scene.background = null; scene.fog = null; scene.overrideMaterial = normals; hide(true);
    renderer.setRenderTarget(target); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(scene, camera);
    scene.background = background; scene.fog = fog; scene.overrideMaterial = null; hide(false);
    const u = occlude.uniforms;
    u.tNormal.value = target.texture; u.tDepth.value = target.depthTexture; u.radius.value = radius; u.far.value = OCCLUSION.fade * distance;
    u.proj.value.copy(camera.projectionMatrix); u.invProj.value.copy(camera.projectionMatrixInverse); u.size.value.set(w, h);
    quad.material = occlude; renderer.setRenderTarget(aoA); renderer.render(passScene, passCamera);
    const b = blur.uniforms; b.tDepth.value = target.depthTexture; b.invProj.value.copy(camera.projectionMatrixInverse);
    b.tAO.value = aoA.texture; b.step.value.set(1 / w, 0); quad.material = blur; renderer.setRenderTarget(aoB); renderer.render(passScene, passCamera);
    b.tAO.value = aoB.texture; b.step.value.set(0, 1 / h); renderer.setRenderTarget(aoA); renderer.render(passScene, passCamera);
    renderer.setRenderTarget(null); renderer.setClearColor(clear, alpha);
    compose.uniforms.tAO.value = aoA.texture; quad.material = compose;
    const auto = renderer.autoClear; renderer.autoClear = false; renderer.render(passScene, passCamera); renderer.autoClear = auto;
  }
  return {apply};
}

// -- the selection's outline -------------------------------------------------------------------
// The selected solids are drawn alone into a mask, through everything in front of them, and a ring
// a couple of pixels wide is drawn round the mask over the frame: bright where the part is in
// view, fainter where another part hides it -- the CAD and Blender idiom, which a glow alone was not.
// The colour is written to the canvas as it is (sRGB), as the page's chrome is.
export const OUTLINE = {colour: 0x58a6ff, width: 2, hidden: .35, layer: 2};

export function createOutline(renderer) {
  let mask = null, w = 0, h = 0;
  const flat = new THREE.MeshBasicMaterial({color: 0xffffff, side: THREE.DoubleSide});
  const ring = new THREE.ShaderMaterial({
    uniforms: {tMask: {value: null}, texel: {value: new THREE.Vector2()},
               colour: {value: new THREE.Color(OUTLINE.colour).convertLinearToSRGB()}, hidden: {value: OUTLINE.hidden}, width: {value: OUTLINE.width}},
    vertexShader: FULLSCREEN,
    fragmentShader: `uniform sampler2D tMask; uniform vec2 texel; uniform vec3 colour; uniform float hidden, width; varying vec2 vUv;
      void main(){
        vec4 here=texture2D(tMask,vUv);
        if (here.a>.5) discard;
        float best=0., seen=0.;
        for (int x=-3;x<=3;x++) for (int y=-3;y<=3;y++) {
          vec2 o=vec2(float(x),float(y)); if (length(o)>width+.5) continue;
          vec4 m=texture2D(tMask,vUv+o*texel);
          if (m.a>.5) { best=1.; seen=max(seen,m.r); }
        }
        if (best<.5) discard;
        gl_FragColor=vec4(colour, mix(hidden,1.,seen));
      }`,
    transparent: true, depthTest: false, depthWrite: false, toneMapped: false});
  const passScene = new THREE.Scene(), passCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), ring); passScene.add(quad);
  // The mask's red is 1 where the part is in view (it passed the depth test against the scene's
  // solids) and 0 where it is hidden; its alpha is 1 wherever the part is at all.
  const visibleMat = new THREE.MeshBasicMaterial({color: 0xffffff, side: THREE.DoubleSide});
  const hiddenMat = new THREE.MeshBasicMaterial({color: 0x000000, side: THREE.DoubleSide, depthTest: false, depthWrite: false});
  const occluders = new THREE.MeshBasicMaterial({colorWrite: false, side: THREE.DoubleSide});
  function size(width, height) {
    if (mask && width === w && height === h) return;
    if (mask) mask.dispose();
    w = width; h = height;
    mask = new THREE.WebGLRenderTarget(w, h, {minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter});
  }
  // `selected`: the meshes to ring; `solids`: every drawn solid, which may hide them.
  function apply(scene, camera, selected, solids, clipping = null) {
    if (!selected.length) return;
    const buffer = renderer.getDrawingBufferSize(new THREE.Vector2());
    size(buffer.x, buffer.y);
    const background = scene.background, fog = scene.fog, clear = renderer.getClearColor(new THREE.Color()), alpha = renderer.getClearAlpha();
    const layers = camera.layers.mask, auto = renderer.autoClear;
    [visibleMat, hiddenMat, occluders].forEach(m => {m.clippingPlanes = clipping;});
    scene.background = null; scene.fog = null;
    renderer.setRenderTarget(mask); renderer.setClearColor(0x000000, 0); renderer.clear();
    renderer.autoClear = false;
    camera.layers.set(OUTLINE.layer);
    // Every solid's depth, then the selection black through it, then white where it is in front.
    solids.forEach(m => m.layers.enable(OUTLINE.layer));
    scene.overrideMaterial = occluders; renderer.render(scene, camera);
    solids.forEach(m => m.layers.disable(OUTLINE.layer));
    selected.forEach(m => m.layers.enable(OUTLINE.layer));
    scene.overrideMaterial = hiddenMat; renderer.render(scene, camera);
    scene.overrideMaterial = visibleMat; renderer.render(scene, camera);
    selected.forEach(m => m.layers.disable(OUTLINE.layer));
    scene.overrideMaterial = null; camera.layers.mask = layers;
    scene.background = background; scene.fog = fog;
    renderer.setRenderTarget(null); renderer.setClearColor(clear, alpha);
    const u = ring.uniforms; u.tMask.value = mask.texture; u.texel.value.set(1 / w, 1 / h);
    u.width.value = OUTLINE.width * Math.min(2, renderer.getPixelRatio());
    renderer.render(passScene, passCamera);
    renderer.autoClear = auto;
  }
  return {apply};
}
