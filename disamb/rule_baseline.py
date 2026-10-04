# 更强的手写规则基线（不训练）：姓/本名匹配 > 匹配长度 > 年代合理 > 同名人少 > 关系度数高
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, numpy as np
D = pickle.load(open(str(ROOT / 'disamb/pairs.pkl'), 'rb'))
rows, N = D['rows'], D['feat_names']
i = {n: N.index(n) for n in N}
test = [r for r in rows if r[0] % 5 == 0]


def key(f):
    era = f[i['年代差']]
    return (bool(f[i['前字=姓']] or f[i['匹配本名']]), f[i['匹配长度']],
            era == -1 or era <= 60, -f[i['该字符串同名人数']], f[i['候选人关系度数']])


full, amb = [], []
for w, g, _, cs in test:
    if not cs:
        full.append(False); continue
    top = max(cs, key=lambda c: key(c[1]))[0]
    full.append(top == g)
    if len(cs) > 1 and any(p == g for p, _ in cs):
        amb.append(top == g)
print(f'规则基线 全量 Top-1 {np.mean(full):.1%} | 多候选含金标子集 {np.mean(amb):.1%} (n={len(amb)})')
