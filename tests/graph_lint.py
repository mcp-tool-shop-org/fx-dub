"""graph_lint — structural validation + defect detectors for archived ComfyUI graphs.

This is the executable form of the defect ledgers in
``workflows/comfy-cloud/as-built/README.md``. Each detector encodes one entry
from a ledger (or one trap from ``kb/fxdub.db``) and returns a list of
:class:`Finding` records — empty list means "clean".

The archived graphs are *provenance archives*: they are known-bad on purpose.
That is what makes them useful as fixtures — a detector that cannot go red on
the graph it was written for is theater, so ``tests/test_graphs.py`` asserts
that each detector fires on exactly the graphs the ledger says it should.

Editor format (what ``get_saved_workflow`` returns for a canvas tab)::

    {"nodes": [ {"id":.., "type":.., "inputs":[..], "outputs":[..],
                 "widgets_values": [..] | {..},
                 "widgets_values_named": {..}   # optional, preferred when present
                }, ... ],
     "links": [ [link_id, src_node_id, src_slot, dst_node_id, dst_slot, TYPE], ... ]}

* An ``inputs`` entry carries ``link``: a link id, or ``null`` when the value
  comes from the node's widget instead of a wire.
* An ``outputs`` entry carries ``links``: a list of link ids (possibly empty).
* ``widgets_values`` is positional when it is a list. Positions map onto the
  ``inputs`` entries that carry a ``widget`` marker, with one wrinkle: a seed
  widget is followed by an extra ``control_after_generate`` value that has no
  corresponding input. :func:`widget_values` handles both shapes and prefers
  ``widgets_values_named`` when the export supplies it.

API format (``*.api.json``, what ``/api/prompt`` consumes) is a flat dict of
node-id -> ``{"class_type": .., "inputs": {name: value | [node_id, slot]}}``.
"""

from __future__ import annotations

import glob
import json
import os
from collections import OrderedDict, namedtuple

# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS_BUILT_DIR = os.path.join(REPO_ROOT, "workflows", "comfy-cloud", "as-built")

#: The graph the v2.1 fix order is meant to produce. Absent until the Comfy
#: Agent builds it and we pull + archive it; the forward gate in
#: ``test_graphs.py`` skips while it is missing and turns into a hard
#: all-detectors-clean assertion the moment it lands.
V21_PATH = os.path.join(AS_BUILT_DIR, "fx-dub-v2.1.json")


def editor_graph_paths():
    """Every archived EDITOR-format graph (i.e. every ``*.json`` but ``*.api.json``)."""
    return sorted(
        p
        for p in glob.glob(os.path.join(AS_BUILT_DIR, "*.json"))
        if not p.endswith(".api.json")
    )


def api_graph_paths():
    """Every archived API-format graph (``*.api.json``)."""
    return sorted(glob.glob(os.path.join(AS_BUILT_DIR, "*.api.json")))


