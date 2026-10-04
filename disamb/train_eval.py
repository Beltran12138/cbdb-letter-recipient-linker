# 按 PREREG：按写信人划分；阈值只在训练集 GroupKFold 上选；测试集只跑一次。
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

D = pickle.load(open(str(ROOT / 'disamb/pairs.pkl'), 'rb'))
rows, names = D['rows'], D['feat_names']
is_test = lambda w: w % 5 == 0
train = [r for r in rows if not is_test(r[0])]
test = [r for r in rows if is_test(r[0])]


def flat(rs):
    X, y, g, lid = [], [], [], []
    for i, (w, gold, _, cs) in enumerate(rs):
        for p, f in cs:
            X.append(f); y.append(p == gold); g.append(w); lid.append(i)
    return np.array(X, float), np.array(y), np.array(g), np.array(lid)


def predict(model, rs):
    out = []                                   # (预测pid, 置信度, 是否正确)
    for w, gold, _, cs in rs:
        if not cs:
            out.append((None, 0.0, False)); continue
        p = model.predict_proba(np.array([f for _, f in cs], float))[:, 1]
        k = int(p.argmax())
        out.append((cs[k][0], p[k] / p.sum(), cs[k][0] == gold))
    return out


def fit(rs):
    X, y, _, _ = flat(rs)
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)


# 训练集上 5 折（按写信人分组）拿 OOF 置信度，选阈值
writers = np.array([r[0] for r in train])
oof = [None] * len(train)
for tr, va in GroupKFold(5).split(train, groups=writers):
    m = fit([train[i] for i in tr])
    for i, o in zip(va, predict(m, [train[i] for i in va])):
        oof[i] = o


def thr_for(outs, target=0.90):
    best = None
    for t in np.linspace(0, 1, 201):
        sel = [o for o in outs if o[0] is not None and o[1] >= t]
        if sel and np.mean([o[2] for o in sel]) >= target:
            best = t; break
    return best


T = thr_for(oof)
print(f'训练集 OOF 选出的阈值 T = {T:.3f}')

model = fit(train)
res = predict(model, test)
n = len(test)
acc = np.mean([o[2] for o in res])
amb = [o for o, r in zip(res, test) if len(r[3]) > 1 and any(p == r[1] for p, _ in r[3])]
sel = [o for o in res if o[0] is not None and o[1] >= T]
print(f'\n测试集书信 {n}（写信人 {len({r[0] for r in test})}）')
print(f'1. Top-1 准确率（全量）: {acc:.1%}')
print(f'2. 多候选且含金标子集 Top-1: {np.mean([o[2] for o in amb]):.1%}  (n={len(amb)})')
print(f'3. 置信度 ≥ T: 覆盖 {len(sel)/n:.1%}，实际精度 {np.mean([o[2] for o in sel]):.1%}')

# 基线 v2（同一测试集）：年代≤60 → 姓氏/本名过滤 → 唯一才作答
i = {k: names.index(k) for k in ('年代差', '前字=姓', '匹配本名')}
b_ans = b_ok = 0
for w, gold, _, cs in test:
    v1 = [(p, f) for p, f in cs if f[i['年代差']] == -1 or f[i['年代差']] <= 60]
    v2 = [(p, f) for p, f in v1 if f[i['前字=姓']] or f[i['匹配本名']]] or v1
    if len(v2) == 1:
        b_ans += 1; b_ok += v2[0][0] == gold
print(f'对照 基线v2: 覆盖 {b_ans/n:.1%}，精度 {b_ok/max(b_ans,1):.1%}，全量 Top-1 {b_ok/n:.1%}')

# 精度-覆盖曲线（测试集，仅报告用）
print('\n阈值  覆盖   精度')
for t in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95):
    s = [o for o in res if o[0] is not None and o[1] >= t]
    print(f'{t:.2f}  {len(s)/n:5.1%}  {np.mean([o[2] for o in s]):5.1%}')

imp = model.fit  # 占位，特征重要性另行用置换法评估
pickle.dump({'test_res': res, 'T': T}, open(str(ROOT / 'disamb/run1.pkl'), 'wb'))
