"""Tests for the Quán (evening) audio pack and inline Web Audio integration."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "chonoi/web/assets/audio/quan"
sys.path.insert(0, str(ROOT / "tools"))

import quan_audio  # noqa: E402


class QuanAudioTest(unittest.TestCase):
    def test_wav_pack_integrity(self):
        quan_audio.check()
        manifest = json.loads((AUDIO_DIR / "manifest.json").read_text(encoding="utf-8"))
        wav_names = {entry["path"] for entry in manifest["assets"]}
        self.assertGreaterEqual(len(wav_names), 20)
        for required in ("bgm_quan_night.wav", "bgm_quan_rush.wav", "amb_quan_river_night.wav", "jingle_quan_end.wav"):
            self.assertIn(required, wav_names)

    def test_index_and_mock_have_inline_quan_audio_and_valid_js(self):
        for html_name in ("index.html", "mock_quan.html"):
            html_text = (ROOT / "chonoi/web" / html_name).read_text(encoding="utf-8")
            self.assertNotIn("quan_audio.js", html_text, f"{html_name} must embed QuanAudio inline")
            self.assertIn("QuanAudio", html_text, html_name)
            self.assertIn("NIGHT_PLUCK", html_text, html_name)
            self.assertIn("RUSH_MEL", html_text, html_name)
            blocks = re.findall(r"<script>([\s\S]*?)</script>", html_text)
            self.assertEqual(len(blocks), 1, html_name)
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tf:
                tf.write(blocks[0])
                tmp_path = Path(tf.name)
            try:
                subprocess.run(["node", "--check", str(tmp_path)], check=True)
            finally:
                tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
