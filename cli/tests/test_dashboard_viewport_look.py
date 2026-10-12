# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The 3D viewport's look (ADR-600, ADR-601, ADR-602; docs/DASHBOARD.md §10).

ADR-600, the floor: the design's own floor and world geometry is never drawn
beside the design; the prototype mat stands in for it, at its top (or under
the design when there is none), the grid is one square a metre on a side at
every zoom, and the camera's clip planes follow the shot and the floor.
ADR-601, the shaded solids: crease-angle normals, a procedural studio for
reflections, and a physical finish per part, a board coloured from its own
geometry. ADR-602, the wireframe: the diagram style is 'wireframe' (a stored
'hairline' still means it), with an optional soft layer of mesh lines whose
switch and strength, like the reflections', are this browser's own.

Synthetic solids are installed straight into the page's viewer, so each
behaviour is proved on geometry whose answer is known; browser tests skip
without a Chromium.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from test_review_server import _model_state, _open, browser, needs_browser, served  # noqa: F401

STATIC = Path(__file__).resolve().parents[1] / "cadex_cli" / "review_static"

# Boxes and a cylinder as triangle soups (mm), and an entry for viewer().install.
SOLIDS = r"""
window.T = {
  box(x0,y0,z0,x1,y1,z1) {
    const v=[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]];
    const f=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
    return f.flatMap(t=>t.flatMap(i=>v[i]));
  },
  cylinder(r,h,n) {
    const out=[], p=k=>[r*Math.cos(2*Math.PI*k/n), r*Math.sin(2*Math.PI*k/n)];
    for (let k=0;k<n;k++) {
      const [ax,ay]=p(k), [bx,by]=p((k+1)%n);
      out.push(ax,ay,0, bx,by,0, bx,by,h,  ax,ay,0, bx,by,h, ax,ay,h,  0,0,h, ax,ay,h, bx,by,h,  0,0,0, bx,by,0, ax,ay,0);
    }
    return out;
  },
  entry(name, tris, extra) {
    return Object.assign({name, positions:new Float32Array(tris), placement:{position_mm:[0,0,0], rotation_xyzw:[0,0,0,1]}}, extra||{});
  },
};
true
"""


def _page(browser, server):
    page = _open(browser, server.url)
    # The project has no accepted model; the solids below are installed by hand.
    assert _model_state(page) in ("loaded", "missing")
    page.evaluate("localStorage.clear()")
    assert page.evaluate(SOLIDS)
    return page


def _install(page, entries_js: str):
    return page.evaluate(f"(function(){{ var v=window.cadexReview.viewer(); v.install([{entries_js}]); return v.stats(); }})()")


def _pixels(page):
    """The viewport's RGB pixels as a flat list, drawn now."""
    return page.evaluate("""(function () {
      var v = window.cadexReview.viewer(); v.draw();
      var c = document.getElementById('viewer'), g = document.createElement('canvas');
      g.width = c.width; g.height = c.height; var x = g.getContext('2d'); x.drawImage(c, 0, 0);
      var d = x.getImageData(0, 0, g.width, g.height).data, out = [];
      for (var i = 0; i < d.length; i += 4) out.push([d[i], d[i + 1], d[i + 2]]);
      return out; })()""")


# -- ADR-600: the floor ----------------------------------------------------------

def test_the_grid_is_one_metre_and_never_steps():
    """No pitch ladder, no finer mesh, no half-pitch dots: one metre, painted once."""
    floor = (STATIC / "floor.js").read_text()
    environment = (STATIC / "environment.js").read_text()
    assert re.search(r"export const GRID_PITCH = 1;", floor)
    for gone in ("PITCH_LADDER", "chooseGridPitch", "minor", "dotAt", "pitchLabel"):
        assert gone not in floor and gone not in environment, gone
    assert "chooseGridPitch" not in environment and "gridMinor" not in environment


