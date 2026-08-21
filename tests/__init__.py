"""fx-dub test suite.

Run from the repo root with the stdlib runner (this is exactly what CI runs):

    python -m unittest discover -s tests -v

pytest also collects these, but is never required — every test is a stdlib
``unittest.TestCase``.

Helper libraries (not test modules, so discovery's ``test*.py`` pattern skips
them):

* ``graph_lint``  — structural validation + defect detectors for the archived
  ComfyUI graphs in ``workflows/comfy-cloud/as-built/``.
* ``flac_info``   — STREAMINFO decoder used to turn a downloaded master into a
  receipt (sample rate / channels / bit depth / duration).
"""
