# run4：积压批次切分（见 PREREG_addendum_run4.md）。特征全部来自 2022-07-27 版。
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
train = strip(F.build(old_gold))
test = strip(F.build(test_in))
print(f'训练 {len(train)} 封（2022-07 版金标）| 测试 {len(test)} 封（之后才识别）')


def fit(rs):
    X = np.array([f for r in rs for _, f in r[3]], float)
    y = np.array([p == r[1] for r in rs for p, _ in r[3]])
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)


def predict(m, rs):                      # 置信度 = 首选候选的原始概率
    out = []
    for w, g, _, cs in rs:
        if not cs:
            out.append((None, 0.0, False)); continue
        s = m.predict_proba(np.array([f for _, f in cs], float))[:, 1]
        k = int(s.argmax())
        out.append((cs[k][0], float(s[k]), cs[k][0] == g))
    return out


# 训练集 OOF：校准表 + 阈值
oof = [None] * len(train)
for tr, va in GroupKFold(5).split(train, groups=np.array([r[0] for r in train])):
    m = fit([train[i] for i in tr])
    for i, o in zip(va, predict(m, [train[i] for i in va])):
        oof[i] = o
print('\n训练集 OOF 校准表（原始概率分箱 → 实际正确率）')
for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .9), (.9, 1.01)]:
    b = [o for o in oof if o[0] is not None and lo <= o[1] < hi]
    if b:
        print(f'  [{lo:.1f},{min(hi,1):.1f}) n={len(b):5d}  平均概率 {np.mean([o[1] for o in b]):.2f}  实际正确 {np.mean([o[2] for o in b]):.2f}')
T = next((t for t in np.linspace(0, 1, 201)
          if (lambda s: s and np.mean([o[2] for o in s]) >= .97)([o for o in oof if o[0] is not None and o[1] >= t])), 1.0)
sel = [o for o in oof if o[0] is not None and o[1] >= T]
print(f'阈值 T = {T:.3f}（OOF 覆盖 {len(sel)/len(oof):.1%}，精度 {np.mean([o[2] for o in sel]):.1%}）')

# 测试集：只跑一次
res = predict(fit(train), test)
n = len(test)
sel = [o for o in res if o[0] is not None and o[1] >= T]
print(f'\n== 时间切分测试集 {n} 封')
print(f'候选召回 {np.mean([any(p == r[1] for p, _ in r[3]) for r in test]):.1%} | 全量 Top-1 {np.mean([o[2] for o in res]):.1%}')
print(f'置信度 ≥ T：覆盖 {len(sel)/n:.1%}，实际精度 {np.mean([o[2] for o in sel]) if sel else float("nan"):.1%}，'
      f'高置信错误率 {1-np.mean([o[2] for o in sel]) if sel else float("nan"):.1%}')
for t0 in (0.9,):
    s0 = [o for o in res if o[0] is not None and o[1] >= t0]
    print(f'固定阈值 {t0}：覆盖 {len(s0)/n:.1%}，实际精度 {np.mean([o[2] for o in s0]):.1%}')
import pickle
pickle.dump({'res': res, 'test': [(w, g, t) for w, g, t, _ in test], 'T': T},
            open(str(ROOT / 'disamb/run4.pkl'), 'wb'))
