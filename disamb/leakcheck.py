# 泄漏排查：写信人-金标之间的非书信关系，是不是和这封信出自同一文献来源（同批录入）
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, collections
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()
L = tuple(range(429, 437))

letters = q('SELECT c_personid, c_assoc_id, c_source, c_created_by, c_created_date FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)')
pair_src = collections.defaultdict(set)
for w, g, s, cb, cd in letters:
    pair_src[(w, g)].add(s)

other = collections.defaultdict(list)
for a, b, code, s, cb, cd in q(f'SELECT c_personid, c_assoc_id, c_assoc_code, c_source, c_created_by, c_created_date FROM ASSOC_DATA WHERE c_assoc_code NOT IN {L} AND c_assoc_id>0'):
    other[(a, b)].append((code, s, cb, cd))
    other[(b, a)].append((code, s, cb, cd))

pairs = set(pair_src)
has_rel = [p for p in pairs if other.get(p)]
same_src = [p for p in has_rel if any(s in pair_src[p] for _, s, _, _ in other[p])]
print(f'写信人-金标 配对 {len(pairs)}；有非书信关系 {len(has_rel)} ({len(has_rel)/len(pairs):.0%})')
print(f'其中关系与书信出自同一文献来源: {len(same_src)} ({len(same_src)/max(len(has_rel),1):.0%})')
codes = collections.Counter(c for p in has_rel for c, _, _, _ in other[p])
cn = dict(q('SELECT c_assoc_code, c_assoc_desc_chn FROM ASSOC_CODES'))
print('这些关系最常见的代码:', [(cn.get(c), n) for c, n in codes.most_common(8)])

# 对照：随机「写信人-非金标候选」配对中有关系的比例（看特征是否天然区分）
import pickle, random
D = pickle.load(open(str(ROOT / 'disamb/pairs.pkl'), 'rb'))
random.seed(0)
neg = [(w, p) for w, g, _, cs in D['rows'] for p, _ in cs if p != g]
neg = random.sample(neg, 5000)
print(f'对照：写信人-非金标候选 有关系 {sum(1 for x in neg if other.get(x))/len(neg):.1%}')
