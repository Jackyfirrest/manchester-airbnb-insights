# Review-grounded property profiles

`property_profiles.ipynb` is the implementation, analysis, and main deliverable. The executive **Written summary** is the second cell, under **“Written summary for the portfolio manager.”** The rest of the notebook starts with the fixed Inside Airbnb snapshot, rebuilds the diagnostic sample, prepares and selects reviews, shows both prompt versions and their observed outcomes, parses and validates saved responses, evaluates claims and omissions, tests sensitivity to review order, draws the figures, and projects cost.

The 12-listing sample is diagnostic rather than representative. It fills a 3 review-volume × 2 recency × 2 geography design and contains deliberate low-evidence and large-input cases. It is enough to exercise the pipeline and expose failures, but not to estimate portfolio-wide accuracy. It does not test Salford or the eight reviewed listings missing detailed metadata; the notebook states the larger human-labeled evaluation needed before production.

## Project structure

```text
property_profiles.ipynb       complete workflow and saved outputs
run_notebook.sh               offline-by-default notebook launcher
requirements.txt              pinned Python dependencies
.env.example                  live-run settings without credentials
data/
  README.md                   exact snapshot URLs and hashes
  listings.csv                local, ignored by Git
  listings.csv.gz             local, ignored by Git
  reviews.csv.gz              local, ignored by Git
results/
  README.md                   experiment roles and record types
  original_20260929/          development evidence: prompt iteration and side experiments
    runs.jsonl
    sample_manifest.csv
    experiment_summary.json
    claim_evidence_review.json
  rerun_20260930T070111Z/     primary result set used for reported findings
    runs.jsonl
    ai_assisted_review.json
    comparison_checks.json
    hash_verification.json
```

The main findings, profiles, claim review, stability figure, measured usage, and cost projection use the 30 September experiment: 12 main calls and three calls that change only review order. Its claim-evidence review is linked only to those outputs. The 29 September records remain for prompt iteration, the human-assisted paired case, the earlier excluded-review inspection, and historical comparison.

Raw response records cannot be recreated byte for byte because model outputs may vary. Calculated tables and figures are rebuilt from the downloaded data and saved responses each time the notebook runs. Recorded semantic judgments are evidence from a separate AI-assisted review; new outputs need a new review and must not inherit old labels.

## Setup

Use Python 3.11 or 3.12 from the repository root:

```bash
python -m venv .venv
# activate the environment, then
pip install -r requirements.txt
```

Download the three snapshot files listed in `data/README.md` into `data/`. The notebook checks their SHA-256 fingerprints to confirm that the analysis uses the intended snapshot. These technical fingerprints are kept in the verification metadata rather than treated as analysis results. No API key is needed offline.

## Run offline

The Bash script defaults to offline mode and replays the saved responses through the same parsing and validation code used by live extraction:

```bash
bash run_notebook.sh
# equivalent:
bash run_notebook.sh --offline
```

Offline mode is the normal reproducibility path: it makes no API calls and incurs no model cost. Use live mode only when intentionally generating a new set of model responses.

Without Bash, run:

```bash
jupyter nbconvert --to notebook --execute property_profiles.ipynb \
  --output property_profiles.ipynb \
  --ExecutePreprocessor.timeout=600
```

This updates the notebook in place with all tables and figures visible.

## Export and run a Python runner

The runner is generated from the notebook and is not maintained as a second implementation:

```bash
jupyter nbconvert --to python property_profiles.ipynb \
  --output property_profiles_runner
RUN_LIVE=0 RUN_LIVE_NOTEBOOK=0 python property_profiles_runner.py
```

The generated `property_profiles_runner.py` is disposable and ignored by Git.

## Run live

Copy `.env.example` to `.env`, set a new `GEMINI_API_KEY` and the documented `GEMINI_MODEL`, then explicitly choose live mode:

```bash
bash run_notebook.sh --live
```

Both `RUN_LIVE=1` and `RUN_LIVE_NOTEBOOK=1` are required. The notebook rebuilds the same 12 main requests and three order-only requests, checks source and request hashes, counts evidence and complete-request tokens before generation, and saves each request, response, setting, usage record, latency, validation result, and failure immediately under a new timestamped `live_results/` directory. It never overwrites either saved experiment.

Keep `.env`, downloaded data, `instruction/`, `live_results/`, and generated runners local. Credentials are never printed or written to result records.
