"""Multi-firm prop-account Monte Carlo (shared bankroll, day-level bootstrap). Tracks cash, fees spent, payouts received.
Account kinds: l150 = Lucid 150K Flex | pro = Lucid 25K Pro (loss limit off) | fn150 = FundedNext 150K Flex | fnpro = FundedNext 25K Pro
mff150 = MyFundedFutures 150K | mff = MyFundedFutures 25K | ph150 = Phidias 150K. Older/rejected kinds kept for reference: flex, fn, tfy, tfs, tfd.
Each account dict: kind, Ce (evaluation day $), Cf (funded day $), optional Cf2 (funded day $ after first payout).
sim(...)[day] = (net cash change, fees spent, payouts received, evaluations bought). See docs/prop_firm_strategy.pdf."""
import numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presets import NAMES
EBv, FBv = [3.5, 3.5, 2.5, 2.5, 3.5], [3, 3, 4, 3, 4]
def day(D, n, s, t, m, dll=None):
    pnl = (s * (50 * D[n + '_pts'] - D[n + '_n'] * (3.5 + t * 12.5))).to_numpy()
    if dll:
        tr = (s * (50 * D[n + '_tr'] - D[n + '_n'] * (3.5 + t * 12.5))).to_numpy(); hit = tr <= -dll
        return np.where(hit, -dll, pnl)[m], hit[m]
    return pnl[m]
def accounts(D, t, m, kind, slots):
    out = []
    for k in slots:
        if kind in ('pro', 'fnpro', 'mff'):  se, sf = min(2.0, round(EBv[k] * 0.6 * 10) / 10), min(2.0, round(FBv[k] * 0.6 * 10) / 10)
        elif kind == 'flex': se, sf = EBv[k], FBv[k]
        elif kind in ('tfs', 'tfd'):
            se, sf = min(1.0, round(EBv[k] * TFS['ke'] * 10) / 10), min(1.0, round(FBv[k] * TFS['kf'] * 10) / 10)
            cf = day(D, NAMES[5 + k], sf, t, m, 500.0)[0] if kind == 'tfd' else day(D, NAMES[5 + k], sf, t, m)
            out.append(dict(kind=kind, Ce=day(D, NAMES[k], se, t, m), Cf=cf)); continue
        elif kind == 'tfy':
            se, sf = min(1.0, round(EBv[k] * TFY['ke'] * 10) / 10), min(1.0, round(FBv[k] * TFY['kf'] * 10) / 10)
            ce, eh = day(D, NAMES[k], se, t, m, 600.0); cf, _ = day(D, NAMES[5 + k], sf, t, m, 600.0)
            out.append(dict(kind=kind, Ce=ce, Cf=cf, Eh=eh)); continue
        else:              se, sf = min(3.0, round(EBv[k] * 0.85 * 10) / 10), min(3.0, round(FBv[k] * 0.85 * 10) / 10)
        out.append(dict(kind=kind, Ce=day(D, NAMES[k], se, t, m), Cf=day(D, NAMES[5 + k], sf, t, m)))
    return out