@needs_browser
def test_world_geometry_is_not_drawn_and_the_mat_lies_on_its_top(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    # A grey body standing on a bright red 2 m slab marked world geometry, whose top is z = 0.
    stats = _install(page, "T.entry('body', T.box(-30,-20,0,30,20,30), {color:'#9a9a9a'}),"
                           "T.entry('slab', T.box(-1000,-1000,-12,1000,1000,0), {color:'#ff0000', world:true})")
    assert stats["world"] == ["slab"] and stats["hidden_world"] == ["slab"]
    assert stats["floor"] == {"z_mm": 0, "source": "world", "pitch_mm": 1000}
    assert stats["stage"]["floorZ"] == 0
    # Fit frames the body alone, and not one pixel of the slab is drawn.
    assert stats["bounds"]["min"] == pytest.approx([-30, -20, 0], abs=1e-3)
    red = [p for p in _pixels(page) if p[0] > 150 and p[1] < 80 and p[2] < 80]
    assert red == []
    # Nothing picks or ghosts the slab.
    assert page.evaluate("window.cadexReview.viewer().setGhost([T.entry('slab', T.box(-1000,-1000,-12,1000,1000,0), {world:true})])") == 0
    # A body lifted off its floor still has the mat at the floor's top...
    stats = _install(page, "T.entry('body', T.box(-30,-20,50,30,20,80)),"
                           "T.entry('slab', T.box(-1000,-1000,-12,1000,1000,0), {world:true})")
    assert stats["floor"]["z_mm"] == 0 and stats["floor"]["source"] == "world"
    # ...but world geometry taller than a floor leaves the mat under the design.
    stats = _install(page, "T.entry('body', T.box(-30,-20,0,30,20,30)),"
                           "T.entry('wall', T.box(100,-500,0,120,500,400), {world:true})")
    assert stats["floor"] == {"z_mm": 0, "source": "design", "pitch_mm": 1000}
    # With no world geometry the mat is under the design's lowest point.
    stats = _install(page, "T.entry('body', T.box(-30,-20,7,30,20,30))")
    assert stats["floor"]["z_mm"] == pytest.approx(7) and stats["hidden_world"] == []
    # A model that is nothing but world geometry is drawn as it is.
    stats = _install(page, "T.entry('slab', T.box(-100,-100,-2,100,100,0), {world:true})")
    assert stats["hidden_world"] == [] and stats["components"] == 1


@needs_browser
def test_the_grid_and_clip_planes_hold_at_every_zoom(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    _install(page, "T.entry('body', T.box(-30,-20,0,30,20,30))")
    seen = []
    for distance in (20, 150, 2000, 30000, 400000):
        stats = page.evaluate(f"""(function(){{ var v=window.cadexReview.viewer(), c=v.camera();
            c.distance={distance}; v.setCamera(c); return v.stats(); }})()""")
        stage, clip = stats["stage"], stats["clip"]
        # One metre, whatever the framing.
        assert stage["pitch"] == 1 and stats["floor"]["pitch_mm"] == 1000
        # Near is a fixed share of the standoff; far covers the whole floor and the fade.
        d = distance / 1000
        assert clip["near"] == pytest.approx(min(1, max(1e-5, d * 0.002)), rel=1e-6)
        assert clip["far"] >= 1.5 * stage["roomSize"] - 1e-6 and clip["far"] > stage["fog"]["far"]
        assert clip["far"] / clip["near"] < 1e6
        seen.append(stage["roomSize"])
    assert seen == sorted(seen)


# -- ADR-601: the shaded solids ------------------------------------------------------

@needs_browser
def test_crease_normals_are_smooth_round_a_cylinder_and_crisp_at_its_rim(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    result = page.evaluate("""import('./review_scene.js').then(function (m) {
      var tris = T.cylinder(10, 20, 32), n = m.creaseNormals(new Float32Array(tris));
      // Facet 0 is the side quad's first triangle: its corner at k=0, z=0 is radial (smooth);
      // facet 2 is the top cap: every normal is +z (the 90 degree rim is a crease).
      return {radial: [n[0], n[1], n[2]], cap: [n[18], n[19], n[20], n[24], n[25], n[26]], degrees: m.CREASE_DEGREES};
    })""", await_promise=True)
    assert result["degrees"] == 40
    assert result["radial"] == pytest.approx([1, 0, 0], abs=1e-6)
    assert result["cap"] == pytest.approx([0, 0, 1, 0, 0, 1], abs=1e-6)


@needs_browser
def test_each_part_takes_its_finish_and_a_board_its_own_colours(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    board = ("{width_mm:20, length_mm:30, thickness_mm:1.6,"
             " chip:{origin:[5,5,1.6], size:[5,5,1]}, pads:[{origin:[15,25,1.6], dia_mm:2}]}")
    tris = "T.box(0,0,0,20,30,1.6).concat(T.box(5,5,1.6,10,10,2.6), T.box(14.5,24.5,1.6,15.5,25.5,1.7))"
    stats = _install(page, ", ".join([
        "T.entry('shell', T.box(0,0,0,10,10,10), {color:'#e8e2d4', supplier:'printed'})",
        "T.entry('servo', T.box(0,0,0,10,10,10), {color:'#2c2f35', supplier:'purchased'})",
        "T.entry('bolt', T.box(0,0,0,3,3,10), {finish:'hardware', catalog:{family:'bolt', part_number:'M3x10'}})",
        "T.entry('bearing', T.box(0,0,0,3,3,10), {finish:'hardware', catalog:{family:'bearing'}})",
        "T.entry('insert', T.box(0,0,0,3,3,10), {finish:'hardware', catalog:{family:'heat_insert'}})",
        f"T.entry('esp32', {tris}, {{finish:'board', color:'#1f6b3c', board:{board}}})",
        "T.entry('plain_board', T.box(0,0,0,20,30,1.6), {finish:'board'})",
    ]))
    assert stats["finishes"] == {"shell": "printed", "servo": "purchased", "bolt": "black_oxide",
                                 "bearing": "steel", "insert": "brass", "esp32": "board", "plain_board": "board"}
    assert stats["reflections"] == {"strength": 1, "environment": True}
    # The board's chip box and its pad are coloured facet by facet; the plain board is plain green.
    assert stats["boards"] == {"esp32": {"chip": 12, "pad": 12}}
    assert stats["colours"]["plain_board"] == "#1f6b3c" and stats["colours"]["esp32"] == "#1f6b3c"
    # Picking still glows a physical part, and a board keeps its facet colours under it.
    assert page.evaluate("window.cadexReview.viewer().highlight('esp32')") == "esp32"
    assert page.evaluate("window.cadexReview.viewer().highlight(null)") is None
    facets = page.evaluate("""import('./review_scene.js').then(function (m) {
      var tris = T.box(0,0,0,20,30,1.6).concat(T.box(5,5,1.6,10,10,2.6), T.box(14.5,24.5,1.6,15.5,25.5,1.7));
      var r = m.boardColours(new Float32Array(tris), {chip:{origin:[5,5,1.6], size:[5,5,1]}, pads:[{origin:[15,25,1.6], dia_mm:2}]}, '#1f6b3c');
      var c = r.colours, at = function (f) { return [c[f*9], c[f*9+1], c[f*9+2]]; };
      return {mask: at(0), chip: at(12), pad: at(24)};
    })""", await_promise=True)
    assert facets["mask"][1] > facets["mask"][0] and facets["mask"][1] > facets["mask"][2]   # green
    assert max(facets["chip"]) < 0.02                                                        # near black
    assert min(facets["pad"]) > 0.5                                                          # tin
    # The reflections' strength is the page's to scale, and it persists.
    assert page.evaluate("window.cadexReview.setReflections(0.4)") == 0.4
    assert page.evaluate("window.cadexReview.viewer().stats().reflections.strength") == 0.4
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    assert page.evaluate("window.cadexReview.reflections()") == 0.4
    assert page.evaluate("document.getElementById('reflections').value") == "0.4"
    page.evaluate("localStorage.clear()")


# -- ADR-602: the wireframe ------------------------------------------------------------

@needs_browser
def test_a_stored_hairline_choice_opens_as_wireframe(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    page.evaluate("localStorage.setItem('cadex.render', 'hairline')")
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    assert page.evaluate("window.cadexReview.renderStyle()") == "wireframe"
    assert page.evaluate("localStorage.getItem('cadex.render')") == "wireframe"
    assert page.evaluate("window.cadexReview.viewer().stats().render_style") == "wireframe"
    assert page.evaluate("document.querySelector('#view3d-style button[aria-pressed=true]').dataset.style") == "wireframe"
    assert page.evaluate("document.querySelector('#view3d-style button[data-style=wireframe]').textContent") == "Wireframe"
    # The old name still means the diagram when asked for.
    assert page.evaluate("window.cadexReview.setStyle('shaded')") == "shaded"
    assert page.evaluate("window.cadexReview.setStyle('hairline')") == "wireframe"
    assert page.evaluate("window.cadexReview.viewer().setStyle('hairline')") == "wireframe"
    page.evaluate("localStorage.clear()")


@needs_browser
def test_mesh_lines_show_facets_under_the_ink_and_their_choice_persists(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    page.evaluate("window.cadexReview.setStyle('wireframe')")
    _install(page, "T.entry('drum', T.cylinder(30, 40, 48))")
    assert page.evaluate("window.cadexReview.meshLines()") == {"shown": True, "strength": 0.12}

    def drawn():
        paper = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()")
        rgb = [int(paper[i:i + 2], 16) for i in (1, 3, 5)]
        return sum(1 for p in _pixels(page) if sum(abs(a - b) for a, b in zip(p, rgb)) > 6)

    with_lines = drawn()
    assert page.evaluate("window.cadexReview.viewer().stats().mesh_lines.drawn") > 48
    # The switch in the View menu turns them off; the ink stays.
    page.click("#view-panel summary")
    page.click("#mesh-lines")
    assert page.evaluate("window.cadexReview.meshLines().shown") is False
    without = drawn()
    assert 0 < without < with_lines
    page.click("#mesh-lines")
    # The strength slider: stronger lines change more pixels, and the choice survives a reload.
    page.evaluate("var s=document.getElementById('mesh-strength'); s.value='0.6'; s.dispatchEvent(new Event('input'))")
    assert page.evaluate("window.cadexReview.viewer().meshLines()") == {"shown": True, "strength": 0.6}
    page.click("#mesh-lines")
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    assert page.evaluate("window.cadexReview.meshLines()") == {"shown": False, "strength": 0.6}
    assert page.evaluate("window.cadexReview.viewer().meshLines()") == {"shown": False, "strength": 0.6}
    assert page.evaluate("document.getElementById('mesh-lines').checked") is False
    # Shaded has no mesh lines to switch; the controls say so.
    assert page.evaluate("window.cadexReview.setStyle('shaded')") == "shaded"
    assert page.evaluate("document.getElementById('mesh-lines').disabled") is True
    assert page.evaluate("document.getElementById('reflections').disabled") is False
    page.evaluate("localStorage.clear()")


# -- ADR-676: the looks, occlusion and surface detail ------------------------------------

def test_the_looks_are_one_list_in_the_scene_the_page_and_its_menus():
    shading = (STATIC / "shading.js").read_text()
    review = (STATIC / "review.js").read_text()
    html = (STATIC / "index.html").read_text()
    looks = re.findall(r"'(\w+)'", re.search(r"export const LOOKS = \[([^\]]*)\]", shading).group(1))
    assert looks == ["studio", "softbox", "dramatic", "daylight", "aluminium", "clay"]
    assert re.findall(r"'(\w+)'", re.search(r"var LOOKS = \[([^\]]*)\]", review).group(1)) == looks
    for select in ("view3d-look", "look-choice"):
        block = re.search(r'<select id="%s"[^>]*>(.*?)</select>' % select, html, re.S).group(1)
        assert re.findall(r'<option value="(\w+)"', block) == looks, select


def _mean(page, region=None):
    pixels = _pixels(page)
    return [sum(p[i] for p in pixels) / len(pixels) for i in range(3)]


@needs_browser
def test_each_look_lights_the_parts_and_a_matcap_makes_them_one_material(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    _install(page, "T.entry('red', T.box(-40,-20,0,-5,20,30), {color:'#c0392b'}),"
                   "T.entry('blue', T.box(5,-20,0,40,20,30), {color:'#2c5fa8'})")
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    assert stats["look"] == {"name": "studio", "occlusion": True, "detail": True, "matcap": False}
    studio = _pixels(page)
    seen = {}
    for name in ("softbox", "dramatic", "daylight", "aluminium", "clay"):
        assert page.evaluate(f"window.cadexReview.setLook({{name: '{name}'}})")["name"] == name
        look = page.evaluate("window.cadexReview.viewer().stats().look")
        assert look["name"] == name and look["matcap"] is (name in ("aluminium", "clay"))
        frame = _pixels(page)
        seen[name] = sum(1 for a, b in zip(frame, studio) if sum(abs(x - y) for x, y in zip(a, b)) > 12)
    assert all(count > 500 for count in seen.values()), seen

    # Under the aluminium matcap a red part and a blue one are the same grey metal.
    def tone(name):
        x, y = page.evaluate(f"(function(){{ var v=window.cadexReview.viewer(), r=document.getElementById('viewer').getBoundingClientRect(),"
                             f" p=v.screenPoint('{name}'); return [p[0]-r.left, p[1]-r.top]; }})()")
        return page.evaluate(f"""(function () {{
          var c=document.getElementById('viewer'), g=document.createElement('canvas'); g.width=c.width; g.height=c.height;
          var x=g.getContext('2d'); window.cadexReview.viewer().draw(); x.drawImage(c,0,0);
          var s=c.width/c.clientWidth, d=x.getImageData(Math.round({x}*s)-3, Math.round({y}*s)-3, 6, 6).data, t=[0,0,0];
          for (var i=0;i<d.length;i+=4) {{ t[0]+=d[i]; t[1]+=d[i+1]; t[2]+=d[i+2]; }}
          return t.map(function (v) {{ return v/(d.length/4); }}); }})()""")
    page.evaluate("window.cadexReview.setLook({name: 'aluminium'})")
    red, blue = tone("red"), tone("blue")
    # Both grey metal (each face as bright as its normal makes it), neither red nor blue.
    assert max(red) - min(red) < 20 and max(blue) - min(blue) < 20, (red, blue)
    page.evaluate("window.cadexReview.setLook({name: 'studio'})")
    red, blue = tone("red"), tone("blue")
    assert red[0] > red[2] + 30 and blue[2] > blue[0] + 30, (red, blue)
    # The header's menu and the View menu are one choice, kept by this browser; a matcap has no
    # reflections to scale, and the wireframe none of the shaded look.
    page.evaluate("var s=document.getElementById('view3d-look'); s.value='clay'; s.dispatchEvent(new Event('change'))")
    assert page.evaluate("document.getElementById('look-choice').value") == "clay"
    assert page.evaluate("document.getElementById('reflections').disabled") is True
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    assert page.evaluate("window.cadexReview.look()") == {"name": "clay", "occlusion": True, "detail": True}
    assert page.evaluate("window.cadexReview.viewer().look()") == "clay"
    assert page.evaluate("window.cadexReview.setStyle('wireframe')") == "wireframe"
    assert page.evaluate("['view3d-look','look-choice','occlusion','detail'].every(function (id) {"
                         " return document.getElementById(id).disabled; })") is True
    page.evaluate("localStorage.clear()")


@needs_browser
def test_occlusion_darkens_where_surfaces_meet_and_detail_shows_close_up(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    # A block standing on a plate: the occlusion gathers in the corner between them and on the mat.
    _install(page, "T.entry('plate', T.box(-60,-60,0,60,60,6), {color:'#d9d4cb', finish:'printed'}),"
                   "T.entry('block', T.box(-20,-20,6,20,20,46), {color:'#d9d4cb', finish:'printed'})")
    lit = _pixels(page)
    assert page.evaluate("window.cadexReview.setLook({occlusion: false})")["occlusion"] is False
    flat = _pixels(page)
    darker = sum(1 for a, b in zip(lit, flat) if sum(b) - sum(a) > 9)
    lighter = sum(1 for a, b in zip(lit, flat) if sum(a) - sum(b) > 9)
    assert darker > 1000 and lighter < darker / 20, (darker, lighter)
    page.click("#view-panel summary")
    page.click("#occlusion")
    assert page.evaluate("window.cadexReview.look().occlusion") is True
    page.click("#view-panel summary")
    # A printed drum, close up: its layer lines and grain are there with detail on, and gone with it off.
    _install(page, "T.entry('drum', T.cylinder(15, 30, 96), {color:'#d9d4cb', finish:'printed'})")
    page.evaluate("(function(){ var v=window.cadexReview.viewer(), c=v.camera(); c.distance=55; c.pitch=0.15; c.target=[0,0,15]; v.setCamera(c); })()")
    textured = _pixels(page)
    assert page.evaluate("window.cadexReview.setLook({detail: false})")["detail"] is False
    smooth = _pixels(page)
    changed = sum(1 for a, b in zip(textured, smooth) if sum(abs(x - y) for x, y in zip(a, b)) > 3)
    assert changed > 2000, changed
    assert page.evaluate("localStorage.getItem('cadex.detail')") == "off"
    page.evaluate("localStorage.clear()")
