"""Small reproducibility helper for the property-profile notebook.

Offline functions only read compact frozen artifacts. Live mode is opt-in through
RUN_LIVE=1, rebuilds the 12 automatic inputs from the downloaded snapshot, checks
tokens before every call, and writes a new timestamped JSONL file.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import math
import os
import re
import time

import httpx
import pandas as pd
from dotenv import load_dotenv
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
ANCHOR = pd.Timestamp("2026-06-29")
SEED = 20260929
AGE_BANDS = ["0-365 days", "366-1095 days", ">1095 days"]
AGE_WEIGHTS = dict(zip(AGE_BANDS, [0.5, 0.3, 0.2]))
EVIDENCE_BUDGET = 8000
ENVELOPE_RESERVE = 128
INPUT_LIMIT = 10000

BR = re.compile(r"<br\s*/?>", re.I)
ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#\d+|#x[0-9a-fA-F]+);")
PUNCT_ONLY = re.compile(r"[\s.!?,;:\-_*~]+")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify_snapshot(data_dir: Path | str = ROOT / "data") -> None:
    """Refuse a live rerun if the downloaded files differ from the frozen snapshot."""
    data_dir = Path(data_dir)
    expected = load_json(ARTIFACTS / "experiment_summary.json")["snapshot"]["input_sha256"]
    for name, digest in expected.items():
        path = data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing snapshot file: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"Snapshot hash mismatch for {name}: {actual}")


def frozen_runs(experiment: str | None = None) -> list[dict]:
    rows = load_jsonl(ARTIFACTS / "frozen_runs.jsonl")
    return rows if experiment is None else [r for r in rows if r["experiment"] == experiment]


def clean_comment(text: str) -> str:
    """Decode complete entities and normalize whitespace without rewriting prose."""
    text = ENTITY.sub(lambda m: html.unescape(m.group()), text)
    text = BR.sub("\n", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _record(review_id: str, date: str, comment: str) -> str:
    return json.dumps({"review_id": review_id, "date": date, "comment": comment},
                      ensure_ascii=False, separators=(",", ":")) + "\n"


def _tagged(review_id: str, date: str, comment: str) -> str:
    return f"[review_id={review_id}; date={date}]\n{comment}\n\n"


def prepare_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    x = reviews[["listing_id", "id", "date", "comments"]].rename(
        columns={"id": "review_id", "comments": "raw_comment"}).copy()
    x["clean_comment"] = x.raw_comment.map(clean_comment)
    x["uninformative_reason"] = x.clean_comment.map(
        lambda s: "empty_after_cleaning" if not s else
        "ascii_punctuation_only" if PUNCT_ONLY.fullmatch(s) else "")
    x["eligible_text"] = x.uninformative_reason.eq("")
    x["age_days"] = (ANCHOR - pd.to_datetime(x.date, errors="raise")).dt.days
    if not x.age_days.ge(0).all():
        raise ValueError("Review date occurs after the fixed snapshot anchor")
    x["age_band"] = pd.cut(x.age_days, [-1, 365, 1095, float("inf")],
                           labels=AGE_BANDS).astype(str)
    json_cost = [math.ceil(len(_record(i, d, s)) / 3)
                 for i, d, s in zip(x.review_id, x.date, x.clean_comment)]
    tagged_cost = [math.ceil(len(_tagged(i, d, s)) / 3)
                   for i, d, s in zip(x.review_id, x.date, x.clean_comment)]
    x["planning_units"] = [max(a, b) for a, b in zip(json_cost, tagged_cost)]
    x["priority_hash"] = [hashlib.sha256(f"{SEED}|{l}|{r}".encode()).hexdigest()
                          for l, r in zip(x.listing_id, x.review_id)]
    return x


def select_reviews(prepared: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the frozen automatic whole-review, time-balanced selector."""
    x = prepared.copy()
    x["included"] = False
    row_budget = EVIDENCE_BUDGET - ENVELOPE_RESERVE
    for _, all_rows in x.groupby("listing_id", sort=True):
        candidates = all_rows[all_rows.eligible_text]
        if candidates.planning_units.sum() <= row_budget:
            x.loc[candidates.index, "included"] = True
            continue
        remaining = row_budget
        selected: set[int] = set()

        def take(index: int) -> bool:
            nonlocal remaining
            cost = int(x.at[index, "planning_units"])
            if index in selected or cost > remaining:
                return False
            selected.add(index); remaining -= cost; x.at[index, "included"] = True
            return True

        active = [b for b in AGE_BANDS if candidates.age_band.eq(b).any()]
        for band in active:
            temporal = candidates[candidates.age_band.eq(band)].sort_values(["date", "review_id"])
            for index in [temporal.index[0], temporal.index[-1]]:
                take(index)
        post_anchor = remaining
        weight_sum = sum(AGE_WEIGHTS[b] for b in active)
        for band in active:
            allowance = math.floor(post_anchor * AGE_WEIGHTS[band] / weight_sum)
            ordered = candidates[candidates.age_band.eq(band)].sort_values(["priority_hash", "review_id"])
            for index in ordered.index:
                cost = int(x.at[index, "planning_units"])
                if index not in selected and cost <= allowance and take(index):
                    allowance -= cost
        for index in candidates.sort_values(["priority_hash", "review_id"]).index:
            take(index)
    return x


