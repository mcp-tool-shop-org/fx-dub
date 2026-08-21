"""The archived ComfyUI graphs — structural validation + red-gate defect detectors.

Two jobs here.

**Structure.** Every graph in ``workflows/comfy-cloud/as-built/`` must parse and
be internally consistent: links point at nodes that exist, and every input that
cites a link id cites one that is actually in ``links``. The ``.api.json`` gets
the API-format equivalent — every ``["<node_id>", slot]`` reference resolves.

**Defects.** ``workflows/comfy-cloud/as-built/README.md`` carries two prose
defect ledgers (v1's ten items, v2's F1-F5). This module turns them into
executable detectors and then proves each one *fires* on the archived graph the
ledger indicts. That is the whole point: the archives are known-bad provenance
copies, so a detector that stays green on them is theater. The gate must go red.

The forward gate (:class:`Fxdub21ForwardGateTests`) is the inverse — when the
v2.1 graph is built and archived, every detector must be silent on it. It skips
with a clear message while that file is absent.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:  # importable under `unittest discover` and pytest alike
    sys.path.insert(0, _HERE)

import graph_lint  # noqa: E402  (path shim above must run first)
from graph_lint import describe  # noqa: E402

AS_BUILT_DIR = graph_lint.AS_BUILT_DIR


def _path(name):
    return os.path.join(AS_BUILT_DIR, name)


#: The ledger, as a matrix. Keys are file names in as-built/; values say which
#: detectors MUST go red on that archive and which MUST stay green.
RED_GATE = {
    "describe-a-video-florence2.json": {
        # v1 ledger items 3, 7, 8, 2 respectively.
        "must_fire": {
            "deprecated_saveaudio",
            "caption_unsaved",
            "uncapped_florence",
            "florence_nondeterministic",
        },
        # v1 wired a separate negative encoder — the CFG bug is a v2 regression.
        "must_not_fire": {"pos_eq_neg"},
    },
    "demo-sfx-ace-step.json": {
        "must_fire": {"deprecated_saveaudio"},
        "must_not_fire": {"pos_eq_neg"},
    },
    "demo-dialogue-chatterbox.json": {
        "must_fire": {"deprecated_saveaudio"},
        "must_not_fire": set(),
    },
    "fx-dub-v2.json": {
        # v2 blockers F1, F3, the unfixed cost trap, and the 1.5/1.0 latent mismatch.
        "must_fire": {
            "pos_eq_neg",
            "loader_skip_feeds_mux",
            "uncapped_florence",
            "ace15_wrong_latent",
        },
        # v2 delivered these fixes as briefed — they must stay fixed.
        "must_not_fire": {
            "deprecated_saveaudio",
            "florence_nondeterministic",
            "caption_unsaved",
        },
    },
}

DETECTOR_NAMES = set(graph_lint.DETECTORS)


class ArchiveInventoryTests(unittest.TestCase):
    """The fixtures the rest of this module depends on are actually present."""

    def test_as_built_directory_exists(self):
        self.assertTrue(os.path.isdir(AS_BUILT_DIR), AS_BUILT_DIR)

    def test_editor_graphs_present(self):
        found = {os.path.basename(p) for p in graph_lint.editor_graph_paths()}
        self.assertTrue(found, "no editor-format graphs archived")
        for name in RED_GATE:
            with self.subTest(graph=name):
                self.assertIn(name, found)

    def test_api_graph_present(self):
        found = {os.path.basename(p) for p in graph_lint.api_graph_paths()}
        self.assertIn("fx-dub-v2.api.json", found)

    def test_red_gate_matrix_only_names_real_detectors(self):
        for name, spec in RED_GATE.items():
            with self.subTest(graph=name):
                named = spec["must_fire"] | spec["must_not_fire"]
                self.assertTrue(
                    named <= DETECTOR_NAMES,
                    "unknown detector(s): {0}".format(sorted(named - DETECTOR_NAMES)))
                self.assertFalse(
                    spec["must_fire"] & spec["must_not_fire"],
                    "a detector cannot be required to both fire and stay silent")


class EditorGraphStructureTests(unittest.TestCase):
    """Every editor-format archive parses and holds together."""

    def test_every_editor_graph_parses(self):
        for path in graph_lint.editor_graph_paths():
            with self.subTest(graph=os.path.basename(path)):
                try:
                    graph = graph_lint.load_graph(path)
                except json.JSONDecodeError as exc:
                    self.fail("{0} is not valid JSON: {1}".format(path, exc))
                self.assertIsInstance(graph, dict)

    def test_every_editor_graph_has_nodes_and_links(self):
        for path in graph_lint.editor_graph_paths():
            with self.subTest(graph=os.path.basename(path)):
                graph = graph_lint.load_graph(path)
                self.assertIsInstance(graph.get("nodes"), list)
                self.assertIsInstance(graph.get("links"), list)
                self.assertGreater(len(graph["nodes"]), 0)

    def test_every_editor_graph_is_structurally_sound(self):
        for path in graph_lint.editor_graph_paths():
            with self.subTest(graph=os.path.basename(path)):
                findings = graph_lint.structural_findings(graph_lint.load_graph(path))
                self.assertEqual([], findings, describe(findings))

    def test_every_node_carries_an_id_and_a_type(self):
        for path in graph_lint.editor_graph_paths():
            graph = graph_lint.load_graph(path)
            for node in graph_lint.graph_nodes(graph):
                with self.subTest(graph=os.path.basename(path), node=node.get("id")):
                    self.assertIsNotNone(node.get("id"))
                    self.assertTrue(graph_lint.node_type(node))


class ApiGraphStructureTests(unittest.TestCase):
    """The API-format archive is the form ``/api/prompt`` would actually eat."""

    def setUp(self):
        self.path = _path("fx-dub-v2.api.json")
        if not os.path.exists(self.path):
            self.skipTest("fx-dub-v2.api.json is not archived")
        self.api = graph_lint.load_graph(self.path)

    def test_api_graph_is_a_node_map(self):
        self.assertIsInstance(self.api, dict)
        self.assertGreater(len(self.api), 0)
        for node_id, node in self.api.items():
            with self.subTest(node=node_id):
                self.assertIsInstance(node, dict)
                self.assertIn("class_type", node)

    def test_api_references_resolve(self):
        findings = graph_lint.api_structural_findings(self.api)
        self.assertEqual([], findings, describe(findings))

    def test_api_and_editor_archives_describe_the_same_graph(self):
        """The two v2 archives are the same workflow in two serialisations."""
        editor = graph_lint.load_graph(_path("fx-dub-v2.json"))
        editor_ids = {str(n.get("id")) for n in graph_lint.graph_nodes(editor)}
        api_ids = {str(k) for k in self.api}
        self.assertEqual(
            editor_ids, api_ids,
            "editor/API node id sets diverge — one archive is stale")

        editor_types = sorted(graph_lint.node_type(n) for n in graph_lint.graph_nodes(editor))
        api_types = sorted(n.get("class_type") for n in self.api.values())
        self.assertEqual(editor_types, api_types)


class DetectorRobustnessTests(unittest.TestCase):
    """Detectors must survive every archived graph shape without blowing up."""

    def test_every_detector_runs_on_every_editor_graph(self):
        for path in graph_lint.editor_graph_paths():
            graph = graph_lint.load_graph(path)
            for name, detector in graph_lint.DETECTORS.items():
                with self.subTest(graph=os.path.basename(path), detector=name):
                    findings = detector(graph)
                    self.assertIsInstance(findings, list)
                    for finding in findings:
                        self.assertIsInstance(finding, graph_lint.Finding)
                        self.assertTrue(finding.detail, "finding carries no explanation")

    def test_detectors_are_silent_on_an_empty_graph(self):
        empty = {"nodes": [], "links": []}
        for name, detector in graph_lint.DETECTORS.items():
            with self.subTest(detector=name):
                self.assertEqual([], detector(empty))

    def test_widget_values_prefers_named_over_positional(self):
        """Positional widget lists must decode to the same values as the named dict."""
        graph = graph_lint.load_graph(_path("fx-dub-v2.json"))
        florence = graph_lint.nodes_of_type(graph, "Florence2Run")[0]
        named = dict(florence["widgets_values_named"])
        self.assertEqual(graph_lint.widget_values(florence)["do_sample"], named["do_sample"])

        positional = dict(florence)
        positional.pop("widgets_values_named")
        decoded = graph_lint.widget_values(positional)
        for key in ("task", "max_new_tokens", "num_beams", "do_sample", "seed"):
            with self.subTest(widget=key):
                self.assertEqual(decoded[key], named[key])

    def test_widget_values_skips_control_after_generate(self):
        """A seed widget is trailed by a phantom control value with no input socket."""
        graph = graph_lint.load_graph(_path("describe-a-video-florence2.json"))
        sampler = graph_lint.nodes_of_type(graph, "KSampler")[0]
        values = graph_lint.widget_values(sampler)
        self.assertEqual(values.get("seed"), 0)
        self.assertEqual(values.get("steps"), 50)          # not the string "fixed"
        self.assertEqual(values.get("sampler_name"), "euler")


class RedGateTests(unittest.TestCase):
    """The point of the suite: the detectors go red on the known-bad archives."""

    def test_documented_defects_fire(self):
        for name, spec in sorted(RED_GATE.items()):
            path = _path(name)
            if not os.path.exists(path):
                self.fail("archived graph {0} is missing".format(name))
            fired = graph_lint.fired(graph_lint.load_graph(path))
            for detector in sorted(spec["must_fire"]):
                with self.subTest(graph=name, detector=detector):
                    self.assertIn(
                        detector, fired,
                        "{0} did NOT fire on {1}, but the defect ledger documents it there — "
                        "the detector cannot fail on known-bad input".format(detector, name))

    def test_fixed_defects_stay_green(self):
        for name, spec in sorted(RED_GATE.items()):
            path = _path(name)
            if not os.path.exists(path):
                self.fail("archived graph {0} is missing".format(name))
            results = graph_lint.run_all(graph_lint.load_graph(path))
            for detector in sorted(spec["must_not_fire"]):
                with self.subTest(graph=name, detector=detector):
                    self.assertEqual(
                        [], results[detector],
                        "{0} fired on {1}, which the ledger says is clean here: {2}".format(
                            detector, name, describe(results[detector])))

    def test_every_detector_fires_somewhere_in_the_archive(self):
        """No detector is dead code — each one is proven against a real bad graph."""
        proven = set()
        for path in graph_lint.editor_graph_paths():
            proven |= graph_lint.fired(graph_lint.load_graph(path))
        missing = DETECTOR_NAMES - proven
        self.assertEqual(
            set(), missing,
            "detector(s) never demonstrated red on any archived graph: {0}".format(sorted(missing)))


class LedgerSpecificTests(unittest.TestCase):
    """Spot checks that pin the exact wiring each ledger entry describes."""

    def setUp(self):
        self.v1 = graph_lint.load_graph(_path("describe-a-video-florence2.json"))
        self.v2 = graph_lint.load_graph(_path("fx-dub-v2.json"))

    def test_v2_cfg_cancels_because_both_conditioning_inputs_share_a_socket(self):
        findings = graph_lint.pos_eq_neg(self.v2)
        self.assertEqual(1, len(findings), describe(findings))
        sampler = graph_lint.node_index(self.v2)[findings[0].node_id]
        positive = graph_lint.input_source(self.v2, sampler, "positive")
        negative = graph_lint.input_source(self.v2, sampler, "negative")
        self.assertEqual(positive, negative)
        source = graph_lint.node_index(self.v2)[positive[0]]
        self.assertEqual("TextEncodeAceStepAudio1.5", graph_lint.node_type(source))

    def test_v2_caption_reaches_a_savetext(self):
        """v1 ledger item 7 was fixed in v2 — the caption is archived to fxdub/caption."""
        florence = graph_lint.nodes_of_type(self.v2, "Florence2Run")[0]
        savers = graph_lint.direct_targets_of_type(self.v2, florence, "caption", "SaveText")
        self.assertEqual(1, len(savers))
        self.assertEqual("fxdub/caption", graph_lint.widget(savers[0], "filename_prefix"))

    def test_v2_still_has_no_subsampler_on_the_caption_branch(self):
        """The cost trap is unfixed in v2: no VHS_SelectEveryNthImage anywhere."""
        self.assertNotIn("VHS_SelectEveryNthImage", graph_lint.node_types(self.v2))

    def test_v2_pairs_the_15_encoder_with_the_10_latent(self):
        types = graph_lint.node_types(self.v2)
        self.assertIn("TextEncodeAceStepAudio1.5", types)
        self.assertIn("EmptyAceStepLatentAudio", types)
        self.assertNotIn("EmptyAceStep1.5LatentAudio", types)

    def test_v1_captioner_is_the_non_deterministic_base_model(self):
        loader = graph_lint.nodes_of_type(self.v1, "DownloadAndLoadFlorence2Model")[0]
        self.assertEqual("microsoft/Florence-2-base", graph_lint.widget(loader, "model"))
        florence = graph_lint.nodes_of_type(self.v1, "Florence2Run")[0]
        self.assertTrue(graph_lint.widget(florence, "do_sample"))

    def test_v2_captioner_is_pinned(self):
        loader = graph_lint.nodes_of_type(self.v2, "DownloadAndLoadFlorence2Model")[0]
        self.assertEqual("microsoft/Florence-2-large", graph_lint.widget(loader, "model"))
        florence = graph_lint.nodes_of_type(self.v2, "Florence2Run")[0]
        self.assertFalse(graph_lint.widget(florence, "do_sample"))
        self.assertEqual(1, graph_lint.widget(florence, "seed"))

    def test_v2_masters_go_through_the_blessed_saver(self):
        self.assertEqual([], graph_lint.deprecated_saveaudio(self.v2))
        self.assertEqual(3, len(graph_lint.nodes_of_type(self.v2, "SaveAudioAdvanced")))


class Fxdub21ForwardGateTests(unittest.TestCase):
    """The forward gate: v2.1 must land with every detector silent."""

    def setUp(self):
        if not os.path.exists(graph_lint.V21_PATH):
            self.skipTest(
                "forward gate idle: {0} not archived yet (v2.1 is ordered in "
                "docs/briefs/2026-08-21-fxdub-04-brief.md but not yet built + pulled). "
                "These tests turn into a hard gate the moment the file lands.".format(
                    os.path.basename(graph_lint.V21_PATH)))
        self.graph = graph_lint.load_graph(graph_lint.V21_PATH)

    def test_v21_is_structurally_sound(self):
        findings = graph_lint.structural_findings(self.graph)
        self.assertEqual([], findings, describe(findings))

    def test_v21_trips_no_detector(self):
        for name, findings in graph_lint.run_all(self.graph).items():
            with self.subTest(detector=name):
                self.assertEqual(
                    [], findings,
                    "v2.1 still trips {0}: {1}".format(name, describe(findings)))

    def test_v21_gate_is_not_vacuous(self):
        """A green gate on a graph with nothing to inspect would be theatre too.

        Every detector must have had something to chew on: the node types it
        watches are present, so "no findings" means "fixed", not "absent".
        """
        types = graph_lint.node_types(self.graph)
        for required in ("VHS_LoadVideo", "Florence2Run", "KSampler",
                         "VHS_VideoCombine", "SaveText", "TextEncodeAceStepAudio1.5"):
            with self.subTest(node_type=required):
                self.assertIn(required, types)

        sampler = graph_lint.nodes_of_type(self.graph, "KSampler")[0]
        positive = graph_lint.input_source(self.graph, sampler, "positive")
        negative = graph_lint.input_source(self.graph, sampler, "negative")
        self.assertIsNotNone(positive, "KSampler positive is unwired — pos_eq_neg had no input")
        self.assertIsNotNone(negative, "KSampler negative is unwired — pos_eq_neg had no input")
        self.assertNotEqual(positive, negative)

    def test_v21_applies_the_briefed_fixes(self):
        """F1/F3 and the cost trap are fixed by construction, not by omission."""
        index = graph_lint.node_index(self.graph)

        # F1: the negative branch is a real ConditioningZeroOut, per the reference stack.
        sampler = graph_lint.nodes_of_type(self.graph, "KSampler")[0]
        negative = graph_lint.input_source(self.graph, sampler, "negative")
        self.assertEqual("ConditioningZeroOut", graph_lint.node_type(index[negative[0]]))

        # F3 / cost trap: the captioner sits behind a subsampler while the loader's
        # IMAGE still reaches the mux intact.
        loader = graph_lint.nodes_of_type(self.graph, "VHS_LoadVideo")[0]
        downstream = {
            graph_lint.node_type(index[dst])
            for dst, _slot in graph_lint.output_targets(self.graph, loader, "IMAGE")
        }
        self.assertIn("VHS_SelectEveryNthImage", downstream)
        self.assertIn("VHS_VideoCombine", downstream)
        self.assertNotIn("Florence2Run", downstream)

        florence = graph_lint.nodes_of_type(self.graph, "Florence2Run")[0]
        image_src = graph_lint.input_source(self.graph, florence, "image")
        self.assertEqual("VHS_SelectEveryNthImage", graph_lint.node_type(index[image_src[0]]))

        # The ACE 1.5 stack: split-file loaders and the matching 1.5 latent.
        types = graph_lint.node_types(self.graph)
        self.assertIn("EmptyAceStep1.5LatentAudio", types)
        self.assertNotIn("EmptyAceStepLatentAudio", types)


if __name__ == "__main__":
    unittest.main()
