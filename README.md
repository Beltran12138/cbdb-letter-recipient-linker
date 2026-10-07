# cbdb-letter-recipient-linker

Given a letter's writer and title from the [China Biographical Database (CBDB)](https://cbdb.hsites.harvard.edu/), propose the recipient's CBDB person ID with a confidence score, and abstain when unsure.

Methods note with all evaluations and limits: https://claude.ai/code/artifact/2c2a76b0-e9e3-4acc-aa26-fc33124258cd (source: `report/recipient-linker.html`).

## Main result

Trained only on the CBDB 2022-07-27 release, tested on the 9,738 titled letters added between 2022-07 and 2023-03 (the CSA Ming letters batch):

| | Letters | Top-1 | Answered (confidence ≥ 0.9) | Precision when answered |
|---|---|---|---|---|
| All | 9,738 | 87.1% | 62.2% | 97.4% |
| Letters still unidentified in the CSA task file, identified later (post hoc) | 704 | 24.0% | 11.4% | 83.8% (67/80) |

Across 10 repetitions that change only the order of candidates, the cross-validation folds and the model seed (`disamb/run4_stability.py`), the 0.9 threshold answered 58–66% of the batch at 97.4–97.9% precision, and top-1 stayed at 86.9–87.4%.

The linker does well on letters people also found easy, and poorly on the hard residue. See `disamb/RESULTS_run*.md` and the pre-registration notes `disamb/PREREG*.md`.

**Correction (2026-10-07).** An earlier version of this README, the methods note and an email to the CBDB team reported 51.1% answered at a threshold of 0.945. That threshold came from the pre-registered rule "lowest threshold with ≥ 97% out-of-fold precision", and a re-run from a clean copy showed the rule is unstable: across the 10 repetitions it chose thresholds from 0.94 to 1.0 and answered 0–54% of the batch. Precision when answering stayed at 97.8–98.2%. A set iteration in `features_v2.py` also made results depend on `PYTHONHASHSEED`; this is fixed. Results are now reported at the fixed 0.9 threshold, which was the pre-registered secondary threshold.

## Linking new letters

```
python disamb/predict.py letters.csv out.csv --db data/cbdb_20261003.sqlite3 --top 3
```

`letters.csv` needs two columns, `writer_id` (CBDB person ID of the writer) and `title`. The model is trained on every identified letter in the `--db` release (1–2 minutes the first time; cached in `disamb/model_<db>.pkl` afterwards). `out.csv` lists the top candidates for each letter with `person_id`, `name_chn`, the candidate rules that found it, `confidence`, and `answered`, which is true only for a first-ranked candidate with confidence ≥ 0.9 (change with `--threshold`). Letters marked `answered = False` should be treated as unidentified.

Check: trained on the 2022-07-27 release and given only the writer and title of 500 letters sampled from the 2022-07 → 2023-03 batch, it ranked the later CBDB identification first for 87.2% and answered 62.8% at 97.5% precision (306/314).

Titles that carry no name (such as 其二) cannot be linked from the title alone.

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
