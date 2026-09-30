# Experiment records

The notebook uses `rerun_20260930T070111Z/` as the primary result set. The 29 September folder supports prompt development and clearly labeled historical comparisons.

## `original_20260929/`

- `runs.jsonl` — the original v1 pilot, v2 pilot, 12 `main_v2` profiles, human-assisted paired case, and three order-only runs. It supports prompt iteration and historical comparison rather than the primary reported profiles.
- `claim_evidence_review.json` — the historical 50-claim review and 96/5,089 excluded-review inspection. These remain labeled historical and are not mixed into the primary quality results.
- `sample_manifest.csv` — the frozen 12-listing selection and group metadata. The notebook rebuilds the sample from raw data and checks it against this record.
- `experiment_summary.json` — the original experiment plans and compact recorded comparisons, including the human-assisted nominations and v1/v2 cases. Several calculated fields duplicate values that the notebook now recomputes; they remain because the same file also preserves contemporaneous decisions that are not recoverable from API responses alone.

## `rerun_20260930T070111Z/`

- `runs.jsonl` — the primary 12 main calls and three order-only calls, with requests, token preflights, raw responses, settings, usage, latency, validation, and failures. It supports the primary profiles, structural validation, stability analysis, measured usage, and cost projection.
- `ai_assisted_review.json` — the semantic review linked to the primary profiles. Old semantic labels were not reused.
- `comparison_checks.json` — the evaluation criteria recorded before the rerun calls. The notebook does not calculate from this file; it is retained as evidence that the comparison was defined before results were inspected.
- `hash_verification.json` — request-hash, source-data-hash, and exact request-object comparisons between the original and rerun inputs. The notebook loads it for the experiment-record checks.

No notebook cell reads `live_results/` or `local_archive/`. `live_results/` is only the destination for a future opt-in run, and `local_archive/` holds retired development code and tests. Both stay local and are ignored by Git.

