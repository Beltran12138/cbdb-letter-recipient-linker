from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()

print('ASSOC_DATA 字段:', [r[1] for r in q('PRAGMA table_info(ASSOC_DATA)')])
print('ALTNAME_DATA 字段:', [r[1] for r in q('PRAGMA table_info(ALTNAME_DATA)')])
print('BIOG_MAIN 人数:', q('SELECT COUNT(*) FROM BIOG_MAIN')[0][0])

# 书信类关系代码
codes = q("""SELECT c_assoc_code, c_assoc_desc_chn, c_assoc_desc FROM ASSOC_CODES
             WHERE c_assoc_desc_chn LIKE '%書%' OR c_assoc_desc_chn LIKE '%信%' OR c_assoc_desc LIKE '%letter%'""")
print('\n书信类关系代码数:', len(codes))
for c in codes[:40]:
    n = q('SELECT COUNT(*) FROM ASSOC_DATA WHERE c_assoc_code=?', (c[0],))[0][0]
    print(c[0], c[1], '|', c[2], '| 条数', n)
