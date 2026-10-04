# 朴素基线：标题子串 → CBDB 本名/别名词典 → 时代过滤 → 姓氏过滤
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, collections
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()

person = {pid: (nm, sur, yr) for pid, nm, sur, yr in
          q('SELECT c_personid, c_name_chn, c_surname_chn, c_index_year FROM BIOG_MAIN')}
lex = collections.defaultdict(set)
for pid, (nm, _, _) in person.items():
    if nm and len(nm) >= 2:
        lex[nm].add(pid)
for pid, a in q('SELECT c_personid, c_alt_name_chn FROM ALTNAME_DATA'):
    if a and len(a) >= 2:
        lex[a].add(pid)

rows = q('''SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA
            WHERE c_assoc_code IN (429,431,433,435)''')

def cands(title, writer):
    hits = {}
    for L in (4, 3, 2):
        for i in range(len(title) - L + 1):
            s = title[i:i + L]
            for pid in lex.get(s, ()):
                if pid != writer:
                    hits.setdefault(pid, (s, title[i - 1] if i > 0 else ''))
    return hits

def era_ok(w, r):
    wy, ry = person.get(w, (0, 0, None))[2], person.get(r, (0, 0, None))[2]
    return wy is None or ry is None or abs(wy - ry) <= 60

stat = collections.Counter()
for w, gold, t in rows:
    c = cands(t, w)
    v0 = set(c)
    v1 = {p for p in v0 if era_ok(w, p)}
    # v2：别名前一字等于候选人姓氏，或命中的是本名
    v2 = {p for p in v1 if c[p][1] == person[p][1] or c[p][0] == person[p][0]} or v1
    for tag, s in (('v0 词典', v0), ('v1 +时代', v1), ('v2 +姓氏', v2)):
        if not s:
            stat[tag, '无候选'] += 1
        elif len(s) == 1:
            stat[tag, '唯一且对' if gold in s else '唯一但错'] += 1
        else:
            stat[tag, '多候选(含金标)' if gold in s else '多候选(无金标)'] += 1

n = len(rows)
for tag in ('v0 词典', 'v1 +时代', 'v2 +姓氏'):
    print(tag, {k[1]: f'{v} ({v/n:.0%})' for k, v in sorted(stat.items()) if k[0] == tag})