def load_graph(path):
    """Parse a graph JSON file (UTF-8; the exports carry emoji in output names)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

Finding = namedtuple("Finding", "code node_id detail")


def _f(code, node_id, detail):
    return Finding(code, node_id, detail)


def describe(findings):
    """Render findings for an assertion message."""
    return "; ".join("{0}@{1}: {2}".format(f.code, f.node_id, f.detail) for f in findings)


# --------------------------------------------------------------------------
# low-level accessors
# --------------------------------------------------------------------------

CONTROL_AFTER_GENERATE = frozenset({"fixed", "increment", "decrement", "randomize"})
SEED_WIDGET_NAMES = frozenset({"seed", "noise_seed", "rand_seed"})

#: Positional widget order for node types whose archived export omits the
#: per-input ``widget`` markers (the two standalone demo graphs do). Only node
#: types a detector actually reads widgets from need an entry here.
FALLBACK_WIDGET_ORDER = {
    "VHS_LoadVideo": [
        "video", "force_rate", "custom_width", "custom_height",
        "frame_load_cap", "skip_first_frames", "select_every_nth", "format",
    ],
    "Florence2Run": [
        "text_input", "task", "fill_mask", "keep_model_loaded", "max_new_tokens",
        "num_beams", "do_sample", "output_mask_select", "seed",
    ],
    "KSampler": ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "EmptyAceStepLatentAudio": ["seconds", "batch_size"],
    "EmptyAceStep1.5LatentAudio": ["seconds", "batch_size"],
}


def _clean(name):
    """Strip the editor's decorative non-ASCII from a socket name.

    ``VHS_VideoInfo`` names its outputs ``source_fps<colour-square emoji>``; the
    logical name is the ASCII part.
    """
    if not isinstance(name, str):
        return ""
    return "".join(ch for ch in name if ch.isascii()).strip()


def node_type(node):
    return node.get("type") or node.get("class_type") or ""


def graph_nodes(graph):
    ns = graph.get("nodes")
    return ns if isinstance(ns, list) else []


def nodes_of_type(graph, type_name):
    return [n for n in graph_nodes(graph) if node_type(n) == type_name]


def node_types(graph):
    return {node_type(n) for n in graph_nodes(graph)}


def node_index(graph):
    return {n.get("id"): n for n in graph_nodes(graph)}


def parse_link(entry):
    """Normalise one ``links`` entry into a dict, or ``None`` if unparseable.

    Handles the list form ``[id, src, src_slot, dst, dst_slot, TYPE]`` (what
    every archived graph uses) and the object form some editor builds emit.
    """
    if isinstance(entry, (list, tuple)) and len(entry) >= 5:
        return {
            "id": entry[0], "src": entry[1], "src_slot": entry[2],
            "dst": entry[3], "dst_slot": entry[4],
            "type": entry[5] if len(entry) > 5 else None,
        }
    if isinstance(entry, dict) and "id" in entry:
        return {
            "id": entry.get("id"),
            "src": entry.get("origin_id"), "src_slot": entry.get("origin_slot"),
            "dst": entry.get("target_id"), "dst_slot": entry.get("target_slot"),
            "type": entry.get("type"),
        }
    return None


def link_index(graph):
    """``{link_id: parsed_link}`` for every parseable link in the graph."""
    out = {}
    links = graph.get("links")
    if isinstance(links, list):
        for entry in links:
            link = parse_link(entry)
            if link is not None:
                out[link["id"]] = link
    return out


def widget_values(node):
    """Best-effort ``{widget_name: value}`` for a node.

    Prefers ``widgets_values_named``; falls back to a dict ``widgets_values``;
    finally maps a positional list onto the node's widget-marked inputs (or the
    :data:`FALLBACK_WIDGET_ORDER` table), skipping the phantom
    ``control_after_generate`` value that trails a seed widget.
    """
    named = node.get("widgets_values_named")
    if isinstance(named, dict):
        return dict(named)

    values = node.get("widgets_values")
    if isinstance(values, dict):
        return dict(values)
    if not isinstance(values, list):
        return {}

    names = [
        _clean(i.get("name"))
        for i in (node.get("inputs") or [])
        if isinstance(i, dict) and "widget" in i
    ]
    if not names:
        names = list(FALLBACK_WIDGET_ORDER.get(node_type(node), []))

    out = {}
    pos = 0
    for name in names:
        if pos >= len(values):
            break
        out[name] = values[pos]
        pos += 1
        if (
            name in SEED_WIDGET_NAMES
            and pos < len(values)
            and isinstance(values[pos], str)
            and values[pos] in CONTROL_AFTER_GENERATE
        ):
            pos += 1  # swallow control_after_generate
    return out


def widget(node, name, default=None):
    return widget_values(node).get(name, default)


def _as_number(value, default=None):
    """Coerce a widget value to a number; widgets are sometimes stringly typed."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value) if ("." in value or "e" in value.lower()) else int(value)
        except ValueError:
            return default
    return default


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return False


def input_source(graph, node, input_name, links=None):
    """``(src_node_id, src_slot)`` feeding a named input, or ``None`` if unwired."""
    links = link_index(graph) if links is None else links
    for inp in node.get("inputs") or []:
        if not isinstance(inp, dict) or _clean(inp.get("name")) != input_name:
            continue
        link_id = inp.get("link")
        if link_id is None:
            return None
        link = links.get(link_id)
        if link is None:
            return None
        return (link["src"], link["src_slot"])
    return None


