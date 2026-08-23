# Synthetic Cybercrime ATM-Prediction Dataset Generator

Generates a **fully synthetic**, leakage-safe dataset for training an ML
pipeline that predicts where (and when) a cybercrime mule account is likely
to cash out at an ATM, given a complaint.

**No real data is used or claimed.** All people, phone numbers, UPI IDs,
bank accounts, complaints, transactions, mule networks, and withdrawal
events are synthetically generated (seeded, reproducible). Only city /
district / pincode / lat-lon *geography* is realistic Indian geography —
placed to be plausible, not sourced from any private or government
database. Nothing here comes from, or claims to come from, NCRP, CFCFRMS,
I4C, banks, or police systems.

## ✅ Full-scale run completed

This deliverable includes the **actual full production run**: 50,000
complaints, 349,706 transactions, 40,000 accounts, 7,000 ATMs, 50,000
withdrawals, **11,932,605 rank_pairs rows**, **0 leakage violations**. Exact
numbers are in `dataset/metadata/statistics.json` and
`dataset/metadata/leakage_report.json`.

Because `rank_pairs.csv` (+ its train/val/test splits) totals ~5.9GB
uncompressed, those four files are shipped separately as `.gz` alongside this
project archive rather than inside the zip:
- `rank_pairs.csv.gz` (master, all rows)
- `train_rank_pairs_train.csv.gz`
- `validation_rank_pairs_val.csv.gz`
- `test_rank_pairs_test.csv.gz`

Decompress with `gunzip <file>.gz` (or `pd.read_csv(path, compression="gzip")`
directly — pandas handles `.gz` natively, no need to decompress first).

## ⚠️ Scale note — how to reproduce or rerun

The spec's full production target is **50,000 complaints** and
**5–20 million** complaint×ATM ranking pairs — this repo actually reached
that target in this deliverable (11.9M rows, see above). Because a single
foreground process in the environment this was built in is capped at a few
minutes, the full run was executed via the **resumable chunked driver**,
`run_resumable.py`, instead of `main.py` (which is fine for demo/dev scale
but would need to run uninterrupted for ~25-30 minutes at full scale):

```bash
cd scripts
DATASET_SCALE=full python3 run_resumable.py   # first call: SETUP (generates
                                                # all base data, ~2.5 min)
DATASET_SCALE=full CHUNK_SIZE=3500 python3 run_resumable.py   # repeat until
                                                                # it prints
                                                                # "RUN COMPLETE"
```

Each chunk call processes ~3,500 complaints in ~65-70 seconds and is fully
resumable — progress lives in `checkpoint/state.json` and the prebuilt as-of-T
lookup context is pickled in `checkpoint/base_data.pkl` so no call has to
redo earlier work. On unrestricted hardware you'd just let `main.py` (or a
version of `run_resumable.py` with `CHUNK_SIZE` set to the full complaint
count) run uninterrupted instead.

For smaller/faster runs, `main.py` still works standalone:

```bash
DATASET_SCALE=demo python3 main.py    # ~1,200 complaints, seconds
DATASET_SCALE=dev  python3 main.py    # 5,000 complaints, ~1 minute
```

## Pipeline

```
config.py                  sizes, seed (42), Indian city/geography table
utils.py                   haversine, jitter, weighted sampling, time-window binning
gen_atms.py                atm_master.csv
gen_complaints.py          complaints.csv
gen_accounts.py            accounts.csv, upi_entities.csv
gen_clusters.py            reusable "fraud ring" infrastructure (mule networks)
gen_flow.py                transactions.csv, withdrawals.csv, case_links.csv, graph_edges.csv
gen_history_features.py    as-of-timestamp-T historical feature helpers (leakage-safe core)
gen_rank_pairs.py          hybrid candidate retrieval -> rank_pairs.csv, time_labels.csv,
                           anomaly_features.csv, Recall@K / candidate stats
validate.py                leakage_report.json checks
split_and_stats.py         chronological train/val/test split, statistics.json
main.py                    orchestrates everything, writes dataset/ + metadata/
```

Run: `cd scripts && python3 main.py` (defaults to `DATASET_SCALE=demo`).

## Leakage safety — how it's actually enforced

1. **Prediction timestamp = complaint filing time.** A complaint only
   produces ranking/time/anomaly rows if its actual withdrawal happened
   **after** the complaint was filed (`withdrawal_timestamp > prediction_timestamp`).
   Cases where cash-out already happened before/at filing are excluded from
   the forward-looking prediction task by construction — they aren't
   "predictable in advance," so training on them would be leakage, not signal.
2. **All historical/graph/hotspot features are computed with `AsOfIndex`**
   (`gen_history_features.py`), which does a `searchsorted` on a sorted
   timestamp array and only aggregates events strictly before `T`. Nothing
   downstream can see an ATM's future cashout count, a cluster's future
   case count, or a graph edge created after `T`.
