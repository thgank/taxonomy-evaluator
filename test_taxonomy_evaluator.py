"""Small scientific regression suite; run with python -m unittest -v."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from taxonomy_evaluator import evaluate, graph_metrics, label, load_taxonomy, unit_number

ROOT = Path(__file__).resolve().parent


class EvaluationTests(unittest.TestCase):
    def test_known_counts_and_threshold(self):
        predicted = load_taxonomy(ROOT / "examples/predicted.csv")
        gold = load_taxonomy(ROOT / "examples/gold.csv")
        report = evaluate(predicted, gold)
        self.assertEqual(report["metrics"]["true_positives"], 5)
        self.assertEqual(report["metrics"]["false_positives"], 1)
        self.assertEqual(report["metrics"]["false_negatives"], 1)
        self.assertAlmostEqual(report["metrics"]["f1"], 5 / 6)
        filtered = evaluate(predicted, gold, 0.5)
        self.assertEqual(filtered["metrics"]["precision"], 1)
        self.assertAlmostEqual(filtered["metrics"]["f1"], 10 / 11)

    def test_export_formats_duplicates_unicode_and_isolates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.json"
            path.write_text(json.dumps({"nodes": [
                {"id": "a", "label": " ENERGY "}, {"id": "b", "label": "Solar  Energy"},
                {"id": "c", "label": "isolated"}], "edges": [
                {"parent": "a", "child": "b", "score": 0.2},
                {"parent": "a", "child": "b", "score": 0.9}]}), encoding="utf-8")
            taxonomy = load_taxonomy(path)
            self.assertEqual(taxonomy["edges"], {("energy", "solar energy"): 0.9})
            self.assertEqual(taxonomy["source"]["duplicate_rows"], 1)
            self.assertEqual(graph_metrics(taxonomy["nodes"], taxonomy["edges"])["isolated_nodes"], ["isolated"])
            path = Path(directory) / "export.csv"
            path.write_text('parent_id,parent_label,child_id,child_label,relation,score\na,"energy, systems",b,solar,is_a,0.9\n', encoding="utf-8-sig")
            self.assertIn(("energy, systems", "solar"), load_taxonomy(path)["edges"])
            path = Path(directory) / "labels.json"
            path.write_text('{"edges": [{"parent": "Énergie", "child": "éolienne"}]}', encoding="utf-8")
            self.assertEqual(load_taxonomy(path)["source"]["unscored_rows"], 1)
        self.assertEqual(label("E\u0301NERGIE"), label("Énergie"))
        self.assertEqual(label(" Қуат  сақтау "), "қуат сақтау")

    def test_graph_direction_cycles_components_and_longest_depth(self):
        edges = [("a", "b"), ("a", "c"), ("b", "c"), ("c", "d")]
        graph = graph_metrics(set("abcde"), edges)
        self.assertEqual(graph["max_depth"], 3)
        self.assertEqual(graph["component_count"], 2)
        self.assertEqual(graph["multiple_parent_nodes"], ["c"])
        cyclic = graph_metrics(set("abcde"), edges + [("d", "b")])
        self.assertFalse(cyclic["is_dag"])
        self.assertIsNone(cyclic["max_depth"])
        self.assertTrue(cyclic["cycle_example"])
        self.assertFalse(graph_metrics({"a"}, [("a", "a")])["is_dag"])
        chain = [(str(i), str(i + 1)) for i in range(1500)]
        self.assertEqual(graph_metrics({str(i) for i in range(1501)}, chain)["max_depth"], 1500)
        def taxonomy(pairs):
            return {"nodes": set("ab"), "edges": dict.fromkeys(pairs, 1), "source": {}}
        self.assertEqual(evaluate(taxonomy([("b", "a")]), taxonomy([("a", "b")]))["metrics"]["true_positives"], 0)

    def test_empty_inputs_and_invalid_data(self):
        empty = {"nodes": set(), "edges": {}, "source": {}}
        self.assertIsNone(evaluate(empty, empty)["metrics"]["f1"])
        self.assertIsNone(graph_metrics(set(), [])["max_depth"])
        for value in (float("nan"), float("inf"), -0.1, 1.1, True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                unit_number(value)
        bad_inputs = [
            '[]', '{"edges": [{"parent": "", "child": "x"}]}',
            '{"edges": [{"parent": "a", "child": "b", "score": "NaN"}]}',
            '{"nodes": [{"id": "a", "label": "x"}], "edges": [{"parent": "a", "child": "b"}]}',
            '{"nodes": [{"id": "a", "label": "x"}, {"id": "b", "label": "X"}], "edges": []}',
            '{"edges": [{"parent": "a", "child": "b", "relation": "part_of"}]}',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in bad_inputs:
                path.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ValueError):
                    load_taxonomy(path)

    def test_cli_gates_invalid_arguments_and_input_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            command = [sys.executable, str(ROOT / "taxonomy_evaluator.py"),
                       str(ROOT / "examples/predicted.csv"), str(ROOT / "examples/gold.csv")]
            passed = subprocess.run(command + ["--threshold", "0.5", "--min-f1", "0.9", "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertTrue(json.loads(output.read_text())["gate"]["passed"])
            failed = subprocess.run(command + ["--min-f1", "0.9"], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertFalse(json.loads(failed.stdout)["gate"]["passed"])
            for arguments in (["--threshold", "nan"], ["--output", command[2]]):
                invalid = subprocess.run(command + arguments, capture_output=True, text=True)
                self.assertEqual(invalid.returncode, 2)
                self.assertNotIn("Traceback", invalid.stderr)
            cyclic = Path(directory) / "cycle.csv"
            cyclic.write_text("parent,child\na,b\nb,a\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "taxonomy_evaluator.py"), str(cyclic), command[3]], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("directed cycle", json.loads(result.stdout)["gate"]["failures"][0])


if __name__ == "__main__":
    unittest.main()