def output_targets(graph, node, output_name, links=None):
    """``[(dst_node_id, dst_slot), ...]`` reachable in ONE hop from a named output."""
    links = link_index(graph) if links is None else links
    out = []
    for output in node.get("outputs") or []:
        if not isinstance(output, dict) or _clean(output.get("name")) != output_name:
            continue
        for link_id in output.get("links") or []:
            link = links.get(link_id)
            if link is not None:
                out.append((link["dst"], link["dst_slot"]))
    return out


def direct_targets_of_type(graph, node, output_name, target_type, index=None, links=None):
    """One-hop targets of ``output_name`` whose node type is ``target_type``."""
    index = node_index(graph) if index is None else index
    hits = []
    for dst_id, _slot in output_targets(graph, node, output_name, links=links):
        dst = index.get(dst_id)
        if dst is not None and node_type(dst) == target_type:
            hits.append(dst)
    return hits


# --------------------------------------------------------------------------
# structural validation
# --------------------------------------------------------------------------

def structural_findings(graph):
    """Editor-format integrity: nodes/links present, no dangling references."""
    out = []

    nodes = graph.get("nodes")
    links = graph.get("links")
    if not isinstance(nodes, list) or not nodes:
        out.append(_f("missing_nodes", None, "top-level 'nodes' is absent or empty"))
        return out
    if not isinstance(links, list):
        out.append(_f("missing_links", None, "top-level 'links' is absent or not a list"))
        return out

    ids = set()
    for node in nodes:
        if not isinstance(node, dict) or "id" not in node:
            out.append(_f("bad_node", None, "node entry is not an object with an id"))
            continue
        if not node_type(node):
            out.append(_f("untyped_node", node.get("id"), "node has no 'type'"))
        if node["id"] in ids:
            out.append(_f("duplicate_node_id", node["id"], "node id used more than once"))
        ids.add(node["id"])

    seen_links = {}
    for entry in links:
        link = parse_link(entry)
        if link is None:
            out.append(_f("bad_link_shape", None, "link entry is not [id, src, slot, dst, slot, TYPE]"))
            continue
        if link["id"] in seen_links:
            out.append(_f("duplicate_link_id", None, "link id {0} used more than once".format(link["id"])))
        seen_links[link["id"]] = link
        if link["src"] not in ids:
            out.append(_f("dangling_link_source", link["src"],
                          "link {0} originates at an unknown node".format(link["id"])))
        if link["dst"] not in ids:
            out.append(_f("dangling_link_target", link["dst"],
                          "link {0} targets an unknown node".format(link["id"])))

    for node in nodes:
        if not isinstance(node, dict):
            continue
        for inp in node.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            link_id = inp.get("link")
            if link_id is not None and link_id not in seen_links:
                out.append(_f("unknown_input_link", node.get("id"),
                              "input '{0}' cites link {1}, absent from 'links'".format(
                                  _clean(inp.get("name")), link_id)))
    return out


