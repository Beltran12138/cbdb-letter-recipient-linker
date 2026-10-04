# run2：标准划分 + 困难划分（见 PREREG_addendum_run2.md）
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, csv, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

D = pickle.load(open(str(ROOT / 'disamb/pairs_v2.pkl'), 'rb'))
rows = [(w, g, t, [(p, f) for p, f, _ in cs]) for w, g, t, cs in D['rows']]


def fit(rs):
    X = np.array([f for r in rs for _, f in r[3]], float)
    y = np.array([p == r[1] for r in rs for p, _ in r[3]])
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)


def predict(m, rs):
    out = []
    for w, g, _, cs in rs:
        if not cs:
            out.append((None, 0.0, False)); continue
        s = m.predict_proba(np.array([f for _, f in cs], float))[:, 1]
        k = int(s.argmax())
        out.append((cs[k][0], s[k] / s.sum(), cs[k][0] == g))
    return out


def threshold(train, target=0.90):
    oof = [None] * len(train)
    groups = np.array([r[0] for r in train])
    for tr, va in GroupKFold(5).split(train, groups=groups):
        m = fit([train[i] for i in tr])
        for i, o in zip(va, predict(m, [train[i] for i in va])):
            oof[i] = o
    for t in np.linspace(0, 1, 201):
        sel = [o for o in oof if o[0] is not None and o[1] >= t]
        if sel and np.mean([o[2] for o in sel]) >= target:
            return t
    return 1.0


def report(name, train, test):
    T = threshold(train)
    res = predict(fit(train), test)
    n = len(test)
    recall = np.mean([any(p == r[1] for p, _ in r[3]) for r in test])
    amb = [o for o, r in zip(res, test) if len(r[3]) > 1 and any(p == r[1] for p, _ in r[3])]
    sel = [o for o in res if o[0] is not None and o[1] >= T]
    print(f'\n== {name}：测试 {n} 封 / 训练 {len(train)} 封 | 阈值 T={T:.3f}')
    print(f'候选召回 {recall:.1%} | 全量 Top-1 {np.mean([o[2] for o in res]):.1%} | '
          f'多候选含金标子集 {np.mean([o[2] for o in amb]):.1%} (n={len(amb)})')
    print(f'置信度≥T：覆盖 {len(sel)/n:.1%}，实际精度 {np.mean([o[2] for o in sel]):.1%}')
    return res


# 1. 标准划分
report('标准划分 run2', [r for r in rows if r[0] % 5], [r for r in rows if r[0] % 5 == 0])

# 2. 困难划分
cs = list(csv.reader(open(str(ROOT / 'csa/newtask.csv'), encoding='utf-8-sig')))
hdr, data = cs[1], cs[2:]
c = {h: i for i, h in enumerate(hdr)}
csv_writers = {int(r[c['人物id']]) for r in data if r[c['人物id']].strip()}
late = {(int(r[c['人物id']]), r[c['作品標題']]) for r in data
        if r[c['人物id']].strip() and not r[c['通訊人']].strip()}
hard_test = [r for r in rows if (r[0], r[2]) in late]
hard_train = [r for r in rows if r[0] not in csv_writers]
report('困难划分（当初未识别、后来识别）', hard_train, hard_test)
