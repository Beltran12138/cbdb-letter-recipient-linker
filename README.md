# cbdb-letter-recipient-linker

Given a letter's writer and title from the [China Biographical Database (CBDB)](https://cbdb.hsites.harvard.edu/), propose the recipient's CBDB person ID with a confidence score, and abstain when unsure.

Methods note with all evaluations and limits: https://claude.ai/code/artifact/2c2a76b0-e9e3-4acc-aa26-fc33124258cd (source: `report/recipient-linker.html`).

## Main result

Trained only on the CBDB 2022-07-27 release, tested on the 9,738 titled letters added between 2022-07 and 2023-03 (the CSA Ming letters batch):

| | Letters | Top-1 | Answered (confidence ≥ 0.945) | Precision when answered |
|---|---|---|---|---|
| All (pre-registered) | 9,738 | 87.1% | 51.1% | 97.7% |
| Letters still unidentified in the CSA task file, identified later (post hoc) | 704 | 24.1% | 7.7% | 77.8% |

The linker does well on letters people also found easy, and poorly on the hard residue. See `disamb/RESULTS_run*.md` and the pre-registration notes `disamb/PREREG*.md`.

## Data (not included)

CBDB is licensed CC BY-NC-SA 4.0 and is not redistributed here. Put these files under `data/`:

| File | Source |
|---|---|
| `data/cbdb_20261003.sqlite3` | `latest.json` in [cbdb-project/cbdb_sqlite](https://github.com/cbdb-project/cbdb_sqlite) → Hugging Face zip |
| `data/old_20220727/CBDB_20220727.db` | Hugging Face `cbdb/cbdb-sqlite`, `history/CBDB_20220727.7z` |
| `data/old_20230324/cbdb_data_20230324.db` | `history/CBDB_20230324.7z` |
| `data/old_20250520/CBDB_20250520.db` | `history/CBDB_20250520/CBDB_20250520.7z` (only for `timesplit_count.py`) |
| `csa/newtask.csv` | [cbdb-project/crowdsource-webapp](https://github.com/cbdb-project/crowdsource-webapp) |

Requires Python 3.11+, `numpy`, `scikit-learn`; `py7zr` to unpack the `.7z` releases.

## Layout

- `data/` — data probes and the naive dictionary baseline
- `disamb/features.py`, `features_v2.py` — candidate generation and features (v2 adds four recall rules and variant-character normalisation)
- `disamb/train_eval.py` (run1), `run2.py`, `run3.py`, `run4.py` — evaluations, one per pre-registration note
- `disamb/leakcheck.py`, `ablate.py`, `rule_baseline.py`, `topk.py`, `diag_run*.py` — diagnostics (post hoc)
- `csa/inspect_newtask.py` — statistics on the CSA task file

Run `disamb/features_v2.py` once before `run2.py`; `run3.py` and `run4.py` build their own features from the older releases.

## Limits

- Gold labels are letters that people managed to identify, so figures are an upper bound for the remaining backlog.
- Candidate rules were designed after reading about 45 training examples from the 2026 release, some of which belong to the run4 batch.
- Correctness is measured only against CBDB's own identifications; no specialist review yet.

## License

Code: MIT (see `LICENSE`). CBDB data: CC BY-NC-SA 4.0, © Harvard University, Academia Sinica, and Peking University.
