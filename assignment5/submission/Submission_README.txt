ASSIGNMENT 5 SUBMISSION
Nursultan Serikov, CSE-2501M, Astana IT University
Prepared 3 November 2026

SUBMIT
Nursultan_Serikov_AS5_Theory.pdf: 4 pages, Times New Roman 12 pt, 1.5 spacing.
Nursultan_Serikov_AS5_Practice.pdf: 2 pages, same formatting.
Screenshots/: three genuine GitHub Actions captures.
Use the final Nursultan_Serikov_AS5_Submission.zip for the complete package.

PROJECT AND PIPELINE
https://github.com/thgank/taxonomy-evaluator/tree/assignment5-github-actions
Branch: assignment5-github-actions (main is unchanged).
Dockerfile: repository root.
Pipeline: .github/workflows/ci.yml
CI platform: GitHub Actions, as specified in the task instruction.

TESTED REVISION AND RUN
11d715859e23bd67b5515139f5306586e6de8302
https://github.com/thgank/taxonomy-evaluator/actions/runs/41595705699
Run #5; event push; success; created 2026-11-03T07:20:50Z.
Initial implementation push also passed:
https://github.com/thgank/taxonomy-evaluator/actions/runs/41594815711
Run #3; db30db212823d04581cb3eda84993c633286d3ec.
Reports and evidence were added after the tested revision. The final ZIP's
REVISION_MANIFEST.txt records the separate documentation commit explicitly.

SCREENSHOTS
01-actions-run-5.png: run #5 summary, push trigger, revision, status and artifacts.
02-delivery-stages-run-5.png: completed Docker build, checks and delivery stages.
03-test-matrix-run-5.png: successful Python 3.11/3.13/3.14 matrix and dependent job.
All captures are from the real public GitHub interface. Detailed logs require
GitHub sign-in in the browser; downloaded authenticated API logs are included.

ARCHIVE CONTENTS
submission/: the PDFs, this index and screenshots.
report_sources/: editable LaTeX sources; build instructions below.
evidence/: baseline, environment, run metadata, tests, image/build information,
container results, complete delivery job log, and evidence index.
reproducibility/: actual CI-delivered source ZIP and Docker image archive,
their SHA256SUMS, and reproduction commands.
REVISION_MANIFEST.txt: tested code and later documentation revision.
SHA256SUMS: integrity hashes for all files in the submission package.

RESULTS AND LIMITS
Five distinct regression methods passed on each of three Python versions.
Docker build and six container execution scenarios passed on Linux amd64.
Filtered synthetic benchmark: TP=5, FP=0, FN=1; precision=1; recall=5/6;
F1=10/11. This is software verification, not measured dissertation accuracy.
Byte repeatability, mounted output, unchanged inputs, and exits 0/1/2 passed.
Local macOS arm64 container execution: NOT RUN; Docker Desktop failed to start.
Optional automatic server/Kubernetes deployment: NOT IMPLEMENTED.
Artifacts are retained on GitHub for 30 days; the final ZIP preserves copies.
AS6 is context only and is not part of this submission. The source AS1-AS6
documents were not published or included in the final archive.
The statement's base rubric totals 90, with +10 optional deployment, although
it also labels practice 'up to 70'. No grade or instructor approval is claimed.

REBUILD REPORTS
Use Tectonic and Times New Roman installed at the font path in format.tex.
From the repository root:
tectonic assignment5/report_sources/Nursultan_Serikov_AS5_Theory.tex --outdir assignment5/submission
tectonic assignment5/report_sources/Nursultan_Serikov_AS5_Practice.tex --outdir assignment5/submission
Use --only-cached if the required TeX resources are already cached and network
initialization is unavailable. Other operating systems need their local font
path in format.tex. Document tooling is not needed to run the evaluator.
