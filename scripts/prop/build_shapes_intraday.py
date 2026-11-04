"""Shape tapes WITH worst intraday excursion, for accounts that fail when intraday equity touches the drawdown floor.
Direction = 10:00 close vs 09:30 open (all accounts). Entry at the 10:00 bar close. Per config and day:
  pts  = closed points per 1 contract (before costs), ntr = trades, worst = lowest intraday point (closed + open, <= 0).
Configs (S, T, cap, lstop): stop S pts (1000 = none), target T pts, stop for the day once closed >= cap or <= -lstop,
max 8 trades, no new entries after 15:30, exit at the last bar. One-trade shapes use cap = 0.01 and lstop = 0.01.
Intrabar: if a bar reaches both stop and target, the stop counts first; worst includes the adverse move of the exit bar.
Usage: python scripts/prop/build_shapes_intraday.py <bars.csv.gz> <out.pkl>"""
import numpy as np, pandas as pd, pickle, sys, time

ONE_S = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 1000)
ONE_T = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 20)
CF = [(S, T, 0.01, 0.01) for S in ONE_S for T in ONE_T]
CF += [(X, X, cap, ls) for X in (2, 3, 4, 5, 6, 8, 10, 12) for cap in (0.01, 1.5 * X) for ls in (1000, 2 * X, 3 * X)]

def trade(h, l, c, k0, s, S, T, kend):
    """Returns (points, exit bar, max adverse excursion >= 0)."""
    e = c[k0]; hh = h[k0 + 1:kend + 1]; ll = l[k0 + 1:kend + 1]; N = len(hh)
    if N == 0: return 0.0, k0, 0.0
    fav = (hh - e) if s > 0 else (e - ll); adv = np.maximum.accumulate((e - ll) if s > 0 else (hh - e))
    kS = np.searchsorted(adv, S, 'left'); kT = np.searchsorted(np.maximum.accumulate(fav), T, 'left')
    if kS < N and kS <= kT: return -S, k0 + 1 + kS, S
    if kT < N: return T, k0 + 1 + kT, max(adv[kT], 0.0)
    return s * (c[kend] - e), kend, max(adv[-1], 0.0)

def build(path):
    t0 = time.time(); df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['date'] = t.dt.date; df['m'] = t.dt.hour * 60 + t.dt.minute
    days, P, N, W = [], [], [], []
    for day, g in df.groupby('date', sort=True):
        m, o, h, l, c = (g[k].to_numpy() for k in ('m', 'open', 'high', 'low', 'close'))
        if m[0] != 571 or len(m) < 300: continue
        last = len(m) - 1; i600 = np.searchsorted(m, 600); stop_k = np.searchsorted(m, 930, 'right') - 1
        s = np.sign(c[i600] - o[0])
        if s == 0: continue
        rp, rn, rw = [], [], []
        for S, T, cap, ls in CF:
            kk = i600; tot = 0.0; n = 0; worst = 0.0
            while n < 8 and kk < stop_k:
                p, kx, mae = trade(h, l, c, kk, s, S, T, last)
                worst = min(worst, tot - mae); tot += p; n += 1; kk = kx + 1
                if tot >= cap or tot <= -ls: break
            rp.append(tot); rn.append(n); rw.append(min(worst, tot))
        days.append(day); P.append(rp); N.append(rn); W.append(rw)
    print(path, len(days), 'days', round(time.time() - t0), 's', flush=True)
    return dict(cfgs=CF, days=pd.to_datetime(days), pts=np.array(P).T, ntr=np.array(N, dtype=np.int16).T, worst=np.array(W).T)

if __name__ == '__main__':
    pickle.dump(build(sys.argv[1]), open(sys.argv[2], 'wb'))
