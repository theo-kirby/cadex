"""D11: real retained project, persistent viewport, decoded video, actual reference frames.

PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
    URL PROJECT REFERENCE [RUN [HISTORICAL [EVIDENCE_DIR]]]
RUN is the run whose retained pose and video are compared (default copy100);
HISTORICAL is the clip played, downloaded and polled from the same page
(default probe3-checkpoint20); EVIDENCE_DIR is a directory name under the
project's evidence/ (default style40). The persistent server is never started
or stopped, the reference checkout is read-only, and all images stay with the
project.
"""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading

from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import run_model
from cadex_cli.video import stl

url, project, reference, *rest = sys.argv[1:]
run, historical, evidence_dir = (rest + ['copy100', 'probe3-checkpoint20', 'style40'][len(rest):])[:3]
root, ref = Path(project), Path(reference)
out = root / 'evidence' / evidence_dir; out.mkdir(parents=True, exist_ok=True)
record = read_run_record(root/'runs'/run, root)
video = record['videos'][0]
trace = json.loads((root/'runs'/run/record['artifacts']['trace']).read_text())
frame = next(f for f in trace['frames'] if f.get('frame_kind') == 'solver_output')
manifest = run_model(root, record)
entries = [{'name': e['name'], 'placement': frame['component_placements'][e['name']],
            'positions': [v for t in stl(root/'runs'/run/'rollout'/(e['output']+'.stl')) for p in t for v in p]}
           for e in manifest['components'] if e['name'] in frame['component_placements']]
evidence = {'project': root.name, 'run': run, 'historical': historical, 'evidence_dir': evidence_dir,
            'video': video, 'screenshots': {},
            'reference_commit': subprocess.check_output(['git','-C',str(ref),'rev-parse','HEAD'],text=True).strip()}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def canvas(page, expression, name):
    path = out/(name+'.png'); path.write_bytes(base64.b64decode(page.evaluate(expression)))
    evidence['screenshots'][name] = sha(path)

subprocess.run(['ffmpeg','-v','error','-y','-i',str(root/'runs'/run/video['path']),
                '-frames:v','1',str(out/'video-frame0.png')],check=True)
# An actual shipped reference clip (dark theme, drone subject) decoded at a fixed time, so the
# comparison also has a reference-native frame beside the reference-module light render.
shipped = ref/'render-examples/orbit_maneuver_policy.mp4'
subprocess.run(['ffmpeg','-v','error','-y','-ss','4','-i',str(shipped),'-frames:v','1',
                str(out/'reference-shipped-orbit-4s.png')],check=True)
