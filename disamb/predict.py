# 对新信预测收信人：输入 CSV（列 writer_id,title），输出前 k 个候选及置信度。
# 用 --db 指定的 CBDB 版本中全部已识别书信训练。作答阈值固定 0.9（run4 预注册的辅助阈值）：
# run4_stability 显示「OOF 精度 ≥ 97% 的最小阈值」规则随随机性在 0.94–1.0 间跳动，固定 0.9 稳定。
# 用法：python disamb/predict.py letters.csv out.csv [--db data/cbdb_20261003.sqlite3] [--top 3] [--threshold 0.9]
import argparse, csv, os, sys, pickle
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument('inp'); ap.add_argument('out')
ap.add_argument('--db', default=str(ROOT / 'data/cbdb_20261003.sqlite3'))
ap.add_argument('--top', type=int, default=3)
ap.add_argument('--threshold', type=float, default=0.9)
a = ap.parse_args()
os.environ['CBDB_PATH'] = a.db
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import features_v2 as F
from sklearn.ensemble import HistGradientBoostingClassifier


def fit(rs):
    X = np.array([f for r in rs for _, f, _ in r[3]], float)
    y = np.array([p == r[1] for r in rs for p, _, _ in r[3]])
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)


def scores(m, cs):
    return m.predict_proba(np.array([f for _, f, _ in cs], float))[:, 1]


cache = str(ROOT / f'disamb/model_{_P(a.db).stem}.pkl')     # 同一 CBDB 版本只训练一次
if os.path.exists(cache):
    m = pickle.load(open(cache, 'rb'))
else:
    m = fit(F.build(F.letters))
    pickle.dump(m, open(cache, 'wb'))
T = a.threshold

rows = list(csv.DictReader(open(a.inp, encoding='utf-8-sig')))
built = F.build([(int(r['writer_id']), None, r['title']) for r in rows])
with open(a.out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['writer_id', 'title', 'rank', 'person_id', 'name_chn', 'rules', 'confidence', 'answered'])
    for (wr, _, title, cs) in built:
        if not cs:
            w.writerow([wr, title, '', '', '', '', '', False]); continue
        s = scores(m, cs)
        for rank, k in enumerate(np.argsort(-s, kind='stable')[:a.top], 1):
            p = cs[k][0]
            w.writerow([wr, title, rank, p, F.person[p][0], '+'.join(cs[k][2]), f'{s[k]:.3f}',
                        rank == 1 and s[k] >= T])