def is_api_link(value):
    """True when an API-format input value is a ``["<node_id>", slot]`` reference."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and not isinstance(value[0], bool)
        and isinstance(value[1], int)
        and not isinstance(value[1], bool)
    )


def api_structural_findings(api):
    """API-format integrity: every ``[node_id, slot]`` reference resolves."""
    out = []
    if not isinstance(api, dict) or not api:
        out.append(_f("missing_api_nodes", None, "API graph is not a non-empty object"))
        return out

    keys = {str(k) for k in api.keys()}
    for node_id, node in api.items():
        if not isinstance(node, dict):
            out.append(_f("bad_api_node", node_id, "node value is not an object"))
            continue
        if not node.get("class_type"):
            out.append(_f("missing_class_type", node_id, "node has no 'class_type'"))
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            out.append(_f("bad_api_inputs", node_id, "'inputs' is not an object"))
            continue
        for name, value in inputs.items():
            if is_api_link(value) and str(value[0]) not in keys:
                out.append(_f("dangling_api_reference", node_id,
                              "input '{0}' references missing node {1!r}".format(name, value[0])))
    return out


# --------------------------------------------------------------------------
# defect detectors  (one per ledger entry / trap)
# --------------------------------------------------------------------------

def pos_eq_neg(graph):
    """v2 F1 / trap: KSampler ``positive`` and ``negative`` share one source socket.

    ``neg + cfg*(pos-neg) == pos`` when they are equal — guidance is silently off.
    """
    out = []
    links = link_index(graph)
    for node in graph_nodes(graph):
        if "ksampler" not in node_type(node).lower():
            continue
        positive = input_source(graph, node, "positive", links=links)
        negative = input_source(graph, node, "negative", links=links)
        if positive is not None and positive == negative:
            out.append(_f("pos_eq_neg", node.get("id"),
                          "{0} positive and negative both come from node {1} slot {2}".format(
                              node_type(node), positive[0], positive[1])))
    return out


def deprecated_saveaudio(graph):
    """v1 ledger 3 / trap: masters must go through ``SaveAudioAdvanced``."""
    return [
        _f("deprecated_saveaudio", n.get("id"),
           "SaveAudio is deprecated; use SaveAudioAdvanced (FLAC/WAV)")
        for n in nodes_of_type(graph, "SaveAudio")
    ]


def caption_unsaved(graph):
    """v1 ledger 7 / trap: a STRING output reaches the manifest only via ``SaveText``."""
    out = []
    links = link_index(graph)
    index = node_index(graph)
    for node in nodes_of_type(graph, "Florence2Run"):
        savers = direct_targets_of_type(graph, node, "caption", "SaveText",
                                        index=index, links=links)
        if not savers:
            out.append(_f("caption_unsaved", node.get("id"),
                          "Florence2Run 'caption' has no SaveText sink — lost headlessly"))
    return out


def loader_skip_feeds_mux(graph):
    """v2 F3 / trap: loader frame knobs act on the ONE image stream.

    ``skip_first_frames`` set on a ``VHS_LoadVideo`` whose IMAGE also feeds the
    mux clips those frames off the delivered video, not just off the captioner.
    """
    out = []
    links = link_index(graph)
    index = node_index(graph)
    for node in nodes_of_type(graph, "VHS_LoadVideo"):
        skip = _as_number(widget(node, "skip_first_frames"), 0) or 0
        if skip <= 0:
            continue
        for mux in direct_targets_of_type(graph, node, "IMAGE", "VHS_VideoCombine",
                                          index=index, links=links):
            out.append(_f("loader_skip_feeds_mux", node.get("id"),
                          "skip_first_frames={0} on the loader also clips VHS_VideoCombine "
                          "node {1}".format(skip, mux.get("id"))))
    return out


def uncapped_florence(graph):
    """v1 ledger 8 / trap: every frame of the clip is captioned.

    ``frame_load_cap == 0`` + ``select_every_nth == 1`` with the loader's IMAGE
    wired straight into ``Florence2Run`` — no ``VHS_SelectEveryNthImage``
    subsampler on the caption branch.
    """
    out = []
    links = link_index(graph)
    index = node_index(graph)
    for node in nodes_of_type(graph, "VHS_LoadVideo"):
        cap = _as_number(widget(node, "frame_load_cap"), None)
        nth = _as_number(widget(node, "select_every_nth"), None)
        if cap != 0 or nth != 1:
            continue
        for run in direct_targets_of_type(graph, node, "IMAGE", "Florence2Run",
                                          index=index, links=links):
            out.append(_f("uncapped_florence", node.get("id"),
                          "frame_load_cap=0 + select_every_nth=1 feeds EVERY frame straight "
                          "into Florence2Run node {0}".format(run.get("id"))))
    return out


def florence_nondeterministic(graph):
    """v1 ledger 2 / trap: ``do_sample=true`` breaks pinned-seed caption replay."""
    out = []
    for node in nodes_of_type(graph, "Florence2Run"):
        if _as_bool(widget(node, "do_sample", False)):
            out.append(_f("florence_nondeterministic", node.get("id"),
                          "Florence2Run do_sample=true — captions are not reproducible"))
    return out


def ace15_wrong_latent(graph):
    """v2 blocker: the ACE-Step 1.5 encoder paired with the 1.0 latent node."""
    types = node_types(graph)
    if "TextEncodeAceStepAudio1.5" not in types:
        return []
    if "EmptyAceStep1.5LatentAudio" in types:
        return []
    return [
        _f("ace15_wrong_latent", n.get("id"),
           "TextEncodeAceStepAudio1.5 present but the latent is EmptyAceStepLatentAudio "
           "(the 1.0 node); use EmptyAceStep1.5LatentAudio")
        for n in nodes_of_type(graph, "EmptyAceStepLatentAudio")
    ]


#: Detector registry — name -> callable. ``test_graphs.py`` drives the red-gate
#: matrix off this, so a new detector is covered the moment it lands here.
DETECTORS = OrderedDict([
    ("pos_eq_neg", pos_eq_neg),
    ("deprecated_saveaudio", deprecated_saveaudio),
    ("caption_unsaved", caption_unsaved),
    ("loader_skip_feeds_mux", loader_skip_feeds_mux),
    ("uncapped_florence", uncapped_florence),
    ("florence_nondeterministic", florence_nondeterministic),
    ("ace15_wrong_latent", ace15_wrong_latent),
])


def run_all(graph):
    """``{detector_name: [Finding, ...]}`` for every registered detector."""
    return OrderedDict((name, fn(graph)) for name, fn in DETECTORS.items())


def fired(graph):
    """Names of the detectors that produced at least one finding."""
    return {name for name, findings in run_all(graph).items() if findings}


# --------------------------------------------------------------------------
# API-format detectors (session 4, 2026-08-22)
# --------------------------------------------------------------------------
# The working fx-dub pipeline is hand-authored API JSON submitted via
# ``submit_workflow``, not a saved canvas tab -- so the traps earned while
# building it are API-shaped and the editor-format DETECTORS above cannot see
# them. These run against ``{node_id: {"class_type":.., "inputs": {..}}}``.
#
# Every one of these cost a real failed job or a rejected take.


#: Auto-grow list inputs whose RUNTIME slot names differ from what ``get_node``
#: advertises. The node spec calls the container ``COMFY_AUTOGROW_V3`` and shows
#: a slot named ``<field>.item_1``; the executor wants ``<field>.audio0``. A
#: ``dry_run`` accepts the wrong name -- pre-flight only checks that link targets
#: exist -- so this is invisible until the job fails at execution.
AUTOGROW_SLOT_NAMES = {
    "ElevenLabsInstantVoiceClone": ("files", "audio0"),
    "FishAudioInstantVoiceClone": ("files", "audio0"),
}

#: Nodes that are broken on Comfy Cloud regardless of wiring. ``AudioPad`` raises
#: ``UnboundLocalError: pad_samples`` inside the node on every call (measured
#: 2026-08-22). Use ``EmptyAudio`` + ``AudioConcat`` to place a clip on a
#: timeline instead.
BROKEN_ON_CLOUD = {
    "AudioPad": "raises UnboundLocalError: pad_samples; use EmptyAudio + AudioConcat",
}


def api_nodes_of_type(api, type_name):
    if not isinstance(api, dict):
        return []
    return [
        (node_id, node) for node_id, node in api.items()
        if isinstance(node, dict) and node.get("class_type") == type_name
    ]


def api_autogrow_slot_name(api):
    """Auto-grow slot addressed by its advertised name instead of its runtime name."""
    out = []
    for class_type, (field, runtime) in AUTOGROW_SLOT_NAMES.items():
        for node_id, node in api_nodes_of_type(api, class_type):
            inputs = node.get("inputs") or {}
            if not isinstance(inputs, dict):
                continue
            bad = [k for k in inputs if k.startswith(field + ".") and not k.startswith(field + "." + runtime[:-1])]
            if bad:
                out.append(_f("api_autogrow_slot_name", node_id,
                              "{0} addresses {1}; the runtime wants {2}.{3}, {4}, ... "
                              "(dry_run does NOT catch this)".format(
                                  class_type, ", ".join(sorted(bad)), field, runtime,
                                  field + "." + runtime[:-1] + "1")))
    return out


def api_fish_autogrow_voices(api):
    """FishAudioTextToSpeech addressing the s2.1-pro voices list by its spec name."""
    out = []
    for node_id, node in api_nodes_of_type(api, "FishAudioTextToSpeech"):
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        bad = [k for k in inputs if k.startswith("model.voices.item_")]
        if bad:
            out.append(_f("api_fish_autogrow_voices", node_id,
                          "model.voices.item_N is rejected at execution "
                          "('unexpected keyword argument'); use model 's1' with "
                          "model.voice, or discover the runtime slot name first"))
    return out


def api_broken_node(api):
    """A node that fails on Comfy Cloud no matter how it is wired."""
    out = []
    for class_type, why in BROKEN_ON_CLOUD.items():
        for node_id, _node in api_nodes_of_type(api, class_type):
            out.append(_f("api_broken_node", node_id,
                          "{0} is broken on Comfy Cloud: {1}".format(class_type, why)))
    return out


def api_bytedance_global_pitch_multivoice(api):
    """ByteDance asked to voice two characters while pitch_rate is non-zero.

    ``pitch_rate`` is a NODE-level knob, so it shifts every speaker in the
    prompt by the same interval -- the two characters collapse toward one voice.
    Render one pass per character (the timestamps are an absolute timeline, so
    the passes layer) and give each its own pitch.
    """
    out = []
    for node_id, node in api_nodes_of_type(api, "ByteDanceSeedAudio"):
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        pitch = _as_number(inputs.get("pitch_rate"), 0) or 0
        prompt = inputs.get("text_prompt")
        if not isinstance(prompt, str) or pitch == 0:
            continue
        speakers = set()
        for line in prompt.splitlines():
            # a timestamp prefix carries its own colon -- "[0.4s:2.0s] MAC: ..."
            body = line.split("]", 1)[1] if line.lstrip().startswith("[") and "]" in line else line
            if ":" not in body:
                continue
            label = body.split(":", 1)[0].strip()
            if label.isupper() and 0 < len(label) <= 16:
                speakers.add(label)
        if len(speakers) > 1:
            out.append(_f("api_bytedance_global_pitch_multivoice", node_id,
                          "pitch_rate={0} applies to all of {1}; render one pass per "
                          "character instead".format(pitch, ", ".join(sorted(speakers)))))
    return out


def api_bytedance_reference_unverified(api):
    """ByteDance in audio-reference mode, which re-speaks the reference's lines.

    Not a wiring defect -- a mandatory-verification marker. In ``audio reference``
    mode the model reproduces the reference clip's DIALOGUE CONTENT, not just its
    timbre, so a multi-line reference yields lines the prompt never asked for.
    Any such render must be gated by ``tools/dialogue_receipt.py --only-speaker``.
    """
    out = []
    for node_id, node in api_nodes_of_type(api, "ByteDanceSeedAudio"):
        inputs = node.get("inputs") or {}
        if isinstance(inputs, dict) and inputs.get("reference_mode") == "audio reference":
            out.append(_f("api_bytedance_reference_unverified", node_id,
                          "audio-reference render reproduces the reference's dialogue "
                          "content; gate the output with dialogue_receipt --only-speaker"))
    return out


#: API detector registry. Kept separate from DETECTORS because the graph shape
#: differs; ``test_graphs.py`` drives both.
API_DETECTORS = OrderedDict([
    ("api_autogrow_slot_name", api_autogrow_slot_name),
    ("api_fish_autogrow_voices", api_fish_autogrow_voices),
    ("api_broken_node", api_broken_node),
    ("api_bytedance_global_pitch_multivoice", api_bytedance_global_pitch_multivoice),
    ("api_bytedance_reference_unverified", api_bytedance_reference_unverified),
])


def run_all_api(api):
    """``{detector_name: [Finding, ...]}`` for every registered API detector."""
    return OrderedDict((name, fn(api)) for name, fn in API_DETECTORS.items())


def fired_api(api):
    """Names of the API detectors that produced at least one finding."""
    return {name for name, findings in run_all_api(api).items() if findings}