FEE = dict(pro=100.0, flex=150.0, fn=140.0, fnpro=85.0, tfy=59.0, tfs=76.0, tfd=76.0)
TFS = dict(ke=0.3, kf=0.3)
MFF = dict(cap=1e9)
FEE['mff'] = 98.0
FEE['l150'] = 265.3
FEE['fn150'] = 259.99
FEE['mff150'] = 334.0
FEE['ph150'] = 190.0
PH = dict(keep=1000.0, cap=2750.0, cons=0.3, qd=10, split=0.8)   # Phidias 150K funded: buffer left after payout, cap/cycle, consistency, qualifying days, split
TFY = dict(ke=0.3, kf=0.3, fail=False)
def sim(accts, rng, trig=None, P=10000, D=252, bank=12000.0, snaps=(42, 126, 252), post=0.5):
    """trig: dict kind->cash level at which that kind's accounts start (default 0)."""
    trig = trig or {}; K = len(accts); L = len(accts[0]['Ce'])
    ph = np.full((K, P), 3, np.int8); b, h, bd, q, c0, n, g = (np.zeros((K, P)) for _ in range(7))
    on = np.zeros((K, P), bool); cash = np.full(P, bank); out = {}; FEES = np.zeros(P); PAID = np.zeros(P); NEV = np.zeros(P)
    for d in range(1, D + 1):
        ix = rng.integers(0, L, P)
        for j, a in enumerate(accts):
            k = a['kind']; on[j] |= cash >= trig.get(k, 0.0); p = ph[j]
            new = (p == 3) & on[j] & (cash >= FEE[k]); cash -= np.where(new, FEE[k], 0); FEES += np.where(new, FEE[k], 0); NEV += new; p = np.where(new, 0, p)
            if k == 'fn':
                rs = (p == 4) & (cash >= 85.0); cash -= np.where(rs, 85.0, 0); FEES += np.where(rs, 85.0, 0); NEV += rs; p = np.where(rs, 0, p)
            ev = p == 0; fu = p == 1
            cf_now = np.where(n[j] > 0, a['Cf2'][ix], a['Cf'][ix]) if 'Cf2' in a else a['Cf'][ix] * np.where(n[j] > 0, a.get('post', post), 1.0)
            c = np.where(ev, a['Ce'][ix], np.where(fu, cf_now, 0.0))
            bj = np.where(ev | fu, b[j] + c, b[j]); hj = np.where(ev | fu, np.maximum(h[j], bj), h[j])
            if k == 'mff150':
                floor = np.where(fu & (n[j] > 0), 100.0, hj - 4500)
            elif k == 'fn150':
                floor = np.where(fu & (n[j] > 0), 100.0, np.where(hj >= 4100, 100.0, hj - 4000))
            elif k == 'l150':
                floor = np.where(fu & (n[j] > 0), 100.0, np.where(hj >= 4600, 100.0, hj - 4500))
            elif k == 'ph150':
                floor = np.where(fu, np.minimum(hj - 4500, 0.0), hj - 4500)
            elif k in ('pro', 'fnpro', 'tfy', 'tfs', 'tfd', 'mff'):
                floor = np.where(fu, np.minimum(hj - 1000, 100.0), hj - 1000)
            elif k == 'flex':
                floor = np.where(fu & (n[j] > 0), 100.0, np.minimum(hj - 2000, 0.0))
            else:
                floor = np.where(fu, np.minimum(hj - 1500, 100.0), hj - 1500)
            bust = (ev | fu) & (bj <= floor)
            if k == 'tfy' and TFY['fail']: bust |= ev & a['Eh'][ix]
            bdj = np.where(~bust & (ev | fu), np.maximum(bd[j], c), bd[j])
            if k == 'mff150': evd = q[j] + ev; passed = ev & ~bust & (bj >= np.maximum(9000, bdj / 0.5)) & (evd >= 2)
            elif k == 'fn150': evd = q[j] + ev; passed = ev & ~bust & (bj >= np.maximum(8000, bdj / 0.4)) & (evd >= 3)
            elif k == 'l150': passed = ev & ~bust & (bj >= np.maximum(9000, bdj / 0.4))
            elif k == 'pro':  passed = ev & ~bust & (bj >= 1250)
            elif k == 'ph150': passed = ev & ~bust & (bj >= 9000)
            elif k in ('fnpro', 'tfy'): passed = ev & ~bust & (bj >= 1500)
            elif k == 'mff': evd = q[j] + ev; passed = ev & ~bust & (bj >= np.maximum(1500, bdj / 0.3)) & (evd >= 4)
            elif k in ('tfs', 'tfd'): passed = ev & ~bust & (bj >= np.maximum(1500, bdj / 0.4))
            elif k == 'flex': passed = ev & ~bust & (bj >= 3000) & (bdj <= 1500)
            else:           passed = ev & ~bust & (bj >= np.maximum(2500, bdj / 0.4))
            fa = fu & ~bust; cyc = bj - c0[j]
            qj = q[j] + (fa & (c >= (150 if k == 'flex' else 200)))
            if k == 'mff150':
                qj = np.where(ev, evd, q[j] + fa); amt = 0.6 * bj; ok = fa & (qj >= 10) & (amt >= 1000); split = 0.80
            elif k == 'fn150':
                qj = np.where(ev, evd, q[j] + (fa & (c >= 250))); amt = np.minimum(0.5 * bj, 4000.0); ok = fa & (qj >= 5) & (cyc >= 500) & (amt > 0); split = 0.95
            elif k == 'l150':
                qj = q[j] + (fa & (c >= 250)); amt = np.minimum(0.5 * bj, 3000.0); ok = fa & (qj >= 5) & (cyc > 0) & (amt >= 500); split = 0.9
            elif k == 'ph150':
                qj = q[j] + fa; amt = np.minimum(PH['cap'], bj - PH['keep'])
                ok = fa & (qj >= PH['qd']) & (bdj <= PH['cons'] * cyc) & (amt >= 500); split = PH['split']
            elif k == 'mff':
                qj = np.where(ev, evd, qj)
                amt = np.minimum(bj - 1100, MFF['cap']); ok = fa & (cyc >= 250) & (amt >= 500); split = 0.9
            elif k == 'tfs':
                amt = np.minimum(0.5 * bj, 1250.0); ok = fa & (qj >= 5) & (cyc > 0) & (amt >= 250); split = 0.9
            elif k == 'tfd':
                amt = np.minimum(0.5 * bj, 600.0); ok = fa & (cyc > 0) & (amt >= 100); split = 0.9
            elif k == 'tfy':
                amt = np.minimum(0.5 * bj, 1000.0); ok = fa & (qj >= 5) & (cyc > 0) & (bdj <= 0.35 * cyc) & (amt >= 250); split = 0.9
            elif k == 'fnpro':
                qj = q[j] + fa
                amt = np.minimum(0.5 * bj, 800.0); ok = fa & (qj >= 3) & (cyc > 0) & (bdj <= 0.4 * cyc) & (amt >= 250); split = 0.9
            elif k == 'pro':
                amt = np.minimum(bj - 1100, np.where(n[j] == 0, 1000.0, 1500.0)); ok = fa & (cyc >= 250) & (bdj <= 0.4 * cyc) & (amt >= 500); split = 0.9
            elif k == 'flex':
                amt = np.minimum(0.5 * bj, 2000.0); ok = fa & (qj >= 5) & (bj >= 1000) & (amt >= 500); split = 0.9
            else:
                amt = np.minimum(0.5 * bj, 1500.0); ok = fa & (qj >= 5) & (cyc >= 500) & (amt >= 250); split = 0.95
            amt = np.where(ok, amt, 0.0); cash += split * amt; PAID += split * amt; bj = bj - amt
            nj = n[j] + ok; gj = g[j] + amt
            c0j = np.where(ok, bj, c0[j]); qj = np.where(ok, 0, qj)
            bdj = np.where(fu & ok, 0.0, bdj)
            if k == 'flex': closed = fa & (gj >= 8000); cash += np.where(closed, 900.0, 0.0); PAID += np.where(closed, 900.0, 0.0)
            elif k in ('fn', 'l150', 'fn150'): closed = fa & (nj >= 5)
            else: closed = np.zeros(P, bool)
            reset = passed | bust | closed
            p = np.where(passed, 1, np.where(ev & bust & (k == 'fn'), 4, np.where(bust | closed, 3, p)))
            for arr_, val in ((b, bj), (h, hj), (bd, bdj), (q, qj), (c0, c0j), (n, nj), (g, gj)):
                arr_[j] = np.where(reset, 0.0, val)
            ph[j] = p
        if d in snaps: out[d] = (cash - bank, FEES.copy(), PAID.copy(), NEV.copy())
    return out