def final_contract() -> tuple[str, dict, dict]:
    row = next(r for r in frozen_runs("main_v2"))
    request = row["request"]
    prompt = request["systemInstruction"]["parts"][0]["text"]
    schema = request["generationConfig"]["responseJsonSchema"]
    settings = {k: v for k, v in request["generationConfig"].items()
                if k != "responseJsonSchema"}
    return prompt, schema, settings


def build_live_requests(data_dir: Path | str = ROOT / "data") -> list[dict]:
    """Build the exact 12 automatic requests locally; this never calls Gemini."""
    data_dir = Path(data_dir)
    verify_snapshot(data_dir)
    reviews = pd.read_csv(data_dir / "reviews.csv.gz", dtype=str, keep_default_na=False)
    sample = pd.read_csv(ARTIFACTS / "sample_manifest.csv", dtype={"listing_id": str})
    raw = reviews[reviews.listing_id.isin(sample.listing_id)].copy()
    selected = select_reviews(prepare_reviews(raw))
    prompt, schema, settings = final_contract()
    model = next(r for r in frozen_runs("main_v2"))["request"]["model"]
    requests = []
    for listing_id in sample.listing_id:
        group = selected[selected.listing_id.eq(listing_id)]
        kept = group[group.included].sort_values(["date", "review_id"])
        header = {"listing_id": listing_id, "snapshot": "2026-06-29",
                  "corpus_reviews": len(group), "corpus_dates": [group.date.min(), group.date.max()],
                  "selected_reviews": len(kept), "selection": "time_only_v0",
                  "purposive_review_ids": []}
        evidence = json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n"
        evidence += "".join(_record(r.review_id, r.date, r.clean_comment) for r in kept.itertuples())
        request = {"model": model, "systemInstruction": {"parts": [{"text": prompt}]},
                   "contents": [{"role": "user", "parts": [{"text": evidence}]}],
                   "generationConfig": {**settings, "responseJsonSchema": schema}}
        requests.append({"listing_id": listing_id, "request": request})
    return requests


