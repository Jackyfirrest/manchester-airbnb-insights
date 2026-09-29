# Review-grounded property profiles

This repository is a notebook-centered diagnostic of review-grounded property
profiles for a fixed Greater Manchester Inside Airbnb snapshot. Open
`property_profiles.ipynb` for the analysis, saved profiles, source citations,
claim-level evidence review, order-only stability test, and operating-cost
projection.

## Assessment context

The assessment asks how an LLM could turn Airbnb guest reviews into grounded
property profiles. This submission first audits and samples the data, then tests
review selection, citation behavior, evidence support, stability, and operating
cost on a small supervised diagnostic. Personal correspondence and the original
assessment files remain local and are not part of the public repository.

The notebook runs offline from the compact files in `artifacts/`; no API key or
raw download is needed to read or reproduce its tables. The diagnostic sample
contains 12 of 5,579 reviewed listings from an inventory of 6,947 listings. It
was selected to expose failure modes and is not representative of Greater
Manchester. The two largest inputs are deliberate stress tests. Salford and the
eight reviewed listings missing detailed metadata are not tested.

## Offline rerun

```bash
python -m venv .venv
# activate the environment, then:
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute property_profiles.ipynb \
  --output property_profiles.executed.ipynb
```

The committed notebook already contains executed outputs for GitHub readers.
The four artifact files are the frozen evidence:

- `sample_manifest.csv`: selected listing IDs and sampling fields;
- `frozen_runs.jsonl`: exact requests, raw responses, parsed outputs,
  validation results, model settings, usage, and latency;
- `claim_evidence_review.json`: review rubric, claim judgments, omission records,
  and excluded-review inspection sample;
- `experiment_summary.json`: sampling, preparation, stability, and projection
  summaries used by the notebook.

## Live rerun

Download the three files listed in `data/README.md` into `data/`; their SHA-256
hashes must match. Copy `.env.example` to `.env`, add the key, and explicitly set
`RUN_LIVE=1`. Execute the notebook from the repository root. Its guarded live
cell rebuilds the 12 automatic inputs, verifies that they match the fixed
snapshot, counts both evidence and complete-request tokens before each
generation, and stops the call when either budget is exceeded. New records are
appended after every listing under a timestamped `live_results/` directory.
Frozen artifacts are never overwritten.

The local request reconstruction has been checked byte-for-byte against all 12
frozen request hashes. The current live transport has not been exercised after
the repository cleanup because doing so would create new Gemini calls.

Keep `.env`, downloaded data, and `live_results/` local. They are ignored by
Git. Pricing in the notebook is an explicit projection from the rates and usage
recorded during the experiment; check current model pricing before a new run.
