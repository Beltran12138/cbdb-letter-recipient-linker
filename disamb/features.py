# 候选生成 + 特征抽取。遵守 PREREG：不使用书信关系代码 429–436。
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, collections, pickle, os

DB = str(ROOT / 'data/cbdb_20261003.sqlite3')
OUT = str(ROOT / 'disamb/pairs.pkl')
LETTER_CODES = tuple(range(429, 437))

db = sqlite3.connect(DB)
q = lambda s, a=(): db.execute(s, a).fetchall()

person = {p: (nm or '', sur or '', yr, dy) for p, nm, sur, yr, dy in
          q('SELECT c_personid, c_name_chn, c_surname_chn, c_index_year, c_dy FROM BIOG_MAIN')}

lex = collections.defaultdict(list)          # 字符串 -> [(pid, 类型)]
for p, (nm, _, _, _) in person.items():
    if len(nm) >= 2:
        lex[nm].append((p, 'name'))
for p, a, t in q('SELECT c_personid, c_alt_name_chn, c_alt_name_type_code FROM ALTNAME_DATA'):
    if a and len(a) >= 2:
        lex[a].append((p, t))

nbr = collections.defaultdict(set)           # 非书信社会关系 + 亲属
for a, b in q(f'SELECT c_personid, c_assoc_id FROM ASSOC_DATA WHERE c_assoc_code NOT IN {LETTER_CODES} AND c_assoc_id > 0'):
    nbr[a].add(b); nbr[b].add(a)
for a, b in q('SELECT c_personid, c_kin_id FROM KIN_DATA WHERE c_kin_id > 0'):
    nbr[a].add(b); nbr[b].add(a)

addr = collections.defaultdict(set)
for p, ad in q('SELECT c_personid, c_addr_id FROM BIOG_ADDR_DATA WHERE c_addr_id > 0'):
    addr[p].add(ad)

offices = collections.defaultdict(set)       # 候选人任过的官名
for p, o in q('''SELECT d.c_personid, c.c_office_chn FROM POSTED_TO_OFFICE_DATA d
                 JOIN OFFICE_CODES c ON c.c_office_id = d.c_office_id WHERE c.c_office_chn IS NOT NULL'''):
    if len(o) >= 2:
        offices[p].add(o)

letters = q(f'''SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA
                WHERE c_assoc_code IN (429,431,433,435)''')

ALT_TYPES = ['name', 4, 5, 3, 6, 7]          # 本名/字/号/别名/谥号/行第，其余归 other


def candidates(title, writer):
    hits = {}
    for L in (4, 3, 2):
        for i in range(len(title) - L + 1):
            s = title[i:i + L]
            for pid, t in lex.get(s, ()):
                if pid == writer or pid in hits:
                    continue
                hits[pid] = (s, t, title[i - 1] if i > 0 else '', i, L)
    return hits


def feats(writer, title, pid, hit, ncand):
    s, t, prev, pos, L = hit
    nm, sur, yr, dy = person[pid]
    wnm, wsur, wyr, wdy = person.get(writer, ('', '', None, None))
    era = abs(wyr - yr) if (wyr is not None and yr is not None) else -1
    rest = title[:pos] + '□' * L + title[pos + L:]
    off_hit = any(o[-2:] in rest for o in offices.get(pid, ()))
    common = len(nbr[writer] & nbr[pid]) if writer in nbr and pid in nbr else 0
    f = [L, prev == sur and sur != '', s == nm, sur != '' and sur in title,
         era, era == -1, wdy == dy,
         pid in nbr.get(writer, ()), common, len(nbr.get(pid, ())),
         len(addr[writer] & addr[pid]) > 0, off_hit, len(offices.get(pid, ())),
         ncand, len(lex[s])]
    f += [t == a for a in ALT_TYPES] + [t not in ALT_TYPES]
    return f


FEAT_NAMES = ['匹配长度', '前字=姓', '匹配本名', '姓出现在标题', '年代差', '年代缺失', '同朝代',
              '与写信人有关系', '共同关系人数', '候选人关系度数', '同地址', '标题含其官名后缀', '任官数',
              '候选总数', '该字符串同名人数'] + [f'类型={a}' for a in ALT_TYPES] + ['类型=其他']

rows = []
for writer, gold, title in letters:
    c = candidates(title, writer)
    # 只丢掉年代差 > 150 年的极端候选（不看金标）
    keep = {p: h for p, h in c.items()
            if person[p][2] is None or person.get(writer, (0, 0, None))[2] is None
            or abs(person[p][2] - person[writer][2]) <= 150}
    rows.append((writer, gold, title,
                 [(p, feats(writer, title, p, h, len(keep))) for p, h in keep.items()]))

pickle.dump({'rows': rows, 'feat_names': FEAT_NAMES}, open(OUT, 'wb'))
n = len(rows)
print('书信', n, '| 平均候选', sum(len(r[3]) for r in rows) / n,
      '| 候选含金标', sum(any(p == r[1] for p, _ in r[3]) for r in rows) / n)
