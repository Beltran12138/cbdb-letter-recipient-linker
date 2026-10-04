# 诊断（事后）：困难划分上的 Top-k 召回——作为「给人工审核的候选短名单」是否有用
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import numpy as np, csv, pickle
exec(open('run2.py', encoding='utf-8').read().split('# 1. 标准划分')[0])
cs_ = list(csv.reader(open(str(ROOT / 'csa/newtask.csv'), encoding='utf-8-sig')))
hdr, data = cs_[1], cs_[2:]
c = {h: i for i, h in enumerate(hdr)}
cw = {int(r[c['人物id']]) for r in data if r[c['人物id']].strip()}
late = {(int(r[c['人物id']]), r[c['作品標題']]) for r in data if r[c['人物id']].strip() and not r[c['通訊人']].strip()}
test = [r for r in rows if (r[0], r[2]) in late]
m = fit([r for r in rows if r[0] not in cw])
for k in (1, 3, 5, 10):
    hit = 0
    for w, gold, _, cs in test:
        if cs:
            s = m.predict_proba(np.array([f for _, f in cs], float))[:, 1]
            hit += gold in [cs[i][0] for i in np.argsort(-s)[:k]]
    print(f'Top-{k}: {hit/len(test):.1%}')
print('候选数中位数:', int(np.median([len(r[3]) for r in test])))
