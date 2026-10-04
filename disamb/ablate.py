# 特征组消融 + 别名来源泄漏检查（仅用于诊断；测试集结果不用于调参）
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parent.parent
import pickle, sqlite3, collections, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

D = pickle.load(open(str(ROOT / 'disamb/pairs.pkl'), 'rb'))
rows, names = D['rows'], D['feat_names']
train = [r for r in rows if r[0] % 5]
test = [r for r in rows if r[0] % 5 == 0]
G = {
    '关系': ['与写信人有关系', '共同关系人数', '同地址'],
    '名气': ['候选人关系度数', '任官数'],
    '别名元数据': [n for n in names if n.startswith('类型=')] + ['该字符串同名人数'],
    '年代': ['年代差', '年代缺失', '同朝代'],
    '字面匹配': ['匹配长度', '前字=姓', '匹配本名', '姓出现在标题', '标题含其官名后缀'],
}


def run(keep):
    idx = [names.index(n) for n in keep]
    X = np.array([[f[i] for i in idx] for r in train for _, f in r[3]], float)
    y = np.array([p == r[1] for r in train for p, _ in r[3]])
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)
    ok = []
    for w, g, _, cs in test:
        if len(cs) > 1 and any(p == g for p, _ in cs):
            s = m.predict_proba(np.array([[f[i] for i in idx] for _, f in cs], float))[:, 1]
            ok.append(cs[int(s.argmax())][0] == g)
    return np.mean(ok)


print(f'全部特征: {run(names):.1%}')
for g, fs in G.items():
    print(f'去掉 {g}: {run([n for n in names if n not in fs]):.1%}   只用 {g}: {run(fs):.1%}')

# 别名来源：金标命中的别名，其 c_source 是否等于该书信的文集来源
db = sqlite3.connect(str(ROOT / 'data/cbdb_20261003.sqlite3'))
q = lambda s, a=(): db.execute(s, a).fetchall()
asrc = collections.defaultdict(set)
for p, a, s in q('SELECT c_personid, c_alt_name_chn, c_source FROM ALTNAME_DATA'):
    asrc[(p, a)].add(s)
lsrc = {(w, g, t): s for w, g, t, s in q('SELECT c_personid,c_assoc_id,c_text_title,c_source FROM ASSOC_DATA WHERE c_assoc_code IN (429,431,433,435)')}
tot = same = 0
for (w, g, t), s in lsrc.items():
    hits = [a for (p, a) in asrc if False]  # 占位
for (p, a), ss in asrc.items():
    pass
# 直接按书信逐条查：标题中出现的金标别名
alt_by_p = collections.defaultdict(list)
for (p, a), ss in asrc.items():
    alt_by_p[p].append((a, ss))
for (w, g, t), s in lsrc.items():
    m = [(a, ss) for a, ss in alt_by_p[g] if a and len(a) >= 2 and a in t]
    if m:
        tot += 1; same += any(s in ss for _, ss in m)
print(f'\n标题命中金标别名的书信 {tot}；其中该别名来源 = 本信文集: {same} ({same/tot:.1%})')
