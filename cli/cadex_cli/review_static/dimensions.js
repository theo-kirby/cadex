// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
// The declared-dimension overlay's geometry (DASHBOARD.md §31, ADR-524). The engine gives a
// `part.measurement` record: a number, its text, and two anchor points, a circle, or an angle's
// vertex and ends, in mm. Only those are in model space. Everything else — the offset, the
// extension lines, the ticks, the text — is laid out in screen pixels, so a dimension reads the
// same on a 2 mm boss and a 2 m beam, its line never goes edge-on, and its number stays upright.
// Looked at straight down its axis, a dimension collapses to a leader: a stub and the number,
// so the value is shown from every side. Pure: `toScreen(point_mm)` is the only way in.
export const DIMENSION = {offset:22, gap:4, overrun:6, tick:5, minSpan:12, leader:24, arc:28, samples:24};

const sub=(a,b)=>[a[0]-b[0],a[1]-b[1]], add=(a,b)=>[a[0]+b[0],a[1]+b[1]], mul=(a,s)=>[a[0]*s,a[1]*s];
const len=a=>Math.hypot(a[0],a[1]);
const seg=(a,b)=>[a[0],a[1],b[0],b[1]];

// Two unit vectors spanning the plane normal to `n` (mm space).
function basis(n) {
  const m=Math.hypot(...n)||1, u=n.map(v=>v/m);
  const pick=Math.abs(u[0])<.9?[1,0,0]:[0,1,0];
  let e=[u[1]*pick[2]-u[2]*pick[1], u[2]*pick[0]-u[0]*pick[2], u[0]*pick[1]-u[1]*pick[0]];
  const k=Math.hypot(...e); e=e.map(v=>v/k);
  return [e, [u[1]*e[2]-u[2]*e[1], u[2]*e[0]-u[0]*e[2], u[0]*e[1]-u[1]*e[0]]];
}

// The two screen points a diameter or radius is drawn between: of `samples` points round the
// circle, the diameter (or radius) that is widest on screen now, so it reads at any orbit.
function circleEnds(record, toScreen) {
  const c=record.center_mm, r=record.radius_mm;
  if (!Array.isArray(c)||!Array.isArray(record.normal)||!(r>0)) return null;
  const centre=toScreen(c); if (!centre) return null;
  const [e1,e2]=basis(record.normal), n=DIMENSION.samples, ring=[];
  for (let i=0;i<n;i++) {
    const t=2*Math.PI*i/n, p=toScreen(c.map((v,j)=>v+r*(Math.cos(t)*e1[j]+Math.sin(t)*e2[j])));
    if (!p) return null; ring.push(p);
  }
  let best=null, width=-1;
  const radius=record.kind==='radius';
  for (let i=0;i<(radius?n:n/2);i++) {
    const a=radius?centre:ring[i+n/2], b=ring[i], w=len(sub(b,a));
    if (w>width) {width=w; best=[a,b];}
  }
  return best;
}

function leader(at, text) {
  const tip=add(at,[DIMENSION.leader*Math.SQRT1_2,-DIMENSION.leader*Math.SQRT1_2]);
  return {form:'leader', lines:[seg(at,tip)], text, at:add(tip,[3,-3]), anchor:'start'};
}

function linear(a, b, text) {
  const d=sub(b,a), span=len(d);
  if (span<DIMENSION.minSpan) return leader(a,text);
  const u=mul(d,1/span); let n=[-u[1],u[0]];
  if (n[1]>0||(n[1]===0&&n[0]<0)) n=mul(n,-1);   // offset up the screen
  const o=DIMENSION.offset, a2=add(a,mul(n,o)), b2=add(b,mul(n,o)), slash=mul(add(u,n),DIMENSION.tick*Math.SQRT1_2);
  return {form:'dimension', text, anchor:'middle', at:add(mul(add(a2,b2),.5),mul(n,4)),
    lines:[seg(add(a,mul(n,DIMENSION.gap)),add(a,mul(n,o+DIMENSION.overrun))),
           seg(add(b,mul(n,DIMENSION.gap)),add(b,mul(n,o+DIMENSION.overrun))),
           seg(a2,b2), seg(sub(a2,slash),add(a2,slash)), seg(sub(b2,slash),add(b2,slash))]};
}

function angle(record, toScreen, text) {
  const v=Array.isArray(record.vertex_mm)&&toScreen(record.vertex_mm);
  const ends=Array.isArray(record.anchors_mm)&&record.anchors_mm.length===2?record.anchors_mm.map(toScreen):[];
  if (!v||ends.length!==2||!ends[0]||!ends[1]) return null;
  const d0=sub(ends[0],v), d1=sub(ends[1],v);
  if (len(d0)<DIMENSION.minSpan||len(d1)<DIMENSION.minSpan) return leader(v,text);
  const r=Math.min(DIMENSION.arc,.8*Math.min(len(d0),len(d1)));
  let t0=Math.atan2(d0[1],d0[0]), t1=Math.atan2(d1[1],d1[0]), dt=t1-t0;
  dt=Math.atan2(Math.sin(dt),Math.cos(dt));   // the smaller arc between the two arms
  const lines=[seg(v,ends[0]),seg(v,ends[1])], steps=12;
  for (let i=0;i<steps;i++) {
    const p=t=>add(v,[r*Math.cos(t0+dt*t/steps),r*Math.sin(t0+dt*t/steps)]);
    lines.push(seg(p(i),p(i+1)));
  }
  const mid=t0+dt/2;
  return {form:'angle', lines, text, anchor:'middle', at:add(v,[(r+14)*Math.cos(mid),(r+14)*Math.sin(mid)+4])};
}

// One record's overlay: {form, lines:[[x1,y1,x2,y2]...], text, at:[x,y], anchor}, or null when
// it cannot be placed in this view (a point behind the camera, a record with nothing to draw).
export function layout(record, toScreen) {
  const text=String(record.text||'');
  if (record.kind==='angle') return angle(record,toScreen,text);
  if (record.kind==='diameter'||record.kind==='radius') {
    const ends=circleEnds(record,toScreen);
    return ends?linear(ends[0],ends[1],text):null;
  }
  const anchors=Array.isArray(record.anchors_mm)&&record.anchors_mm.length===2?record.anchors_mm.map(toScreen):[];
  return anchors.length===2&&anchors[0]&&anchors[1]?linear(anchors[0],anchors[1],text):null;
}
