# 只统计数量，不看具体内容：旧版(2025-05-20) vs 新版(2026-10-03) 的书信金标差集
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import sqlite3, sys
OLD = sys.argv[1]
NEW = str(ROOT / 'data/cbdb_20261003.sqlite3')
SQL = 'SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)'
old = sqlite3.connect(OLD).execute(SQL).fetchall()
new = sqlite3.connect(NEW).execute(SQL).fetchall()
ok = {(w, t) for w, _, t in old}
added = [(w, g, t) for w, g, t in new if (w, t) not in ok]
print('旧版书信', len(old), '| 新版书信', len(new), '| 新增(写信人,标题)', len(added))
old_people = {p for (p,) in sqlite3.connect(OLD).execute('SELECT c_personid FROM BIOG_MAIN')}
print('新增书信中，收信人在旧版已存在:', sum(g in old_people for _, g, _ in added),
      '| 写信人在旧版已存在:', sum(w in old_people for w, _, _ in added))
print('新增书信涉及写信人数:', len({w for w, _, _ in added}),
      '| 其中写信人在旧版金标里也写过信:', len({w for w, _, _ in added} & {w for w, _, _ in old}))
