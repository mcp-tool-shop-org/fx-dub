"""Brand asset regressions.

The logo was shipped once with a fat transparent margin baked into the canvas,
which made every downstream layout (README, landing page, handbook) size it
wrong. The fix was a tight crop; this pins it so a regenerated asset cannot
quietly reintroduce the padding.
"""

from __future__ import annotations

import os
import unittest

try:
    from PIL import Image
except Exception:  # pragma: no cover - exercised only where Pillow is absent
    Image = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(REPO_ROOT, "docs", "assets")

REQUIRED_ASSETS = ("logo.png", "logo.svg", "mark.png", "mark.svg")

#: How much fully transparent margin the canvas may carry on any side.
MAX_ALPHA_MARGIN_PX = 4


def _asset(name):
    return os.path.join(ASSETS_DIR, name)


class BrandAssetFileTests(unittest.TestCase):
    def test_assets_directory_exists(self):
        self.assertTrue(os.path.isdir(ASSETS_DIR), ASSETS_DIR)

    def test_required_assets_exist(self):
        for name in REQUIRED_ASSETS:
            with self.subTest(asset=name):
                self.assertTrue(os.path.isfile(_asset(name)), _asset(name))

    def test_required_assets_are_not_empty(self):
        for name in REQUIRED_ASSETS:
            with self.subTest(asset=name):
                self.assertGreater(os.path.getsize(_asset(name)), 0)

    def test_svgs_are_svg(self):
        for name in (n for n in REQUIRED_ASSETS if n.endswith(".svg")):
            with self.subTest(asset=name):
                with open(_asset(name), "r", encoding="utf-8", errors="replace") as fh:
                    head = fh.read(2048)
                self.assertIn("<svg", head)


@unittest.skipIf(Image is None, "Pillow (PIL) is not installed — CI installs it")
class BrandAssetImageTests(unittest.TestCase):
    def test_logo_is_rgba(self):
        with Image.open(_asset("logo.png")) as im:
            self.assertEqual("RGBA", im.mode)

    def test_logo_alpha_bbox_is_tight(self):
        """The 'cropped properly' regression: no transparent gutter around the mark."""
        with Image.open(_asset("logo.png")) as im:
            rgba = im.convert("RGBA")
            width, height = rgba.size
            bbox = rgba.getchannel("A").getbbox()

        self.assertIsNotNone(bbox, "logo.png is fully transparent")
        left, top, right, bottom = bbox
        margins = {
            "left": left,
            "top": top,
            "right": width - right,
            "bottom": height - bottom,
        }
        for side, margin in sorted(margins.items()):
            with self.subTest(side=side):
                self.assertLessEqual(
                    margin, MAX_ALPHA_MARGIN_PX,
                    "logo.png has {0}px of transparent {1} margin (canvas {2}x{3}, "
                    "alpha bbox {4}) — re-crop it".format(margin, side, width, height, bbox))

    def test_mark_is_square(self):
        with Image.open(_asset("mark.png")) as im:
            width, height = im.size
        self.assertEqual(width, height, "mark.png is {0}x{1}, must be square".format(width, height))

    def test_mark_has_pixels(self):
        with Image.open(_asset("mark.png")) as im:
            self.assertIsNotNone(im.convert("RGBA").getchannel("A").getbbox(),
                                 "mark.png is fully transparent")


if __name__ == "__main__":
    unittest.main()
