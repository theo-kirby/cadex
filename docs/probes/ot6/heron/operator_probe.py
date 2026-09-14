"""Check the retained Heron model at the private URL, at both charter widths.

Usage: PYTHONPATH=cli pixi run python docs/probes/ot6/heron/operator_probe.py URL OUT
The URL comes from argv (read from the environment by the caller), never from
this file. Writes OUT/operator.json and OUT/operator-{1400,400}.png.
"""
import json
import sys
import urllib.request
from pathlib import Path
from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
m = json.load(urllib.request.urlopen(url + 'api/model/accepted'))
receipt = {'project_revision': m['revision'], 'components': len(m['components']),
           'component_names': sorted(c['name'] for c in m['components']), 'visits': []}
for width, height in [(1400, 900), (400, 850)]:
    mobile = width == 400
    with HeadlessBrowser(find_browser(), width=width, height=height) as browser:
        page = browser.page('about:blank')
        page.send('Emulation.setDeviceMetricsOverride',
                  {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': mobile})
        if mobile:
            page.send('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
        page.send('Page.navigate', {'url': url})
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate('window.cadexReview.ready', await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("document.getElementById('model-status').dataset.showing === 'solids'")
        overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
        assert not overflow
        page.scroll_into_view('#model')
        path = out / f'operator-{width}.png'
        page.screenshot(path, clip=page.rect('#model'))
        Image.open(path).convert('RGB').quantize(256).save(path, optimize=True)
        state = page.evaluate('window.cadexReview.state()')
        row = {'width': width, 'height': height, 'selected': state['selected'], 'overflow': overflow,
               'status': page.text('#model-status'), 'accepted': page.text('#accepted-line')}
        page.click('#show-collision')
        page.wait_for("document.getElementById('model-status').dataset.showing === 'solids+proxies'")
        row['proxy_status'] = page.text('#model-status')
        receipt['visits'].append(row)
(out / 'operator.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps(receipt))
