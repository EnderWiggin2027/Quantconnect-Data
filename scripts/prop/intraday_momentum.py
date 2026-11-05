"""Gao, Han, Li & Zhou (2018, JFE) "Market intraday momentum" replication on ES / SPY x10 1-minute RTH bars.
r1  = previous RTH close (16:00) -> 10:00 close      r12 = 15:00 -> 15:30      r13 = 15:30 -> 16:00
Regression r13 = a + b1 r1 + b12 r12. Trading test: at 15:30 go long/short sign(r1), exit at 16:00, ES points per mini.
Usage: python scripts/prop/intraday_momentum.py <bars.csv.gz> [label]"""
import sys, numpy as np, pandas as pd
def days(path):
    df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['d'] = t.dt.date; df['m'] = t.dt.hour * 60 + t.dt.minute
    rows = []; prev = None
    for d, g in df.groupby('d', sort=True):
        m = g.m.to_numpy(); c = g.close.to_numpy(); o = g.open.to_numpy(); v = g.volume.to_numpy()
        full = m[0] == 571 and m[-1] == 960 and len(m) >= 380
        if full and prev is not None:
            px = lambda mm: c[np.searchsorted(m, mm)] if (m == mm).any() else np.nan
            p10, p15, p1530, p16 = px(600), px(900), px(930), c[-1]
            rv = np.std(np.diff(np.log(c[:np.searchsorted(m, 600) + 1])))       # first-30-min realised vol
            rows.append(dict(date=d, r1=np.log(p10 / prev), r12=np.log(p1530 / p15), r13=np.log(p16 / p1530), pts=p16 - p1530,
                             vol30=rv, volu=v[:np.searchsorted(m, 600) + 1].sum(), open_gap=np.log(o[0] / prev)))
        prev = c[-1] if full else None
    return pd.DataFrame(rows).dropna()
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + X); b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    XtXi = np.linalg.inv(X.T @ X); V = XtXi @ (X.T * e ** 2) @ X @ XtXi       # White SE
    return b, b / np.sqrt(np.diag(V)), 1 - e.var() / y.var()
def report(D, label, cost_pts=0.45):
    b, t, r2 = ols(D.r13.to_numpy(), [D.r1.to_numpy(), D.r12.to_numpy()]); b1, t1, r21 = ols(D.r13.to_numpy(), [D.r1.to_numpy()])
    print(f"\n=== {label}: {len(D)} days ===")
    print(f"  r13 ~ r1 + r12 : b1 {b[1]:+.4f} (t {t[1]:+.2f}) | b12 {b[2]:+.4f} (t {t[2]:+.2f}) | R2 {r2*100:.2f}%   [r1 only: t {t1[1]:+.2f}, R2 {r21*100:.2f}%]")
    s1 = np.sign(D.r1); s12 = np.sign(D.r12)
    def tr(name, sig, mask=None):
        x = (sig * D.pts)[mask] if mask is not None else sig * D.pts; x = x[sig[mask] != 0] if mask is not None else x[sig != 0]
        if len(x) < 30: return
        print(f"  {name:<44} n {len(x):>4} | gross {x.mean():+.2f} pts (t {x.mean()/x.std()*np.sqrt(len(x)):+.2f}) | hit {(x>0).mean()*100:4.1f}% | net {x.mean()-cost_pts:+.2f} pts/trade")
    tr("sign(r1)", s1); tr("sign(r1) when r1 and r12 agree", np.where(s1 == s12, s1, 0)); tr("sign(r12)  (15:00-15:30 direction)", s12)
    tr("sign(r12), |r12| above median", s12, D.r12.abs() > D.r12.abs().median())
    hv = D.vol30 > D.vol30.median(); hu = D.volu > D.volu.median(); big = D.r1.abs() > D.r1.abs().median()
    tr("sign(r1), high first-30-min volatility", s1, hv); tr("sign(r1), low first-30-min volatility", s1, ~hv)
    tr("sign(r1), high first-30-min volume", s1, hu); tr("sign(r1), |r1| above median", s1, big)
    tr("sign(r1), |r1| top 25%", s1, D.r1.abs() > D.r1.abs().quantile(0.75))
if __name__ == '__main__':
    report(days(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
