# run4 事后诊断：与 CSV「当时为空」子集的交叉；别名是否在 2022-07 版里预先录入
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, csv, sqlite3, numpy as np, collections
R = pickle.load(open(str(ROOT / 'disamb/run4.pkl'), 'rb'))
res, test, T = R['res'], R['test'], R['T']
rows = list(csv.reader(open(str(ROOT / 'csa/newtask.csv'), encoding='utf-8-sig')))
h, data = rows[1], rows[2:]
c = {k: i for i, k in enumerate(h)}
empty = {(int(r[c['人物id']]), r[c['作品標題']]) for r in data if r[c['人物id']].strip() and not r[c['通訊人']].strip()}
filled = {(int(r[c['人物id']]), r[c['作品標題']]) for r in data if r[c['人物id']].strip() and r[c['通訊人']].strip()}


def show(name, idx):
    r = [res[i] for i in idx]
    if not r:
        print(name, 'n=0'); return
    s = [o for o in r if o[0] is not None and o[1] >= T]
    print(f'{name}: n={len(r)} | Top-1 {np.mean([o[2] for o in r]):.1%} | ≥T 覆盖 {len(s)/len(r):.1%} '
          f'精度 {np.mean([o[2] for o in s]) if s else float("nan"):.1%}')


show('全部', range(len(test)))
show('CSV 当时为空（后来识别）', [i for i, (w, g, t) in enumerate(test) if (w, t) in empty])
show('CSV 当时已填', [i for i, (w, g, t) in enumerate(test) if (w, t) in filled])
show('不在 CSV 中', [i for i, (w, g, t) in enumerate(test) if (w, t) not in empty and (w, t) not in filled])

# 别名在 2022-07 版就有、到 2026 版来源指向本信文集的比例（录入是否为这批书信服务）
old = sqlite3.connect(str(ROOT / 'data/old_20220727/CBDB_20220727.db'))
src = collections.defaultdict(set)
for p, a, s in old.execute('SELECT c_personid, c_alt_name_chn, c_source FROM ALTNAME_DATA'):
    src[(p, a)].add(s)
new = sqlite3.connect(str(ROOT / 'data/old_20230324/cbdb_data_20230324.db'))
lsrc = {(w, t): s for w, g, t, s in new.execute('SELECT c_personid,c_assoc_id,c_text_title,c_source FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)')}
bypid = collections.defaultdict(list)
for (p, a), ss in src.items():
    bypid[p].append((a, ss))
tot = same = 0
for w, g, t in test:
    m = [(a, ss) for a, ss in bypid[g] if a and len(a) >= 2 and a in t]
    if m:
        tot += 1; same += any(lsrc.get((w, t)) in ss for _, ss in m)
print(f'\n命中 2022-07 版别名的测试信 {tot}；别名来源 = 本信文集 {same} ({same/max(tot,1):.1%})')
