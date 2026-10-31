"""Exercise the built image, including mounted output and failure exit codes."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    inputs = [root / "examples" / name for name in ("predicted.csv", "gold.csv")]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs]
    command = ["docker", "run", "--rm", "--network=none", "--read-only",
               "--cap-drop=ALL", "--security-opt=no-new-privileges",
               "--user", f"{os.getuid()}:{os.getgid()}",
               "--mount", f"type=bind,src={root / 'examples'},dst=/data,readonly",
               "--mount", f"type=bind,src={output},dst=/results", args.image,
               "/data/predicted.csv", "/data/gold.csv"]

    def run(name, options, expected):
        result = subprocess.run(command + options, capture_output=True, text=True, timeout=60)
        (output / f"{name}.stdout").write_text(result.stdout, encoding="utf-8")
        (output / f"{name}.stderr").write_text(result.stderr, encoding="utf-8")
        print(f"{name}: exit {result.returncode} (expected {expected})", flush=True)
        assert result.returncode == expected, result.stderr
        return result

    baseline = json.loads(run("baseline", [], 0).stdout)
    options = ["--threshold", "0.5", "--min-f1", "0.9"]
    run("filtered", options + ["--output", "/results/evaluation.json"], 0)
    first = (output / "evaluation.json").read_bytes()
    run("repeat", options + ["--output", "/results/repeat.json"], 0)
    assert first == (output / "repeat.json").read_bytes(), "Report is not repeatable"
    filtered = json.loads(first)
    for report, fp, precision, f1 in ((baseline, 1, 5 / 6, 5 / 6),
                                     (filtered, 0, 1, 10 / 11)):
        metrics = report["metrics"]
        assert (metrics["true_positives"], metrics["false_positives"],
                metrics["false_negatives"]) == (5, fp, 1)
        for key, expected in (("precision", precision), ("recall", 5 / 6), ("f1", f1)):
            assert math.isclose(metrics[key], expected), (key, metrics[key])
        assert report["gate"]["passed"]
        assert [report["inputs"][key]["sha256"] for key in ("predicted", "gold")] == hashes
    failed = json.loads(run("failed-gate", ["--min-f1", "0.9"], 1).stdout)
    assert not failed["gate"]["passed"]
    run("invalid-input", ["--threshold", "nan"], 2)
    run("protect-input", ["--output", "/data/predicted.csv"], 2)
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs] == hashes
    print("PASS: counts, precision/recall/F1, hashes, mounted output, byte repeatability, exits 0/1/2")


if __name__ == "__main__":
    main()
