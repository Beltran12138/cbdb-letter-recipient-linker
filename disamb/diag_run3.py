# run3 事后诊断（测试集已跑完一次，此处不再改方法）
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, sqlite3, collections, random
R = pickle.load(open(str(ROOT / 'disamb/run3.pkl'), 'rb'))
OLD = sqlite3.connect(str(ROOT / 'data/old_20230324/cbdb_data_20230324.db'))
NEW = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
test = R['test']
dy = dict(NEW.execute('SELECT c_dy, c_dynasty_chn FROM DYNASTIES'))
wdy = {p: d for p, d in NEW.execute('SELECT c_personid, c_dy FROM BIOG_MAIN')}
print('写信人朝代:', collections.Counter(dy.get(wdy.get(w)) for w, _, _ in test).most_common(6))
print('标题为 [n/a] 或空:', sum(1 for _, _, t in test if not t or t.strip() in ('[n/a]', '')))

alt_old = collections.defaultdict(set); alt_new = collections.defaultdict(set)
for p, a in OLD.execute('SELECT c_personid, c_alt_name_chn FROM ALTNAME_DATA'):
    alt_old[p].add(a)
for p, a in NEW.execute('SELECT c_personid, c_alt_name_chn FROM ALTNAME_DATA'):
    alt_new[p].add(a)
nm_new = dict(NEW.execute('SELECT c_personid, c_name_chn FROM BIOG_MAIN'))
in_old = {p for (p,) in OLD.execute('SELECT c_personid FROM BIOG_MAIN')}
c = collections.Counter()
for w, g, t in test:
    t = t or ''
    hit_new = [a for a in alt_new[g] | {nm_new.get(g)} if a and len(a) >= 2 and a in t]
    hit_old = [a for a in alt_old[g] | {nm_new.get(g)} if a and len(a) >= 2 and a in t]
    if g not in in_old: c['收信人2023年尚不存在'] += 1
    elif hit_old: c['标题含2023年已有的名/别名'] += 1
    elif hit_new: c['所需别名是2023年后才录入的'] += 1
    else: c['标题里没有任何名/别名'] += 1
print('测试集构成:', dict(c))
random.seed(5)
print('\n样例:')
for w, g, t in random.sample(test, 15):
    print(f'  《{t}》 → {nm_new.get(g)}')
