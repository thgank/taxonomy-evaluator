"""Offline, deterministic evaluation of directed parent-to-child taxonomies."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import sys
import tempfile
import unicodedata
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

VERSION = "1.0.0"


def label(value):
    """Match NFC-normalized, case-folded labels with collapsed whitespace."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("concept labels must be nonempty strings")
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def unit_number(value):
    if isinstance(value, bool):
        raise ValueError("scores and thresholds must be numbers in [0, 1]")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("scores and thresholds must be numbers in [0, 1]") from exc
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError("scores and thresholds must be finite numbers in [0, 1]")
    return number


def load_taxonomy(path):
    """Read a label edge list or taxonomy-builder's ID-based JSON/CSV export."""
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    nodes, identifiers = set(), {}
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get("edges"), list):
            raise ValueError("JSON must be an object with an edges array")
        if "nodes" in data:
            if not isinstance(data["nodes"], list):
                raise ValueError("nodes must be an array of {id, label} objects")
            for node in data["nodes"]:
                if not isinstance(node, dict):
                    raise ValueError("each node must be an object")
                identifier = node.get("id")
                if not isinstance(identifier, str) or not identifier.strip():
                    raise ValueError("node IDs must be nonempty strings")
                name = label(node.get("label"))
                if identifier in identifiers or name in nodes:
                    raise ValueError("duplicate node IDs or normalized labels are ambiguous")
                identifiers[identifier] = name
                nodes.add(name)
        rows = data["edges"]
        id_based = "nodes" in data
    elif path.suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(text), strict=True)
        fields = set(reader.fieldnames or [])
        if len(fields) != len(reader.fieldnames or []):
            raise ValueError("CSV headers must be unique")
        if not ({"parent", "child"} <= fields or {"parent_label", "child_label"} <= fields):
            raise ValueError("CSV requires parent,child or parent_label,child_label headers")
        rows = list(reader)
        id_based = False
    else:
        raise ValueError("input must have a .json or .csv extension")

    edges, unscored = {}, 0
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"edge {index} must be an object")
        if None in row:
            raise ValueError(f"edge {index}: too many CSV columns")
        if row.get("relation", "is_a") != "is_a":
            raise ValueError(f"edge {index}: only is_a relations are supported")
        if id_based:
            parent, child = row.get("parent"), row.get("child")
            if not isinstance(parent, str) or not isinstance(child, str):
                raise ValueError(f"edge {index}: endpoints must be node IDs")
            if parent not in identifiers or child not in identifiers:
                raise ValueError(f"edge {index}: unknown node ID")
            pair = identifiers[parent], identifiers[child]
        else:
            pair = label(row.get("parent_label", row.get("parent"))), label(
                row.get("child_label", row.get("child"))
            )
        score = row.get("score")
        if score is None or score == "":
            unscored += 1
            score = 1.0
        score = unit_number(score)
        edges[pair] = max(edges.get(pair, 0.0), score)
        nodes.update(pair)
    return {
        "nodes": nodes, "edges": edges,
        "source": {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                   "edge_rows": len(rows), "duplicate_rows": len(rows) - len(edges),
                   "unscored_rows": unscored},
    }


def graph_metrics(nodes, edges):
    """Count weak components and calculate longest root-to-node depth for a DAG."""
    parents = {node: set() for node in sorted(nodes)}
    children = {node: set() for node in sorted(nodes)}
    for parent, child in edges:
        parents[child].add(parent)
        children[parent].add(child)
    unseen = set(nodes)
    component_sizes = []
    while unseen:
        stack, size = [unseen.pop()], 0
        while stack:
            node = stack.pop()
            size += 1
            neighbors = (parents[node] | children[node]) & unseen
            unseen.difference_update(neighbors)
            stack.extend(neighbors)
        component_sizes.append(size)
    depth, cycle = {}, []
    try:
        for node in TopologicalSorter({n: sorted(p) for n, p in parents.items()}).static_order():
            depth[node] = max((depth[p] + 1 for p in parents[node]), default=0)
    except CycleError as exc:
        cycle = exc.args[1]
    return {
        "node_count": len(nodes), "edge_count": len(edges),
        "roots": sorted(n for n in nodes if not parents[n]),
        "leaves": sorted(n for n in nodes if not children[n]),
        "isolated_nodes": sorted(n for n in nodes if not parents[n] and not children[n]),
        "multiple_parent_nodes": sorted(n for n in nodes if len(parents[n]) > 1),
        "component_count": len(component_sizes),
        "largest_component_ratio": max(component_sizes, default=0) / len(nodes) if nodes else None,
        "is_dag": not cycle, "cycle_example": cycle,
        "max_depth": None if cycle or not nodes else max(depth.values()),
    }


def evaluate(predicted, gold, threshold=0.0):
    threshold = unit_number(threshold)
    selected = {pair for pair, score in predicted["edges"].items() if score >= threshold}
    reference = set(gold["edges"])
    tp, fp, fn = selected & reference, selected - reference, reference - selected
    precision = len(tp) / len(selected) if selected else None
    recall = len(tp) / len(reference) if reference else None
    f1 = 2 * len(tp) / (len(selected) + len(reference)) if selected and reference else None
    return {
        "schema_version": 1, "tool_version": VERSION,
        "python_version": platform.python_version(), "threshold": threshold,
        "normalization": "NFC + casefold + collapsed whitespace; directed exact-label matching",
        "inputs": {"predicted": predicted["source"], "gold": gold["source"]},
        "metrics": {"true_positives": len(tp), "false_positives": len(fp),
                    "false_negatives": len(fn), "precision": precision, "recall": recall, "f1": f1},
        "errors": {"false_positive_edges": sorted(fp), "false_negative_edges": sorted(fn)},
        "predicted_graph": graph_metrics(predicted["nodes"], sorted(selected)),
        "gold_graph": graph_metrics(gold["nodes"], sorted(reference)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predicted", type=Path)
    parser.add_argument("gold", type=Path)
    parser.add_argument("--threshold", type=unit_number, default=0.0)
    parser.add_argument("--min-f1", type=unit_number, help="fail if F1 is undefined or below this value")
    parser.add_argument("--output", type=Path, help="write JSON atomically; otherwise use stdout")
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.resolve() in {args.predicted.resolve(), args.gold.resolve()}:
            raise ValueError("output must not overwrite an input")
        report = evaluate(load_taxonomy(args.predicted), load_taxonomy(args.gold), args.threshold)
        failures = []
        for name in ("predicted", "gold"):
            if not report[f"{name}_graph"]["is_dag"]:
                failures.append(f"{name} taxonomy contains a directed cycle")
        f1 = report["metrics"]["f1"]
        if args.min_f1 is not None and (f1 is None or f1 < args.min_f1):
            failures.append(f"F1 {f1} does not meet minimum {args.min_f1}")
        report["gate"] = {"passed": not failures, "failures": failures, "min_f1": args.min_f1}
        result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
                                                 delete=False) as stream:
                    temporary = stream.name
                    stream.write(result)
                os.replace(temporary, args.output)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
        else:
            sys.stdout.write(result)
        return 1 if failures else 0
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
