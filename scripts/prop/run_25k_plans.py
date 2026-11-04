"""Earlier all-25K plans (section "How the plan evolved" in docs/prop_firm_strategy.pdf).
  python scripts/prop/run_25k_plans.py              # real ES plans A/B/C (needs data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz)
  python scripts/prop/run_25k_plans.py --multimarket # also 1/5/10 independent synthetic markets (generates ~10 synthetic files, slow)
Results are Monte Carlo (seeded) so they match the PDF to within a few hundred dollars / tenths of a percent."""
import numpy as np, pandas as pd, sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import prop_sim
from prop_sim import sim, accounts
from build_tape import run_file
def tape(src, dst):
    if not os.path.exists(dst):
        print('building tape', dst); run_file(src).to_csv(dst, index=False)
    T = pd.read_csv(dst, parse_dates=['date']); return T
H = ((21, '1mo'), (42, '2mo'), (126, '6mo'), (252, '12mo'))
fmt = lambda o: " | ".join(f"{h}: {np.median(o[d][0]):>+9,.0f} / {np.percentile(o[d][0],5):>+8,.0f} / {(o[d][0]<0).mean()*100:4.1f}%" for d, h in H)
PLANS = (("A: Lucid Pro + FN Pro day 1, MFF at $30k", {'mff': 30000.0}),
         ("B: Lucid Pro day 1, FN Pro + MFF at $30k", {'fnpro': 30000.0, 'mff': 30000.0}),
         ("C: all three from day 1", {}))
def run(Ds, t):
    A, i = [], 0
    for kind in ('pro', 'fnpro', 'mff'):
        for k in range(5):
            A += accounts(Ds[i % len(Ds)], t, np.ones(len(Ds[0]), bool), kind, [k]); i += 1
    for lbl, trig in PLANS:
        print(f"  {lbl:<44}" + fmt(sim(A, np.random.default_rng(3), trig=trig, snaps=tuple(d for d, _ in H))))
if __name__ == '__main__':
    R = tape(os.path.join(ROOT, 'data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz'), os.path.join(ROOT, 'data/tapes/ES_tape_2022-2026.csv'))
    print("cells = median / 5th percentile / P(loss), start $12,000")
    for t in (1, 3):
        print(f"\n=== REAL ES 2022-2026, {t} tick slippage ==="); run([R], t)
    if '--multimarket' in sys.argv:
        Ds = []
        for s in range(1, 11):
            src = os.path.join(ROOT, f'data/synthetic/ES_synth_1m_10y_seed{s}.csv.gz')
            if not os.path.exists(src):
                subprocess.run([sys.executable, os.path.join(ROOT, 'scripts/synth_es.py'), '--years', '10', '--seed', str(s), '--out', src], check=True, cwd=ROOT)
            Ds.append(tape(src, os.path.join(ROOT, f'data/tapes/synth_tape_seed{s}.csv')))
        L = min(len(d) for d in Ds); Ds = [d.iloc[:L].reset_index(drop=True) for d in Ds]
        for t in (1, 3):
            for nm in (1, 5, 10):
                print(f"\n=== SYNTHETIC, {nm} independent market(s), {t} tick ==="); run(Ds[:nm], t)
