# run4 稳健性检查（事后，2026-10-07；非重新调参）：同一 run4 流程重复 10 次，每次只改动本应无关的随机性
# ——每封信内候选顺序、GroupKFold 分组、模型 random_state——看阈值 T 与覆盖率的波动。
# 起因：未固定 PYTHONHASHSEED 时 run4 的覆盖率在 40.7%–51.1% 之间变动。
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import os, sys, sqlite3, numpy as np
OLD = str(ROOT / 'data/old_20220727/CBDB_20220727.db')
NEW = str(ROOT / 'data/old_20230324/cbdb_data_20230324.db')
os.environ['CBDB_PATH'] = OLD
sys.path.insert(0, os.path.dirname(__file__))
import features_v2 as F
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

SQL = 'SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)'
old_gold = sqlite3.connect(OLD).execute(SQL).fetchall()
seen = {(w, t) for w, _, t in old_gold}
test_in = [r for r in sqlite3.connect(NEW).execute(SQL).fetchall() if (r[0], r[2]) not in seen and r[2] and r[2].strip() not in ('[n/a]', '')]
strip = lambda rs: [(w, g, t, [(p, f) for p, f, _ in cs]) for w, g, t, cs in rs]
train0 = strip(F.build(old_gold))
test0 = strip(F.build(test_in))


def shuffled(rs, rng):
    return [(w, g, t, [cs[i] for i in rng.permutation(len(cs))]) for w, g, t, cs in rs]


def fit(rs, seed):
    X = np.array([f for r in rs for _, f in r[3]], float)
    y = np.array([p == r[1] for r in rs for p, _ in r[3]])
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=seed).fit(X, y)


def predict(m, rs):
    out = []
    for w, g, _, cs in rs:
        if not cs:
            out.append((None, 0.0, False)); continue
        s = m.predict_proba(np.array([f for _, f in cs], float))[:, 1]
        k = int(s.argmax())
        out.append((cs[k][0], float(s[k]), cs[k][0] == g))
    return out


rows = []
for seed in range(10):
    rng = np.random.default_rng(seed)
    train, test = shuffled(train0, rng), shuffled(test0, rng)
    oof = [None] * len(train)
    for tr, va in GroupKFold(5, shuffle=True, random_state=seed).split(train, groups=np.array([r[0] for r in train])):
        m = fit([train[i] for i in tr], seed)
        for i, o in zip(va, predict(m, [train[i] for i in va])):
            oof[i] = o
    T = next((t for t in np.linspace(0, 1, 201)
              if (lambda s: s and np.mean([o[2] for o in s]) >= .97)([o for o in oof if o[0] is not None and o[1] >= t])), 1.0)
    res = predict(fit(train, seed), test)
    sel = [o for o in res if o[0] is not None and o[1] >= T]
    if not sel:
        sel = [(None, 0.0, float('nan'))]               # 零作答：覆盖记 0，精度记 nan
    s9 = [o for o in res if o[0] is not None and o[1] >= 0.9]
    r = (seed, T, np.mean([o[2] for o in res]), sum(o[0] is not None for o in sel) / len(res), np.mean([o[2] for o in sel]),
         len(s9) / len(res), np.mean([o[2] for o in s9]))
    rows.append(r)
    print('seed %d  T=%.3f  Top-1 %.1f%%  覆盖 %.1f%% 精度 %.1f%%  | 固定0.9 覆盖 %.1f%% 精度 %.1f%%'
          % (r[0], r[1], 100 * r[2], 100 * r[3], 100 * r[4], 100 * r[5], 100 * r[6]), flush=True)

a = np.array(rows)
print('\n10 次汇总：中位数 [最小, 最大]（精度不计零作答的那次）')
for j, name in [(1, '阈值 T'), (2, 'Top-1'), (3, '覆盖(≥T)'), (4, '精度(≥T)'), (5, '覆盖(≥0.9)'), (6, '精度(≥0.9)')]:
    k = 1 if j == 1 else 100
    print(f'  {name:10s} {k*np.nanmedian(a[:, j]):.3g} [{k*np.nanmin(a[:, j]):.3g}, {k*np.nanmax(a[:, j]):.3g}]')
