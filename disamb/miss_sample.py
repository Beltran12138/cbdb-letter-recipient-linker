# 抽样：金标不在候选里的书信（召回失败），看标题与金标人的名/别名
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, sqlite3, random, collections
D = pickle.load(open(str(ROOT / 'disamb/pairs.pkl'), 'rb'))
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()
miss = [r for r in D['rows'] if r[0] % 5 and not any(p == r[1] for p, _ in r[3])]  # 只看训练集，不碰测试集
random.seed(3)
print('训练集召回失败数', len(miss))
for w, g, t, cs in random.sample(miss, 25):
    nm = q('SELECT c_name_chn FROM BIOG_MAIN WHERE c_personid=?', (g,))[0][0]
    alts = [a for (a,) in q('SELECT c_alt_name_chn FROM ALTNAME_DATA WHERE c_personid=?', (g,))]
    print(f'《{t}》 → {nm} | 别名: {"、".join(alts[:6]) or "（无）"}')
