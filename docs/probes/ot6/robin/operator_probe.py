"""Check the retained Robin model at the private URL. URL comes from argv."""
import json
import sys
import urllib.request
from pathlib import Path
from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
m = json.load(urllib.request.urlopen(url + 'api/model/accepted'))
receipt = {'revision': m['revision'], 'components': len(m['components']), 'visits': []}
assert len(m['components']) == 24
for width, height in [(1400, 900), (400, 850)]:
    with HeadlessBrowser(find_browser(), width=width, height=height) as browser:
        page = browser.page(url)
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
        row = {'width': width, 'selected': state['selected'], 'overflow': overflow,
               'status': page.text('#model-status'), 'accepted': page.text('#accepted-line')}
        page.click('#show-collision')
        page.wait_for("document.getElementById('model-status').dataset.showing === 'solids+proxies'")
        row['proxy_status'] = page.text('#model-status')
        receipt['visits'].append(row)
(out/'operator.json').write_text(json.dumps(receipt, indent=1)+'\n')
print(json.dumps(receipt))
