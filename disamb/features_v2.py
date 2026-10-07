# 候选生成 v2：v1 词典匹配 + 召回规则 R1–R4 + 异体字归一。特征同 v1，另加「来源规则」标记。
# 遵守 PREREG：不使用书信关系代码 429–436。
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, collections, pickle, re, sys, os

DB = os.environ.get('CBDB_PATH', str(ROOT / 'data/cbdb_20261003.sqlite3'))
OUT = str(ROOT / 'disamb/pairs_v2.pkl')
LETTER_CODES = tuple(range(429, 437))
db = sqlite3.connect(DB)
q = lambda s, a=(): db.execute(s, a).fetchall()

VAR = str.maketrans({'荅': '答', '廵': '巡', '菴': '庵', '啓': '啟', '賔': '賓', '冡': '冢', '閤': '閣',
                     '敎': '教', '爲': '為', '眞': '真', '舘': '館', '叅': '參', '内': '內', '静': '靜', '靖': '靖', '蔵': '藏', '黄': '黃', '呉': '吳', '沈': '沈', '徳': '德', '衞': '衛', '昇': '昇'})
norm = lambda s: (s or '').translate(VAR)

person = {p: (norm(nm), norm(sur), yr, dy) for p, nm, sur, yr, dy in
          q('SELECT c_personid, c_name_chn, c_surname_chn, c_index_year, c_dy FROM BIOG_MAIN')}

SUFFIX = ('山人', '先生', '居士', '道人', '老人', '主人', '散人', '翁', '子')
lex = collections.defaultdict(list)                      # 串 -> [(pid, 类型)]
for p, (nm, _, _, _) in person.items():
    if len(nm) >= 2:
        lex[nm].append((p, 'name'))
for p, a, t in q('SELECT c_personid, c_alt_name_chn, c_alt_name_type_code FROM ALTNAME_DATA'):
    a = norm(a)
    if len(a) >= 2:
        lex[a].append((p, t))
        for sf in SUFFIX:                                # R3：剥后缀
            if a.endswith(sf) and len(a) - len(sf) >= 2:
                lex[a[:-len(sf)]].append((p, 'strip'))

given = collections.defaultdict(list)                    # R1：名(去姓) -> pid
for p, (nm, sur, _, _) in person.items():
    if sur and nm.startswith(sur) and 1 <= len(nm) - len(sur) <= 2:
        given[nm[len(sur):]].append(p)
SURNAMES = {sur for _, sur, _, _ in person.values() if sur}

# R2：官称关键词 -> 官名里须含的正式字串（非正式称谓做最小映射，其余按字面）
OFFICE_ALIAS = {'冢宰': ['吏部尚書'], '太宰': ['吏部尚書'], '冬官': ['工部'], '司空': ['工部'], '司馬': ['兵部'],
                '司寇': ['刑部'], '宗伯': ['禮部'], '中丞': ['都御史', '巡撫'], '巡按': ['巡按'], '巡撫': ['巡撫'],
                '總兵': ['總兵'], '總督': ['總督'], '郡守': ['知府'], '太守': ['知府'], '明府': ['知縣'],
                '觀察': ['按察', '副使'], '方伯': ['布政使'], '學憲': ['提學'], '督學': ['提學'],
                '閣老': ['大學士'], '相公': ['同中書門下平章事', '宰相', '大學士', '參知政事'], '相國': ['大學士', '宰相'],
                '侍郎': ['侍郎'], '尚書': ['尚書'], '參政': ['參政', '參知政事'], '資政': ['資政'], '侍講': ['侍講'],
                '運判': ['轉運判官'], '運使': ['轉運使'], '提刑': ['提點刑獄'], '知府': ['知府'], '知縣': ['知縣'],
                '太保': ['太保'], '太傅': ['太傅'], '少保': ['少保'], '御史': ['御史'], '給諫': ['給事中'],
                '大參': ['參政'], '憲副': ['副使'], '僉憲': ['僉事'], '司理': ['推官'], '別駕': ['同知'], '通府': ['同知']}
office_holders = collections.defaultdict(set)            # (姓, 关键词) -> pid
off_rows = q('''SELECT d.c_personid, c.c_office_chn FROM POSTED_TO_OFFICE_DATA d
                JOIN OFFICE_CODES c ON c.c_office_id = d.c_office_id WHERE c.c_office_chn IS NOT NULL''')
offices = collections.defaultdict(set)
for p, o in off_rows:
    o = norm(o); offices[p].add(o)
for p, os_ in offices.items():
    sur = person.get(p, ('', '', None, None))[1]
    if not sur:
        continue
    for kw, forms in OFFICE_ALIAS.items():
        if any(f in o for o in os_ for f in forms):
            office_holders[(sur, kw)].add(p)

nbr = collections.defaultdict(set)
for a, b in q(f'SELECT c_personid, c_assoc_id FROM ASSOC_DATA WHERE c_assoc_code NOT IN {LETTER_CODES} AND c_assoc_id > 0'):
    nbr[a].add(b); nbr[b].add(a)
