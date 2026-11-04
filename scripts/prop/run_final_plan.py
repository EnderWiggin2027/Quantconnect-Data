"""Reproduce the headline tables of docs/prop_firm_strategy.pdf.
  python scripts/prop/run_final_plan.py          # final plan (Lucid 3x150K+2xPro, FN 2xPro + 3x150K@$30k, MFF 3x150K+2x25K@$30k)
  python scripts/prop/run_final_plan.py --old    # also the earlier all-25K plans
  python scripts/prop/run_final_plan.py --multimarket   # earlier 1/5/10 synthetic-market test (slow)"""
import numpy as np, pandas as pd, sys, os, math, pickle, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..')); sys.path.insert(0, HERE)
from prop_sim import sim, accounts
from build_tape import run_file
from build_shapes import build as build_shapes
ES = os.path.join(ROOT, 'data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz')
def cached(path, fn):
    if not os.path.exists(path): print('building', os.path.relpath(path, ROOT)); fn(path)
    return path
TAPE = cached(os.path.join(ROOT, 'data/tapes/ES_tape_2022-2026.csv'), lambda p: run_file(ES).to_csv(p, index=False))
SHAPES = cached(os.path.join(ROOT, 'data/tapes/ES_shapes_2022-2026.pkl'), lambda p: pickle.dump(build_shapes(ES), open(p, 'wb')))
R = pd.read_csv(TAPE, parse_dates=['date']); G = pickle.load(open(SHAPES, 'rb'))
Rs = R[R.date.isin(G['days'])].reset_index(drop=True)
RATES = {'l150': (3.50, 1.00), 'pro': (3.50, 1.00), 'fnpro': (5.76, 1.74), 'fn150': (5.76, 1.74), 'mff150': (4.68, 1.74), 'mff': (4.68, 1.74)}  # round-trip $ per mini / micro
def comm(kind, size):
    mini, micro = RATES[kind]; w = math.floor(size + 1e-9); return mini * w + micro * round((size - w) * 10)
def dayd(kind, pts, ntr, size, t): return 50 * size * pts - ntr * (comm(kind, size) + size * t * 12.5)
def acct150(kind, eshape, esize, fshape, fsize, t, n):
    ie, jf = G['cfgs'].index(eshape), G['cfgs'].index(fshape)
    ce = dayd(kind, G['pts'][ie], G['ntr'][ie], esize, t); cf = dayd(kind, G['pts'][jf], G['ntr'][jf], fsize, t)
    return [dict(kind=kind, Ce=ce, Cf=cf, Cf2=cf) for _ in range(n)]
def acct25(kind, t):
    out = []
    for k in (0, 1):                                   # accounts A and B = Portfolio B slots 1 and 2
        e, f = f"eval_{k+1}", f"funded_{k+1}"
        pts = lambda c: Rs[c].to_numpy()
        out.append(dict(kind=kind, Ce=dayd(kind, pts(e + '_pts'), pts(e + '_n'), 2.0, t),
                        Cf=dayd(kind, pts(f + '_pts'), pts(f + '_n'), 1.8, t), Cf2=dayd(kind, pts(f + '_pts'), pts(f + '_n'), 0.9, t)))
    return out
ONE = lambda T: (1000, T, 0.01, None)                  # one trade/day, no stop, target T, done after the target fills
def final_plan(t):
    return (acct150('l150', ONE(7), 10, ONE(3), 10, t, 3) + acct25('pro', t) + acct25('fnpro', t) +
            acct150('fn150', ONE(8), 8, ONE(3), 8, t, 3) + acct150('mff150', ONE(11), 9, ONE(4), 9, t, 3) + acct25('mff', t))
TRIG = {'fn150': 30000.0, 'mff150': 30000.0, 'mff': 30000.0}
if __name__ == '__main__':
    print("FINAL PLAN, real ES 2022-2026, start $12,000 | medians: spent / payouts / NET (5th pct, P(loss))")
    for t in (1, 3):
        o = sim(final_plan(t), np.random.default_rng(3), trig=TRIG, snaps=(42, 126, 252))
        print(f"\n  {t} tick slippage")
        for d, h in ((42, '2 months'), (126, '6 months'), (252, '12 months')):
            net, fees, paid, nev = o[d]
            print(f"    {h:<10} spent ${np.median(fees):>8,.0f} | payouts ${np.median(paid):>9,.0f} | NET ${np.median(net):>+9,.0f}  (5th ${np.percentile(net,5):>+8,.0f}, P(loss) {(net<0).mean()*100:.1f}%) | evals {np.median(nev):.0f}")
    if '--old' in sys.argv or '--multimarket' in sys.argv:
        subprocess.run([sys.executable, os.path.join(HERE, 'run_25k_plans.py')] + sys.argv[1:], check=True)