def validate_profile(parsed: dict, request: dict) -> list[dict]:
    schema = request["generationConfig"]["responseJsonSchema"]
    errors = [{"kind": "schema", "path": list(e.absolute_path), "message": e.message}
              for e in Draft202012Validator(schema).iter_errors(parsed)]
    lines = [json.loads(s) for s in request["contents"][0]["parts"][0]["text"].splitlines()]
    supplied = {r["review_id"]: r for r in lines[1:]}
    for ci, claim in enumerate(parsed.get("claims", [])):
        for cite in claim.get("citations", []):
            source = supplied.get(cite.get("review_id"))
            if source is None:
                errors.append({"kind": "citation", "claim": ci, "review_id": cite.get("review_id"),
                               "message": "Review ID not supplied"})
            elif cite.get("date") != source["date"]:
                errors.append({"kind": "citation_date", "claim": ci, "review_id": cite["review_id"]})
            elif cite.get("quote", "") not in source["comment"]:
                errors.append({"kind": "quote", "claim": ci, "review_id": cite["review_id"]})
    return errors


def run_live(data_dir: Path | str = ROOT / "data", output_root: Path | str = ROOT / "live_results") -> Path:
    """Run 12 new automatic profiles. Existing frozen artifacts are never touched."""
    if os.getenv("RUN_LIVE") != "1":
        raise RuntimeError("Set RUN_LIVE=1 explicitly before making live calls")
    load_dotenv(ROOT / ".env")
    key, model = os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL")
    base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models").rstrip("/")
    if not key or not model:
        raise RuntimeError("GEMINI_API_KEY and GEMINI_MODEL are required")
    requests = build_live_requests(data_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(output_root) / stamp
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "runs.jsonl"

    def save(record: dict) -> None:
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    for item in requests:
        request = item["request"]
        if request["model"] != "models/" + model:
            raise RuntimeError("Configured model differs from the frozen request model")
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=120, follow_redirects=False) as client:
                count_response = client.post(f"{base}/{model}:countTokens",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={"generateContentRequest": request})
                evidence_response = client.post(f"{base}/{model}:countTokens",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={"contents": request["contents"]})
        except Exception as exc:
            save({"listing_id": item["listing_id"], "request": request,
                  "status": "preflight_transport_failure", "error": repr(exc)})
            continue
        count_body = count_response.json()
        evidence_body = evidence_response.json()
        count = int(count_body.get("totalTokens", INPUT_LIMIT + 1))
        evidence_count = int(evidence_body.get("totalTokens", EVIDENCE_BUDGET + 1))
        record = {"listing_id": item["listing_id"], "request": request,
                  "token_preflight": {"http_status": count_response.status_code,
                                      "evidence_http_status": evidence_response.status_code,
                                      "complete_actual_tokens": count, "request_limit": INPUT_LIMIT,
                                      "evidence_actual_tokens": evidence_count,
                                      "evidence_limit": EVIDENCE_BUDGET,
                                      "complete_response": count_body,
                                      "evidence_response": evidence_body}}
        if (count_response.status_code != 200 or evidence_response.status_code != 200
                or count > INPUT_LIMIT or evidence_count > EVIDENCE_BUDGET):
            record["status"] = "preflight_failed_no_generation"
        else:
            try:
                with httpx.Client(timeout=120, follow_redirects=False) as client:
                    response = client.post(f"{base}/{model}:generateContent",
                        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                        json={k: v for k, v in request.items() if k != "model"})
            except Exception as exc:
                record.update({"status": "generation_transport_failure", "error": repr(exc),
                               "latency_seconds": time.perf_counter() - start})
                save(record)
                continue
            raw = response.json(); record.update({"status": "generated", "http_status": response.status_code,
                "latency_seconds": time.perf_counter() - start, "raw_response": raw})
            try:
                text = "".join(p.get("text", "") for p in raw["candidates"][0]["content"]["parts"]
                               if not p.get("thought", False))
                parsed = json.loads(text); record["parsed_output"] = parsed
                record["validation_errors"] = validate_profile(parsed, request)
            except Exception as exc:
                record["validation_errors"] = [{"kind": "parse", "message": str(exc)}]
            record["usage"] = raw.get("usageMetadata", {})
        # Append after every listing so a later failure cannot erase earlier results.
        save(record)
    return output