3. **Candidate retrieval never sees the true withdrawal ATM.** Geographic,
   hotspot, network, and behavioural candidates are generated blind to the
   label; Recall@K is measured on that blind union *before* any forced
   insertion. Only the training file (`rank_pairs.csv`) force-adds the true
   ATM when retrieval missed it (logged as `forced_insertion_rate` in
   `statistics.json`/`leakage_report.json` — never silently).
4. **`validate.py`** re-checks all of this mechanically after generation
   (impossible coordinates, negative amounts, duplicate IDs, withdrawal
   before its own first transaction, ranking positives that don't match the
   real withdrawal, `prediction_timestamp >= withdrawal_timestamp`, etc.) and
   writes `metadata/leakage_report.json`. On the shipped demo run this comes
   back with **0 violations**.
5. **Chronological split** (`split_and_stats.py`): oldest 70% of complaints
   (by `complaint_timestamp`) → train, next 15% → validation, newest 15% →
   test. No shuffling, so test is genuinely future-relative-to-train.

## What's intentionally *not* trivially solvable

Per section 24/17 of the spec, the withdrawal ATM is **not** just "nearest
ATM to the victim": each fraud cluster has its own geographic home turf,
delay profile (fast/medium/slow), and a mix of pattern behaviours (nearby,
district-shift, long-distance) sampled per case, so a naive nearest-ATM
baseline will not achieve high Recall@K — that's measured explicitly
(`recall_at_k` in `statistics.json`) rather than assumed.

## File structure produced

```
dataset/
├── complaints.csv, accounts.csv, upi_entities.csv, transactions.csv,
│   withdrawals.csv, atm_master.csv, case_links.csv, graph_edges.csv,
│   rank_pairs.csv, time_labels.csv, anomaly_features.csv
├── train/ validation/ test/        (chronological splits of the 3 model-facing files)
└── metadata/
    ├── schema.json, data_dictionary.csv, generation_config.json
    ├── statistics.json              (counts, distributions, Recall@K, positive/negative ratio)
    └── leakage_report.json          (mechanical leakage/quality checks + violation counts)
```

## Known simplifications (documented, not hidden)

- `atm_master.csv`'s `historical_*_as_of_T` columns are a single global
  snapshot as of the end of the simulation window (useful as a descriptive
  reference table). The features that actually feed the ranker are
  recomputed **per complaint at that complaint's own T** inside
  `rank_pairs.csv` — those are the leakage-safe ones to train on.
- `historical_complaints_as_of_T` at the ATM level is approximated as one
  complaint per prior withdrawal event at that ATM (a given ATM's prior
  cash-outs each came from one complaint, so this is exact under this
  generator's 1-withdrawal-per-complaint default, but would need adjustment
  if you enable multiple positive withdrawals per case).
- Graph "centrality" is approximated with in/out degree as-of-T rather than
  a full graph-centrality computation (betweenness/eigenvector centrality
  over a growing timestamp-filtered graph is expensive to keep leakage-safe
  at scale) — swap in `networkx` on the as-of-T edge subgraph per complaint
  if you need a truer centrality measure.
- Anomaly labels (`new_beneficiary_anomaly`, `sudden_degree_change`) are
  seeded partly from account degree with injected randomness so anomalies
  aren't trivially separable (per spec section 15), not from a real
  anomaly-detection model — Isolation Forest is meant to be *trained* on
  `anomaly_features.csv`'s numeric columns, not baked in here.

## Performance optimizations already applied

These were necessary to make the full 50k run finish in practical time and
without exceeding available memory — noting them here in case you extend
the pipeline further:

1. **Time-bucketed hotspot scoring**: ATM hotspot scores for candidate
   *selection* are precomputed once per time bucket (60 buckets across the
   sim window), not once per complaint — turns an O(complaints × atms) loop
   into O(buckets × atms). The bucket start (always ≤ the real complaint T)
   keeps this leakage-safe; only the final per-candidate feature values use
   the exact T.
2. **KD-tree geographic density**: `nearby_atm_count` doesn't depend on the
   prediction timestamp, so it's computed once for the whole ATM master via
   `scipy.spatial.cKDTree` instead of once per (complaint, candidate) pair.
3. **Streaming CSV writers**: `rank_pairs.csv` (+ splits) are written row by
   row via `csv.DictWriter` as they're generated, never buffered as a giant
   list of Python dicts — this is what keeps memory bounded regardless of
   total row count (the 11.9M-row full run peaked well under available RAM).
4. **Resumable chunked execution** (`run_resumable.py`): see above.

## Reproducibility

Fixed seed `42` (`scripts/config.py`). Given the same `DATASET_SCALE`, the
entire dataset is deterministically reproducible from
`metadata/generation_config.json` + the scripts in `scripts/` — including
across chunked/resumed runs, since each row's random component is seeded by
`(SEED, global_complaint_index)` rather than a shared mutable RNG stream.

