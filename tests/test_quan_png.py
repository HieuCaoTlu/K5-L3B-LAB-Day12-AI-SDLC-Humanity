"""PNG loading and delivery checks; renderer changes stay outside headless rules."""

import json
from pathlib import Path
import struct
import subprocess
import unittest
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "chonoi/web/index.html"

LOADER_TEST = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync(process.argv[1], "utf8");
const source = html.slice(html.indexOf("const AQ = "), html.indexOf("const qnow = "));
const mode = process.argv[2], pending = [], draws = [], warnings = [];
class FakeImage {
  complete = false;
  naturalWidth = 0;
  set src(value) { this.url = value; pending.push(this); }
  load() { this.complete = true; this.naturalWidth = 96; this.naturalHeight = 128; this.onload(); }
  fail() { this.complete = true; this.onerror(); }
}
const manifest = {
  scale: 4,
  assets: [{path:"char/a.png"}, {path:"char/b.png"}],
  animations: {walk: {frames:["char/a.png", "char/b.png"], frame_ms:125}}
};
const context = vm.createContext({
  Image: FakeImage,
  g: {drawImage: (...args) => draws.push(args)},
  console: {warn: (...args) => warnings.push(args)},
  fetch: async () => ({ok:mode !== "404", status:404, json:async () => manifest})
});
vm.runInContext(source + "\nthis.state=AQ; this.loaded=quanAssetsReady; this.frame=qframe; this.put=qput;", context);
(async () => {
  assert.equal(context.state.ready, false);
  await new Promise(setImmediate);
  if (mode === "404") {
    await context.loaded;
    assert.equal(context.state.ready, true);
    assert.equal(context.state.man, null);
    assert.equal(context.put("char/a.png", 0, 0), false);
    assert.equal(context.frame("walk", 0), null);
    assert.equal(warnings.length, 1);
    return;
  }
  assert.equal(pending.length, 2);
  pending[0].load();
  await new Promise(setImmediate);
  assert.equal(context.state.man, null);
  assert.equal(context.state.ready, false);
  assert.equal(context.put("char/a.png", 0, 0), false, "no partial pack is rendered");
  pending[1].fail();
  await context.loaded;
  assert.equal(context.state.ready, true);
  assert.equal(context.put("char/b.png", 0, 0), false);
  assert.equal(context.frame("walk", 0), "char/a.png");
  assert.equal(context.frame("walk", 125), "char/a.png", "failed frames are skipped");
  assert.equal(context.put("char/a.png", 1.6, 2.2), true);
  assert.deepEqual(draws[0].slice(1), [2, 2, 24, 32]);
  assert.equal(context.g.imageSmoothingEnabled, false);
})().catch(error => { console.error(error); process.exitCode=1; });
"""


class QuanPNGTest(unittest.TestCase):
    def test_menu_handles_both_modes_without_removed_button(self):
        script = r"""
const assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
const html = fs.readFileSync(process.argv[1], "utf8");
const source = html.slice(html.indexOf("function updateMenu()"), html.indexOf("function lowXY("));
const nodes = Object.fromEntries(["btnNext", "btnNew", "btnUpg", "menubar"].map(id => [id, {style:{}}]));
const context = vm.createContext({document:{getElementById:id => nodes[id]}, cv:{style:{}}, snap:{mode:"quan", day:1, finished:false}});
vm.runInContext(source + "\nupdateMenu();", context);
assert.equal(nodes.menubar.style.display, "none");
context.snap = {mode:"gather"};
vm.runInContext("updateMenu();", context);
assert.equal(nodes.menubar.style.display, "flex");
"""
        subprocess.run(["node", "-e", script, str(HTML)], check=True)

    def test_preload_is_atomic_and_failed_images_keep_working(self):
        subprocess.run(["node", "-e", LOADER_TEST, str(HTML), "partial"], check=True)

    def test_missing_manifest_keeps_fallback_renderer(self):
        subprocess.run(["node", "-e", LOADER_TEST, str(HTML), "404"], check=True)

    def test_live_serves_manifest_and_animation_png(self):
        server = LiveServer(LiveGame("quan", load_contract()["tuning"], {}, 1), port=0)
        server.start()
        try:
            with urllib.request.urlopen(server.url + "assets/quan/manifest.json", timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "application/json")
                manifest = json.load(response)
            path = manifest["animations"]["ut_sen.carry_walk.left"]["frames"][1]
            with urllib.request.urlopen(server.url + "assets/quan/" + path, timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "image/png")
                png = response.read()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), (96, 128))
        finally:
            server.stop()