evidence['reference_shipped_frame'] = {'video': 'render-examples/orbit_maneuver_policy.mp4',
                                       'video_sha256': sha(shipped), 'seconds': 4, 'theme': 'dark',
                                       'image_sha256': sha(out/'reference-shipped-orbit-4s.png')}
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('cadexReview.ready',await_promise=True)
    assert page.text('#project-name') == root.name+' — review'
    assert page.text('#view-kind') == 'RUN '+run
    assert page.text('#view-revision') == record['model']['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.evaluate("document.getElementById('viewer').style.cssText='width:512px;height:512px;border:0;padding:0'; cadexReview.viewer().draw()")
    canvas(page,'cadexReview.viewer().png()', 'persistent-default')
    # Model remains the dashboard's own retained first solved pose. Only the camera
    # and fit volume are set equal to the video, not its geometry or identity.
    page.evaluate('cadexReview.viewer().frameBounds('+json.dumps(video['bounds'])+'); cadexReview.viewer().setCamera('+json.dumps(video['camera'])+')')
    canvas(page,'cadexReview.viewer().png()', 'persistent-same-pose')
    evidence['persistent_identity'] = page.evaluate('cadexReview.state()')
    evidence['camera'] = page.evaluate('cadexReview.viewer().camera()')
    evidence['stats'] = page.evaluate('cadexReview.viewer().stats()')
    for label, scale, pitch in [('close',.7,.25),('wide',3,.08),('under',1,-.5)]:
        c={**video['camera'],'distance':video['camera']['distance']*scale,'pitch':pitch,'yaw':1.8}
        page.evaluate('cadexReview.viewer().setCamera('+json.dumps(c)+')')
        canvas(page,'cadexReview.viewer().png()', 'persistent-'+label)
    # Orbit and zoom by real pointer input on the persistent page, not by API camera
    # placement: the environment must restage under the framing a person reaches.
    page.evaluate('cadexReview.viewer().frameBounds('+json.dumps(video['bounds'])+'); cadexReview.viewer().setCamera('+json.dumps(video['camera'])+')')
    page.scroll_into_view('#viewer'); rect = page.rect('#viewer')
    cx, cy = rect['x']+rect['width']/2, rect['y']+rect['height']/2
    before = page.evaluate('cadexReview.viewer().camera()')
    page.drag(cx, cy, cx-180, cy+30)
    dragged = page.wait_for('(function(){var c=cadexReview.viewer().camera();return c.yaw!=='+repr(before['yaw'])+'&&c.pitch!=='+repr(before['pitch'])+'&&c})()')
    assert dragged['distance'] == before['distance']
    canvas(page,'cadexReview.viewer().png()', 'persistent-orbit-drag')
    page.wheel(cx, cy, -360)
    zoomed = page.wait_for('(function(){var c=cadexReview.viewer().camera();return c.distance<'+repr(dragged['distance'])+'&&c})()')
    canvas(page,'cadexReview.viewer().png()', 'persistent-orbit-zoom')
    page.wheel(cx, cy, 1200)
    zoomed_out = page.wait_for('(function(){var c=cadexReview.viewer().camera();return c.distance>'+repr(before['distance'])+'*2&&c})()')
    canvas(page,'cadexReview.viewer().png()', 'persistent-orbit-far')
    evidence['orbit'] = {'before': before, 'after_drag': dragged, 'after_zoom_in': zoomed, 'after_zoom_out': zoomed_out,
                         'model_pixels': {'drag': page.evaluate('(cadexReview.viewer().setCamera('+json.dumps(dragged)+'), cadexReview.viewer().nonBackgroundPixels())'),
                                          'zoom_in': page.evaluate('(cadexReview.viewer().setCamera('+json.dumps(zoomed)+'), cadexReview.viewer().nonBackgroundPixels())'),
                                          'zoom_out': page.evaluate('(cadexReview.viewer().setCamera('+json.dumps(zoomed_out)+'), cadexReview.viewer().nonBackgroundPixels())')},
                         'stage_far': page.evaluate('cadexReview.viewer().stats().stage')}
    assert min(evidence['orbit']['model_pixels'].values()) > 1000
    page.evaluate('cadexReview.viewer().setCamera('+json.dumps(video['camera'])+')')

    # Identical capture API and explicit same pose/camera, lossless before encoding.
    capture = browser.page(url+'capture.html');capture.wait_for('window.cadexCapture?.available')
    capture.evaluate('cadexCapture.install('+json.dumps(entries)+');cadexCapture.frameBounds('+json.dumps(video['bounds'])+');cadexCapture.setCamera('+json.dumps(video['camera'])+')')
    canvas(capture,'cadexCapture.png()', 'capture-same-pose')
    assert (out/'persistent-same-pose.png').read_bytes() == (out/'capture-same-pose.png').read_bytes()
    evidence['lossless_viewport_capture_equal'] = True

    page.send("Page.bringToFront")
    page.click('#views li[data-run="'+historical+'"]')
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN "+historical+"'")
    page.wait_for("!!document.querySelector('#videos video')")
    checkpoint = read_run_record(root/'runs'/historical,root)['videos'][0]
    evidence['historical_relation'] = page.text('#view-relation')
    page.evaluate("window.checkpointVideo=document.querySelector('#videos video');checkpointVideo.muted=true;checkpointVideo.play()",await_promise=True)
    page.wait_for('checkpointVideo.currentTime > .1')
    downloaded=page.download('#videos li[data-video="0"] a')
    assert sha(downloaded.path)==checkpoint['sha256']
    page.evaluate('cadexReview.refresh()',await_promise=True)
    assert page.evaluate("checkpointVideo === document.querySelector('#videos video') && !checkpointVideo.paused")
    page.click('#current-run');assert page.text('#view-kind')=='RUN '+run
    evidence['checkpoint']=checkpoint
    evidence['checkpoint_playback_download_poll']=True
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(root/'runs'/historical/checkpoint['path']),
                    '-frames:v','1',str(out/'checkpoint-frame0.png')],check=True)

    # An in-memory harness uses the actual unmodified reference scene/environment
    # modules. No file is written into the sibling checkout, no drone glyph scaling.
    routes = {'/scene.js':ref/'web/studio/scene.js','/environment.js':ref/'web/studio/environment.js',
              '/geometry.js':ref/'web/studio/geometry.js',
              '/three.js':ref/'.cache/three/28f7db420fe306d9_three.module.js',
              '/OrbitControls.js':ref/'.cache/three/10917d0867f0b694_OrbitControls.js'}
    html=b'''<style>body{margin:0}#scene{width:512px;height:512px;border:0;padding:0}</style><div id="scene"></div>
    <script type="importmap">{"imports":{"three":"/three.js","three/addons/controls/OrbitControls.js":"/OrbitControls.js"}}</script>'''
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path != '/' and self.path not in routes:
                self.send_error(404);return
            body=html if self.path=='/' else routes[self.path].read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html' if self.path=='/' else 'text/javascript');self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        page=browser.page('http://127.0.0.1:'+str(server.server_port)+'/')
        page.evaluate('window.entries='+json.dumps(entries)+';window.cameraValue='+json.dumps(video['camera'])
                      +';window.floorZ='+repr(video['bounds']['min'][2]/1000-0.003))
        page.evaluate('''(async()=>{
          const THREE=await import('three');
          const {createScene,setToneMapping,configureKeyLight}=await import('/scene.js');
          const {createEnvironment}=await import('/environment.js');
          const v=createScene(document.getElementById('scene'),{grid:false,preserveDrawingBuffer:true});
          v.renderer.setPixelRatio(1);v.controls.enabled=false;v.ground.visible=false;
          setToneMapping(v.renderer,.95);const env=createEnvironment(v);env.setTheme('light');
          const palette=[0x5b9dcd,0xde8f47,0x6ab270,0xc468b4,0xdcc85a,0x7878c8,0xc86e6e,0x6ebebe];
          entries.forEach((e,i)=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(e.positions.map(x=>x/1000),3));g.computeVertexNormals();
            const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:palette[i%8],roughness:.72,metalness:.05,side:THREE.DoubleSide}));
            m.position.fromArray(e.placement.position_mm).multiplyScalar(.001);m.quaternion.fromArray(e.placement.rotation_xyzw);m.castShadow=true;m.receiveShadow=true;v.world.add(m);});
          const c=cameraValue,t=c.target.map(x=>x/1000),d=c.distance/1000,cp=Math.cos(c.pitch);
          v.camera.position.set(t[0]+d*cp*Math.cos(c.yaw),t[2]+d*Math.sin(c.pitch),-t[1]-d*cp*Math.sin(c.yaw));
          v.controls.target.set(t[0],t[2],-t[1]);v.camera.lookAt(v.controls.target);
          env.setStage({camDist:d});env.setSize({floorZ:floorZ});
          configureKeyLight(v,{focus:v.controls.target,extent:.35});v.resize();v.render();window.referenceView=v;window.referenceEnv=env;
        })()''',await_promise=True)
        canvas(page,"referenceView.renderer.domElement.toDataURL('image/png').split(',')[1]",'reference-light-reed')
        # The same close and wide cameras the persistent viewport was staged at, restaged by the
        # reference's own setStage, so framing scale, fog and shadow can be compared like for like.
        for label, scale, pitch in [('close',.7,.25),('wide',3,.08)]:
            page.evaluate('''(async()=>{
              const {configureKeyLight}=await import('/scene.js');const v=referenceView;
              const c=cameraValue,t=c.target.map(x=>x/1000),d=c.distance/1000*%r,yaw=1.8,pitch=%r,cp=Math.cos(pitch);
              v.camera.position.set(t[0]+d*cp*Math.cos(yaw),t[2]+d*Math.sin(pitch),-t[1]-d*cp*Math.sin(yaw));
              v.camera.lookAt(v.controls.target);referenceEnv.setStage({camDist:d});referenceEnv.setSize({floorZ:floorZ});
              configureKeyLight(v,{focus:v.controls.target,extent:.35});v.render();
            })()''' % (scale, pitch),await_promise=True)
            canvas(page,"referenceView.renderer.domElement.toDataURL('image/png').split(',')[1]",'reference-light-reed-'+label)
    finally:server.shutdown();server.server_close()
