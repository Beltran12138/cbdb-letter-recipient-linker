# 解压 2022-07 版，并只统计 2022-07 → 2023-03 窗口内新增书信的数量
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import py7zr, glob, sqlite3, os
D = str(ROOT / 'data')
os.chdir(D)
if not glob.glob('old_20220727/*.db'):
    with py7zr.SevenZipFile('CBDB_20220727.7z') as z:
        print(z.getnames()); z.extractall('old_20220727')
f = glob.glob('old_20220727/*.db')[0]
SQL = 'SELECT c_personid, c_assoc_id, c_text_title FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)'
a = sqlite3.connect(f).execute(SQL).fetchall()
b = sqlite3.connect('old_20230324/cbdb_data_20230324.db').execute(SQL).fetchall()
ka = {(w, t) for w, _, t in a}
add = [r for r in b if (r[0], r[2]) not in ka]
titled = [r for r in add if r[2] and r[2].strip() not in ('[n/a]', '')]
print(f, '| 2022-07 书信', len(a), '| 2023-03 书信', len(b), '| 窗口内新增', len(add), '| 其中有标题', len(titled))
