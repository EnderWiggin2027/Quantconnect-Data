"""Reproduce the INTRADAY-BREACH results in docs/prop_firm_strategy.pdf (dynamic bold play, scripts/prop/dyn.py).
  python scripts/prop/run_intraday.py          # real ES 2022-2026
  python scripts/prop/run_intraday.py --spy    # also SPY x10 2018-2021 (out of sample) and 2022-2025"""
import sys, os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..')); sys.path.insert(0, HERE)
from dyn import prep, trade, eval_run, funded_run, business
from prop_sim import FEE
# policies chosen on synthetic ES (seeds 1-3), validated on real ES and synthetic seeds 4-10
POL = {'l150': ((5, 0.4, 1.0), (2, 1.1, 1.0, 600, 1.0)), 'fn150': ((4, 0.4, 1.0), (2, 1.1, 1.0, 600, 1.0)),
       'pro': ((1.0, 1.5, 1.0), (1.0, 0.6, 1.0, 700, 1.0)), 'fnpro': ((1.0, 1.5, 1.0), (0.5, 0.6, 1.0, 260, 1.0))}
NAME = {'l150': 'Lucid 150K Flex', 'fn150': 'FundedNext 150K', 'pro': 'Lucid 25K Pro', 'fnpro': 'FundedNext 25K Pro'}
def table(src, dst):
    if not os.path.exists(dst): np.savez_compressed(dst, **prep(src))
    return dict(np.load(dst))
def spy_csv(a, b, dst):
    if os.path.exists(dst): return dst
    df = pd.read_parquet(os.path.join(ROOT, 'SPY_1m_Cleaned Parquet.parquet'))
    t = pd.to_datetime(df.Date, utc=True).dt.tz_convert('America/New_York') + pd.Timedelta(minutes=1); m = t.dt.hour * 60 + t.dt.minute
    k = (m >= 571) & (m <= 960) & (t >= a) & (t <= b + ' 23:59'); x = df[k]; tt = t[k]
    pd.DataFrame({'time': tt.dt.strftime('%Y-%m-%d %H:%M:%S%z'), 'open': x.Open * 10, 'high': x.High * 10, 'low': x.Low * 10,
                  'close': x.Close * 10, 'volume': x.Volume}).to_csv(dst, index=False)
    return dst
def report(lbl, T):
    print(f"\n=== {lbl} ({len(T['CL'])} days) ===")
    d = np.arange(len(T['CL'])); row = []
    for S, Tt in ((2, 20), (3, 30), (5, 40), (10, 40)):
        p, _ = trade(T, d, np.full(len(d), float(S)), np.full(len(d), float(Tt))); row.append(f"S{S}/T{Tt} {p.mean():+.2f} (t {p.mean()/p.std()*np.sqrt(len(p)):+.1f})")
    print("  trend-day edge, gross pts/trade: " + " | ".join(row))
    for t in (1.5, 3.0):
        for k in POL:
            p, de = eval_run(T, k, POL[k][0], t=t, P=20000); V, df = funded_run(T, k, POL[k][1], t=t, P=6000)
            print(f"  {t} ticks  {NAME[k]:<19} pass {p*100:4.1f}% | $ per funded acct {V:>6,.0f} | EV per attempt {p*V-FEE[k]:>+5,.0f} (fee {FEE[k]:.0f})")
    S = lambda k, n: [(k, *POL[k])] * n
    for nm, specs, bank in (("Lucid 25K Pro x1, $12k", S('pro', 1), 12e3), ("Lucid 25K Pro x2, $12k", S('pro', 2), 12e3),
                            ("Lucid 150K x1 + FN 150K x1, $30k", S('l150', 1) + S('fn150', 1), 30e3), ("Lucid 25K Pro x5, $12k", S('pro', 5), 12e3)):
        o = business(T, specs, bank=bank)
        print(f"  {nm:<34}" + " | ".join(f"{h}: {np.median(o[d][0]):>+7,.0f} / mean {o[d][0].mean():>+7,.0f} / P(loss) {(o[d][0]<0).mean()*100:4.1f}%" for d, h in ((42, '2mo'), (252, '12mo'))))
if __name__ == '__main__':
    report("REAL ES 2022-2026, intraday breach", table(os.path.join(ROOT, 'data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz'), os.path.join(ROOT, 'data/tapes/ES_dyn_2022-2026.npz')))
    if '--spy' in sys.argv:
        for a, b, tag in (('2018-05-01', '2021-12-31', '2018-2021 (out of sample)'), ('2022-01-01', '2025-12-31', '2022-2025')):
            src = spy_csv(a, b, os.path.join(ROOT, f'data/tapes/SPYx10_{a[:4]}_{b[:4]}.csv.gz'))
            report(f"SPY x10 {tag}", table(src, os.path.join(ROOT, f'data/tapes/SPYx10_dyn_{a[:4]}_{b[:4]}.npz')))
