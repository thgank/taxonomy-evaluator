# Taxonomy Evaluator

**Author:** Nursultan Serikov (group CSE-2501M).

A small scientific command-line tool for evaluating generated taxonomies against an expert reference. Python 3.11+, standard library only; no installation or network connection is needed to run it.

This is an independent companion to [taxonomy-builder](https://github.com/thgank/taxonomy-builder). That system generates and reviews taxonomies; this tool benchmarks exported parent-to-child relations against an external gold standard. All implementation and demonstration data here are original. The examples are **synthetic**, not dissertation results.

## Run

```sh
python3 taxonomy_evaluator.py examples/predicted.csv examples/gold.csv
python3 taxonomy_evaluator.py examples/predicted.csv examples/gold.csv --threshold 0.5 --min-f1 0.9 --output evaluation.json
python3 -m unittest -v
```

The baseline has 5 correct edges, 1 extra edge, and 1 missing edge: precision = recall = F1 = 0.833333. At threshold 0.5, precision = 1.0, recall = 0.833333, and F1 = 0.909091. These values demonstrate the implementation; they do not establish scientific validity on real corpora.

## Input formats

UTF-8 CSV accepts `parent,child,score` or taxonomy-builder's `parent_id,parent_label,child_id,child_label,relation,score`. Scores are optional. Each directed edge means **child is a kind of parent**. Only `is_a` relations are accepted.

Label-based JSON:

```json
{"edges": [{"parent": "energy", "child": "solar energy", "score": 0.9}]}
```

Taxonomy-builder JSON (IDs are resolved to labels):

```json
{"nodes": [{"id": "a", "label": "energy"}, {"id": "b", "label": "solar energy"}], "edges": [{"parent": "a", "child": "b", "score": 0.9}]}
```

The ID-based form preserves explicitly listed isolated nodes. CSV and label-only JSON can describe only nodes appearing in an edge. Fetch `export?format=json&include_orphans=true` from taxonomy-builder when you need isolated-node statistics. API authentication and downloading remain the caller's responsibility; credentials never enter this tool.

## Scientific conventions

- Directed exact-label matching after Unicode NFC normalization, case folding, and whitespace normalization. Reversed edges are different relations. No stemming, translation, or synonym inference.
- Duplicate edges count once, retaining the highest score. Input row, duplicate, and unscored counts are recorded. Scores must be finite and in [0, 1]; missing/null/empty scores default to 1.0.
- `--threshold` includes predicted edges with score **greater than or equal to** the threshold. Gold edges are never thresholded. Declared/observed nodes remain in the graph after filtering, so newly isolated concepts remain visible.
- TP = predicted intersect gold; FP = predicted minus gold; FN = gold minus predicted. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN).
- Precision is `null` when predictions are empty; recall is `null` when gold is empty. By conservative convention, F1 is `null` when either edge set is empty. Nonempty disjoint edge sets have F1 = 0. An undefined F1 fails any requested minimum-F1 gate.
- Structural diagnostics include roots, leaves, isolated nodes, multiple parents, weak components, largest component ratio, and directed cycles. Multiple inheritance is permitted. Roots and leaves include isolated nodes. Depth is the **longest** root-to-node path in edges, with roots at depth 0; it is `null` for a cyclic or empty graph.
- Duplicate node IDs and duplicate normalized node labels in ID-based JSON are rejected because they make label matching ambiguous. Resolve homonyms with qualified labels before evaluation.
- JSON reports include both input SHA-256 hashes, tool/Python versions, parameters, error edges, and graph diagnostics. They omit timestamps for repeatability. Save the Git commit and reference annotation protocol alongside real experiments.

Exit codes: **0** = graph checks and optional F1 gate pass; **1** = a cycle in either graph or failed F1 gate; **2** = invalid input/arguments or an I/O error. F1 alone does not validate a cyclic hierarchy. Output files are replaced atomically, and output cannot overwrite either input.

## Research protocol and limits

Create an expert-annotated gold standard with documented domain, relation direction, labeling rules, and disagreement resolution. Use a development split to choose a threshold, then freeze it before evaluating a held-out test split. Report precision, recall, F1, error examples, graph structure, and annotation limitations together. An incomplete reference can classify valid unseen edges as false positives; confidence scores need not be calibrated probabilities.

The tool keeps inputs and graphs in memory. It is intended for small and medium exported taxonomies. It compares direct edges only; ancestor equivalence, synonym matching, confidence intervals, and large graph storage can be added when an actual study requires them.

## Development, CI/CD, and assignment report

[Public repository](https://github.com/thgank/taxonomy-evaluator) · [CI/CD configuration](https://github.com/thgank/taxonomy-evaluator/blob/main/.github/workflows/ci.yml) · [Actions runs](https://github.com/thgank/taxonomy-evaluator/actions) · [Issues](https://github.com/thgank/taxonomy-evaluator/issues)

The workflow tests Python 3.11, 3.13, and 3.14 on pushes and pull requests. A delivery job depends on all test jobs, checks the synthetic F1 gate, and uploads a runnable ZIP plus its evaluation JSON. This implements delivery of a validated scientific tool; server deployment is unnecessary. Artifacts are downloadable from successful Actions runs and retained for 30 days.

Use short feature branches and focused commits; explain scientific behavior changes in a pull request and run the same local test command before merging. Issue templates cover bugs and research tasks. The MIT license permits reuse.

The 10-page assignment report is [output/pdf/assignment-3-report.pdf](output/pdf/assignment-3-report.pdf); its editable source is [docs/assignment-3-report.tex](docs/assignment-3-report.tex). It uses Times New Roman, 12 pt, 1.5 spacing, and justified body text. Rebuild on macOS with Times New Roman installed:

```sh
tectonic docs/assignment-3-report.tex --outdir output/pdf
```

Example result files are in [output/results](output/results). The original assignment PDF is a local input and is excluded from publication.
