#!/usr/bin/env bash
# verify — test + build + smoke, in one command.
#
# This is the single gate: if `./verify.sh` is green, the tree is shippable.
# CI runs exactly this, so a green local run means a green CI run.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> test suite"
python -m unittest discover -s tests

echo
echo "==> graph-lint detectors are not vacuous"
# A detector that never fires is theater. The suite asserts every detector goes
# red on the archived graph it was written for; this re-states it as a gate so
# `verify` fails loudly if someone lands a detector with no red fixture.
python -m unittest tests.test_api_detectors.RegistryHygieneTests

echo
echo "==> build wheel + sdist"
rm -rf dist build ./*.egg-info
python -m build

echo
echo "==> smoke: install the wheel into a throwaway env and use it"
TMPENV="$(mktemp -d)/venv"
python -m venv "$TMPENV"
if [ -d "$TMPENV/Scripts" ]; then BIN="$TMPENV/Scripts"; else BIN="$TMPENV/bin"; fi
"$BIN/pip" install --quiet dist/*.whl
"$BIN/python" - <<'PY'
import fxdub
from fxdub import audition_receipt, dialogue_receipt, media_probe, vo_graphs

assert fxdub.__version__, "package exposes no version"

# the builders must emit a runnable graph shape
graph = vo_graphs.mix("a.flac", "b.flac", "smoke/mix")
assert any(n["class_type"] == "AudioMix" for n in graph.values())
assert any(n["class_type"] == "SaveAudioAdvanced" for n in graph.values())

# the clone builder must use the RUNTIME slot name, not the advertised one
clone = vo_graphs.elevenlabs_clone_tts("ref.flac", "hi", "smoke/vo")
node = [n for n in clone.values() if n["class_type"] == "ElevenLabsInstantVoiceClone"][0]
assert "files.audio0" in node["inputs"], "clone builder regressed to the advertised slot name"

# the content verifier must reject speech the script never asked for
scene = {"clip_duration_s": 10.0, "lines": [{"speaker": "A", "text": "hello there"}]}
words = [
    {"text": "hello", "start": 0.0, "end": 0.4, "type": "word", "speaker_id": "s0"},
    {"text": "there", "start": 0.5, "end": 0.9, "type": "word", "speaker_id": "s0"},
    {"text": "surprise", "start": 1.2, "end": 1.8, "type": "word", "speaker_id": "s1"},
]
result = dialogue_receipt.check_dialogue(scene, words)
failed = {c["check"] for c in result["checks"] if not c["ok"]}
assert "no_invented_speech" in failed, "content verifier failed to catch invented speech"

print("smoke OK — version", fxdub.__version__)
PY

echo
echo "verify: PASS"
