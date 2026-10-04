from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, collections, random
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()
LET = (429, 431, 433, 435)

rows = q(f"""SELECT a.c_personid, a.c_assoc_id, a.c_assoc_code, a.c_text_title, a.c_source,
                    w.c_name_chn, r.c_name_chn, w.c_dy, r.c_index_year
             FROM ASSOC_DATA a JOIN BIOG_MAIN w ON w.c_personid=a.c_personid
             JOIN BIOG_MAIN r ON r.c_personid=a.c_assoc_id
             WHERE a.c_assoc_code IN {LET}""")
print('书信关系总数:', len(rows))
print('有标题:', sum(1 for r in rows if r[3] and r[3].strip()))
dy = dict(q('SELECT c_dy, c_dynasty_chn FROM DYNASTIES'))
print('写信人朝代分布:', collections.Counter(dy.get(r[7]) for r in rows).most_common(6))
print('收信人 id<=0 (未识别):', sum(1 for r in rows if r[1] is None or r[1] <= 0))

src = collections.Counter(r[4] for r in rows)
print('出处(文本代码) 前5:', [(q('SELECT c_title_chn FROM TEXT_CODES WHERE c_textid=?', (s,)) or [[s]])[0][0] for s, _ in src.most_common(5)])

random.seed(7)
sample = random.sample([r for r in rows if r[3]], 12)
print('\n随机样例 (写信人 → 标题 → 金标收信人):')
for r in sample:
    print(f'  {r[5]} → 《{r[3]}》 → {r[6]}')

# 污染/难度探针：标题里是否直接出现金标收信人的本名或任一别名
alt = collections.defaultdict(set)
for pid, a in q('SELECT c_personid, c_alt_name_chn FROM ALTNAME_DATA WHERE c_alt_name_chn IS NOT NULL'):
    alt[pid].add(a)
hit_name = hit_alt = 0
titled = [r for r in rows if r[3]]
for r in titled:
    t = r[3]
    if r[6] and r[6] in t:
        hit_name += 1
    elif any(a and len(a) >= 2 and a in t for a in alt[r[1]]):
        hit_alt += 1
n = len(titled)
print(f'\n标题含收信人本名: {hit_name}/{n} = {hit_name/n:.0%}')
print(f'标题不含本名但含其某个别名(>=2字): {hit_alt}/{n} = {hit_alt/n:.0%}')
print(f'两者都不含: {n-hit_name-hit_alt}/{n} = {(n-hit_name-hit_alt)/n:.0%}')
