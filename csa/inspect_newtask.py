from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import csv, collections, sqlite3
rows = list(csv.reader(open(str(ROOT / 'csa/newtask.csv'), encoding='utf-8-sig')))
hdr, data = rows[1], rows[2:]
col = {h: i for i, h in enumerate(hdr)}
print('列:', hdr)
print('数据行:', len(data))
filled = [r for r in data if r[col['通訊人']].strip()]
empty = [r for r in data if not r[col['通訊人']].strip()]
print(f'已填收信人: {len(filled)} | 空(待识别): {len(empty)}')
print('写信人数:', len({r[col['人物id']] for r in data}), '| 文集数:', len({r[col['文集']] for r in data}))
print('文集 Top5:', collections.Counter(r[col['文集']] for r in data).most_common(5))

# 已填的收信人，是否已经进了 CBDB 书信金标？
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
gold = {(w, t) for w, t in db.execute('SELECT c_personid, c_text_title FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)')}
in_gold = sum(1 for r in data if (int(r[col['人物id']] or 0), r[col['作品標題']]) in gold)
print(f'(写信人, 标题) 已在 CBDB 金标中: {in_gold}/{len(data)}')
emp_in_gold = sum(1 for r in empty if (int(r[col['人物id']] or 0), r[col['作品標題']]) in gold)
print(f'空行中已在 CBDB 金标里(即后来被识别了): {emp_in_gold}/{len(empty)}')
import random; random.seed(1)
print('\n空行样例:')
for r in random.sample(empty, 12):
    print(f"  {r[col['作者']]} 《{r[col['作品標題']]}》 ({r[col['文集']]})")