# Codec tolerance measured on decoded RGB, separate from lossless scene parity.
def rgb(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'])
a,b=rgb(out/'persistent-same-pose.png'),rgb(out/'video-frame0.png')
assert len(a)==len(b)==512*512*3
error=sum(abs(x-y) for x,y in zip(a,b))/len(a)
assert error<3,error
evidence['codec_mean_absolute_rgb_error']=error
evidence['images']={p.name:sha(p) for p in out.glob('*.png')}
# Standalone side-by-side review artifact; images remain project-local.
rows=[['reference-light-reed','persistent-same-pose','video-frame0'],
      ['reference-light-reed-close','persistent-close','reference-shipped-orbit-4s'],
      ['reference-light-reed-wide','persistent-wide','persistent-orbit-far']]
html='<meta charset="utf-8"><style>body{font:16px sans-serif;margin:12px}main{display:flex}figure{margin:8px}img{width:360px}</style>'
for columns in rows:
    html+='<main>'
    for name in columns:
        html+='<figure><figcaption>'+name+'</figcaption><img src="data:image/png;base64,'+base64.b64encode((out/(name+'.png')).read_bytes()).decode()+'"></figure>'
    html+='</main>'
(out/'side-by-side.html').write_text(html)
with HeadlessBrowser(find_browser(),width=1160,height=1250) as browser:
    page=browser.page('data:text/html;base64,'+base64.b64encode(html.encode()).decode())
    page.send('Emulation.setDeviceMetricsOverride',{'width':1160,'height':1260,'deviceScaleFactor':1,'mobile':False})
    page.screenshot(out/'side-by-side.png')
evidence['images']['side-by-side.png']=sha(out/'side-by-side.png')
(out/'comparison.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence,indent=2))