kin = collections.defaultdict(set)                       # R4
for a, b in q('SELECT c_personid, c_kin_id FROM KIN_DATA WHERE c_kin_id > 0'):
    nbr[a].add(b); nbr[b].add(a); kin[a].add(b); kin[b].add(a)
addr = collections.defaultdict(set)
for p, ad in q('SELECT c_personid, c_addr_id FROM BIOG_ADDR_DATA WHERE c_addr_id > 0'):
    addr[p].add(ad)

letters = q('SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)')
ALT_TYPES = ['name', 4, 5, 3, 6, 7, 'strip']
RULES = ['词典', 'R1姓官名', 'R2姓官称', 'R4亲属']


def wyear(w):
    return person.get(w, ('', '', None, None))[2]


def candidates(title, writer):
    t = norm(title)
    hits = {}

    def add(pid, rule, s, typ, pos, L):
        if pid == writer:
            return
        h = hits.setdefault(pid, {'rules': set(), 's': s, 't': typ, 'prev': t[pos - 1] if pos > 0 else '',
                                  'pos': pos, 'L': L})
        h['rules'].add(rule)
    for L in (4, 3, 2):                                  # 词典（含 R3 剥后缀）
        for i in range(len(t) - L + 1):
            for pid, typ in lex.get(t[i:i + L], ()):
                add(pid, '词典', t[i:i + L], typ, i, L)
    for L in (2, 1):                                     # R1：姓 …(≤6字)… 名
        for j in range(1, len(t) - L + 1):
            g = t[j:j + L]
            for pid in given.get(g, ()):
                sur = person[pid][1]
                if sur and sur in t[max(0, j - 7):j]:
                    add(pid, 'R1姓官名', g, 'name', j, L)
    for kw in OFFICE_ALIAS:                              # R2：姓 + 官称
        for m in re.finditer(kw, t):
            pre = t[max(0, m.start() - 3):m.start()]
            for sur in dict.fromkeys(c for c in pre if c in SURNAMES):   # 按出现顺序；set 的顺序随 PYTHONHASHSEED 变
                for pid in office_holders.get((sur, kw), ()):
                    add(pid, 'R2姓官称', kw, 'office', m.start(), len(kw))
    for pid in kin.get(writer, ()):                      # R4：写信人亲属，名出现在标题
        nm, sur, _, _ = person.get(pid, ('', '', None, None))
        g = nm[len(sur):] if sur and nm.startswith(sur) else ''
        if g and g in t:
            add(pid, 'R4亲属', g, 'name', t.index(g), len(g))
    return t, hits


def feats(writer, t, pid, h, ncand):
    nm, sur, yr, dy = person[pid]
    _, _, wyr, wdy = person.get(writer, ('', '', None, None))
    era = abs(wyr - yr) if (wyr is not None and yr is not None) else -1
    rest = t[:h['pos']] + '□' * h['L'] + t[h['pos'] + h['L']:]
    f = [h['L'], h['prev'] == sur and sur != '', h['s'] == nm, sur != '' and sur in t,
         era, era == -1, wdy == dy,
         pid in nbr.get(writer, ()), len(nbr[writer] & nbr[pid]) if writer in nbr and pid in nbr else 0,
         len(nbr.get(pid, ())), len(addr[writer] & addr[pid]) > 0,
         any(o[-2:] in rest for o in offices.get(pid, ())), len(offices.get(pid, ())),
         ncand, len(lex.get(h['s'], ()))]
    f += [h['t'] == a for a in ALT_TYPES] + [h['t'] not in ALT_TYPES]
    f += [r in h['rules'] for r in RULES]
    return f


FEAT_NAMES = ['匹配长度', '前字=姓', '匹配本名', '姓出现在标题', '年代差', '年代缺失', '同朝代',
              '与写信人有关系', '共同关系人数', '候选人关系度数', '同地址', '标题含其官名后缀', '任官数',
              '候选总数', '该字符串同名人数'] + [f'类型={a}' for a in ALT_TYPES] + ['类型=其他'] + \
             [f'来源={r}' for r in RULES]


def build(rows_in):
    out = []
    for writer, gold, title in rows_in:
        t, c = candidates(title or '', writer)
        wy = wyear(writer)
        keep = {p: h for p, h in c.items()
                if person[p][2] is None or wy is None or abs(person[p][2] - wy) <= 150}
        out.append((writer, gold, title, [(p, feats(writer, t, p, h, len(keep)), sorted(h['rules']))
                                          for p, h in keep.items()]))
    return out


if __name__ == '__main__':
    rows = build(letters)
    pickle.dump({'rows': rows, 'feat_names': FEAT_NAMES}, open(OUT, 'wb'))
    tr = [r for r in rows if r[0] % 5]                  # 只在训练集上看召回
    rec = lambda rs: sum(any(p == r[1] for p, _, _ in r[3]) for r in rs) / len(rs)
    print('训练集召回(全部规则):', f'{rec(tr):.1%}', '| 平均候选', sum(len(r[3]) for r in tr) / len(tr))
    for rule in RULES:                                   # 每条规则的独占贡献
        only = sum(1 for r in tr if any(p == r[1] and rs == [rule] for p, _, rs in r[3]))
        print(f'  仅靠 {rule} 召回的金标: {only} ({only/len(tr):.1%})')
