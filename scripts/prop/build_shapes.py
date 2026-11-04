"""One-trade / loop "shape" tapes for the 150K playbooks: per day, points per 1 contract (before costs) and trades.
Direction = 10:00 close vs 09:30 open. Usage: python scripts/prop/build_shapes.py <bars.csv.gz> <out.pkl>"""
import numpy as np, pandas as pd, itertools, pickle, sys, time
def trade(h, l, c, k0, s, S, T, kend):
    e = c[k0]; hh = h[k0+1:kend+1]; ll = l[k0+1:kend+1]; N = len(hh)
    if N == 0: return 0.0, k0
    fav = (hh - e) if s > 0 else (e - ll); adv = (e - ll) if s > 0 else (hh - e)
    kS = np.searchsorted(np.maximum.accumulate(adv), S, 'left'); kT = np.searchsorted(np.maximum.accumulate(fav), T, 'left')
    if kS < N and kS <= kT: return -S, k0 + 1 + kS
    if kT < N: return T, k0 + 1 + kT
    return s * (c[kend] - e), kend
CF = [(1000, 7, 0.01, None), (1000, 8, 0.01, None), (1000, 11, 0.01, None), (1000, 3, 0.01, None), (1000, 4, 0.01, None)]   # (stop pts, target pts, daily profit cap, daily loss stop); stop 1000 = none; cap 0.01 = done after first net win
def build(path):
    t0 = time.time(); df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['date'] = t.dt.date; df['m'] = t.dt.hour * 60 + t.dt.minute
    days = []; P = []; N = []
    for day, g in df.groupby('date', sort=True):
        m, o, h, l, c = (g[k].to_numpy() for k in ('m', 'open', 'high', 'low', 'close'))
        if m[0] != 571 or len(m) < 300: continue
        last = len(m) - 1; i600 = np.searchsorted(m, 600); stop_k = np.searchsorted(m, 930, 'right') - 1
        s = np.sign(c[i600] - o[0])
        if s == 0: continue
        rp, rn = [], []
        for S, T, Dc, Lc in CF:
            kk = i600; tot = 0.0; n = 0
            while n < 8 and kk < stop_k:
                p, kx = trade(h, l, c, kk, s, S, T, last); tot += p; n += 1; kk = kx + 1
                if (Dc and tot >= Dc) or (Lc and tot <= -Lc): break
            rp.append(tot); rn.append(n)
        days.append(day); P.append(rp); N.append(rn)
    print(path, len(days), 'days', round(time.time() - t0), 's', flush=True)
    return dict(cfgs=CF, days=pd.to_datetime(days), pts=np.array(P).T, ntr=np.array(N, dtype=np.int16).T)
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; pickle.dump(build(src), open(dst, 'wb'))
