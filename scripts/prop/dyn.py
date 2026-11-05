"""State-dependent ("dynamic bold play") prop strategy under INTRADAY breach.

Each day, one trade at the 10:00 bar close in the day's direction (10:00 close vs 09:30 open). The stop and target are
set in DOLLARS from the account's state, then converted to points for the chosen size:
  stop  $ = beta * (cushion above the floor) - margin     (so a stop-out can never touch the floor)
  target$ = min(distance still needed, cap)               (cap keeps days small enough for consistency rules)
Exit at the target, the stop, or the last bar. Separate policies for: evaluation, funded before the floor locks,
funded after the floor locks (collect qualifying days and payouts).
prep(path) -> per-day first-hit tables so any stop/target can be evaluated exactly on real or synthetic bars."""
import numpy as np, pandas as pd, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prop_sim import floorf, FEE
TICK, NL, BIG, W = 0.25, 241, 10 ** 6, 400

def prep(path):
    df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['date'] = t.dt.date; df['m'] = t.dt.hour * 60 + t.dt.minute
    FF, FA, AC, CL = [], [], [], []
    lv = np.arange(NL) * TICK
    for day, g in df.groupby('date', sort=True):
        m, o, h, l, c = (g[k].to_numpy() for k in ('m', 'open', 'high', 'low', 'close'))
        if m[0] != 571 or len(m) < 300: continue
        i = np.searchsorted(m, 600); s = np.sign(c[i] - o[0])
        if s == 0: continue
        e = c[i]; hh, ll = h[i + 1:], l[i + 1:]
        fav = np.maximum.accumulate((hh - e) if s > 0 else (e - ll)); adv = np.maximum.accumulate((e - ll) if s > 0 else (hh - e))
        K = len(fav); ff = np.searchsorted(fav, lv, 'left'); fa = np.searchsorted(adv, lv, 'left')
        FF.append(np.where(ff >= K, BIG, ff)); FA.append(np.where(fa >= K, BIG, fa))
        a = np.full(W, adv[-1]); a[:K] = adv[:W]; AC.append(a); CL.append(s * (c[-1] - e))
    return dict(FF=np.array(FF, np.int32), FA=np.array(FA, np.int32), AC=np.array(AC, np.float32), CL=np.array(CL))

def trade(T, d, S_pts, T_pts):
    """Vectorised one-trade outcome for day indices d with stop/target in points. Returns (points, worst point)."""
    iS = np.clip(np.floor(S_pts / TICK + 1e-9).astype(int), 1, NL - 1); iT = np.ceil(T_pts / TICK - 1e-9).astype(int)
    far = iT >= NL; iT = np.clip(iT, 1, NL - 1)
    kS = T['FA'][d, iS]; kT = np.where(far, BIG, T['FF'][d, iT])
    stop = (kS <= kT) & (kS < BIG); hit = ~stop & (kT < BIG)
    pts = np.where(stop, -iS * TICK, np.where(hit, iT * TICK, T['CL'][d]))
    worst = np.where(stop, -iS * TICK, -np.maximum(T['AC'][d, np.minimum(np.where(hit, kT, W - 1), W - 1)], 0.0))
    return pts, np.minimum(worst, pts)

# ---------------------------------------------------------------- firm rules (same as prop_sim)
RULE = {   # eval target, eval consistency, eval min days, max minis, commission per mini/micro, lock distance (funded)
    'l150': dict(tgt=9000, cons=0.4, mind=0, mx=10, rate=(3.50, 1.00), lockd=4600),
    'fn150': dict(tgt=8000, cons=0.4, mind=3, mx=8, rate=(5.76, 1.74), lockd=4100),
    'mff150': dict(tgt=9000, cons=0.5, mind=2, mx=9, rate=(4.68, 1.74), lockd=1700),
    'ph150': dict(tgt=9000, cons=None, mind=0, mx=17, rate=(4.00, 1.20), lockd=4500),
    'pro': dict(tgt=1250, cons=None, mind=0, mx=2, rate=(3.50, 1.00), lockd=1100),
    'fnpro': dict(tgt=1500, cons=None, mind=0, mx=2, rate=(5.76, 1.74), lockd=1100),
    'mff': dict(tgt=1500, cons=0.3, mind=4, mx=2, rate=(4.68, 1.74), lockd=1100)}
def cost(kind, n, t):
    mini, micro = RULE[kind]['rate']; w = math.floor(n + 1e-9); return mini * w + micro * round((n - w) * 10) + n * t * 12.5

def day_pnl(T, kind, d, n, A, B, t, margin):
    """n contracts, dollar target A (net), dollar stop budget B. Returns ($ day, $ worst intraday)."""
    cd = cost(kind, n, t); S = np.maximum((B - cd - margin) / (50 * n), TICK); Tp = np.maximum((A + cd) / (50 * n), TICK)
    pts, worst = trade(T, d, S, Tp)
    return 50 * n * pts - cd, 50 * n * worst - cd

def eval_run(T, kind, pol, t=1.5, P=4000, D=60, seed=1, margin=None):
    """pol = (n, acap, beta): size, daily target cap (fraction of base target), fraction of cushion risked."""
    R = RULE[kind]; n, acap, beta = pol; margin = cost(kind, n, t) if margin is None else margin
    rng = np.random.default_rng(seed); L = len(T['CL']); Z = np.zeros(P); F0 = np.zeros(P, bool)
    b, h, bd, nd = Z.copy(), Z.copy(), Z.copy(), Z.copy(); live = np.ones(P, bool); ok = np.zeros(P, bool)
    for _ in range(D):
        d = rng.integers(0, L, P); fl = floorf(kind, h, F0, Z)
        tgt = np.maximum(R['tgt'], bd / R['cons']) if R['cons'] else np.full(P, float(R['tgt']))
        A = np.minimum(np.maximum(tgt - b, 50.0), acap * R['tgt']); B = beta * (b - fl)
        c, w = day_pnl(T, kind, d, n, A, B, t, margin)
        brk = live & (b + w <= fl); b = np.where(live, np.where(brk, fl, b + c), b); h = np.where(live, np.maximum(h, b), h)
        bust = live & (brk | (b <= floorf(kind, h, F0, Z))); bd = np.where(live & ~bust, np.maximum(bd, c), bd); nd += live
        tgt = np.maximum(R['tgt'], bd / R['cons']) if R['cons'] else R['tgt']
        ps = live & ~bust & (b >= tgt) & (nd >= R['mind']); ok |= ps; live &= ~(bust | ps)
    return ok.mean(), nd.mean()

def funded_run(T, kind, pol, t=1.5, P=3000, D=300, seed=2, keep=1000.0, margin=None):
    """pol = (n, g, b1, a2, b2): size; pre-lock daily target (fraction of lock distance) and cushion fraction;
    post-lock daily target ($) and cushion fraction. Returns ($ received per funded account, mean funded days)."""
    R = RULE[kind]; n, g, b1, a2, b2 = pol; margin = cost(kind, n, t) if margin is None else margin
    rng = np.random.default_rng(seed); L = len(T['CL']); Z = np.zeros(P); FU = np.ones(P, bool)
    b, h, bd, q, c0, npay, paid, days = (Z.copy() for _ in range(8)); live = np.ones(P, bool)
    for _ in range(D):
        d = rng.integers(0, L, P); fl = floorf(kind, h, FU, npay)
        locked = (npay > 0) if kind == 'mff150' else (fl >= (0.0 if kind == 'ph150' else 100.0))
        A = np.where(locked, a2, g * R['lockd']); B = np.where(locked, b2, b1) * (b - fl)
        c, w = day_pnl(T, kind, d, n, A, B, t, margin)
        brk = live & (b + w <= fl); b = np.where(live, np.where(brk, fl, b + c), b); h = np.where(live, np.maximum(h, b), h)
        bust = live & (brk | (b <= floorf(kind, h, FU, npay))); live &= ~bust; days += live | bust
        bd = np.where(live, np.maximum(bd, c), bd); cyc = b - c0
        if kind == 'l150':
            q += live & (c >= 250); amt = np.minimum(0.5 * b, 3000.0); ok = live & (q >= 5) & (cyc > 0) & (amt >= 500); sp = 0.9
        elif kind == 'fn150':
            q += live & (c >= 250); amt = np.minimum(0.5 * b, 4000.0); ok = live & (q >= 5) & (cyc >= 500) & (amt > 0); sp = 0.95
        elif kind == 'mff150':
            q += live; amt = 0.6 * b; ok = live & (q >= 10) & (amt >= 1000); sp = 0.8
        elif kind == 'ph150':
            q += live; amt = np.minimum(2750.0, b - keep); ok = live & (q >= 10) & (bd <= 0.3 * cyc) & (amt >= 500); sp = 0.8
        elif kind == 'pro':
            amt = np.minimum(b - 1100, np.where(npay == 0, 1000.0, 1500.0)); ok = live & (cyc >= 250) & (bd <= 0.4 * cyc) & (amt >= 500); sp = 0.9
        elif kind == 'fnpro':
            q += live; amt = np.minimum(0.5 * b, 800.0); ok = live & (q >= 3) & (cyc > 0) & (bd <= 0.4 * cyc) & (amt >= 250); sp = 0.9
        else:  # mff 25K
            amt = b - 1100; ok = live & (cyc >= 250) & (amt >= 500); sp = 0.9
        amt = np.where(ok, amt, 0.0); paid += sp * amt; b -= amt; npay += ok
        c0 = np.where(ok, b, c0); q = np.where(ok, 0, q); bd = np.where(ok, 0, bd)
        if kind in ('l150', 'fn150'): live &= npay < 5
    return paid.mean(), days.mean()

# ---------------------------------------------------------------- business simulation (shared bankroll, same drawn day)
def payout(kind, b, c, live, q, bd, cyc, npay, keep=1000.0):
    if kind in ('l150', 'fn150'): q = q + (live & (c >= 250))
    elif kind in ('mff150', 'ph150', 'fnpro'): q = q + live
    if kind == 'l150':   amt = np.minimum(0.5 * b, 3000.0); ok = live & (q >= 5) & (cyc > 0) & (amt >= 500); sp = 0.9
    elif kind == 'fn150': amt = np.minimum(0.5 * b, 4000.0); ok = live & (q >= 5) & (cyc >= 500) & (amt > 0); sp = 0.95
    elif kind == 'mff150': amt = 0.6 * b; ok = live & (q >= 10) & (amt >= 1000); sp = 0.8
    elif kind == 'ph150': amt = np.minimum(2750.0, b - keep); ok = live & (q >= 10) & (bd <= 0.3 * cyc) & (amt >= 500); sp = 0.8
    elif kind == 'pro':  amt = np.minimum(b - 1100, np.where(npay == 0, 1000.0, 1500.0)); ok = live & (cyc >= 250) & (bd <= 0.4 * cyc) & (amt >= 500); sp = 0.9
    elif kind == 'fnpro': amt = np.minimum(0.5 * b, 800.0); ok = live & (q >= 3) & (cyc > 0) & (bd <= 0.4 * cyc) & (amt >= 250); sp = 0.9
    else:                amt = b - 1100; ok = live & (cyc >= 250) & (amt >= 500); sp = 0.9
    return np.where(ok, amt, 0.0), ok, sp, q

def business(T, specs, t=1.5, P=10000, D=252, bank=12000.0, trig=None, seed=3, snaps=(42, 126, 252)):
    """specs: list of (kind, eval policy, funded policy). Returns {day: (net, fees, payouts, evals bought)}."""
    trig = trig or {}; K = len(specs); L = len(T['CL']); rng = np.random.default_rng(seed)
    ph = np.full((K, P), 3, np.int8); b, h, bd, nd, q, c0, npay = (np.zeros((K, P)) for _ in range(7)); on = np.zeros((K, P), bool)
    cash = np.full(P, bank); FEES, PAID, NEV = np.zeros(P), np.zeros(P), np.zeros(P); out = {}; F0, F1 = np.zeros(P, bool), np.ones(P, bool)
    for day in range(1, D + 1):
        d = rng.integers(0, L, P)
        for j, (kind, ep, fp) in enumerate(specs):
            R = RULE[kind]; on[j] |= cash >= trig.get(kind, 0.0); fee = FEE[kind]
            new = (ph[j] == 3) & on[j] & (cash >= fee); cash -= np.where(new, fee, 0); FEES += np.where(new, fee, 0); NEV += new
            ph[j] = np.where(new, 0, ph[j]); ev = ph[j] == 0; fu = ph[j] == 1
            if not (ev | fu).any(): continue
            bj, hj, bdj, npj = b[j], h[j], bd[j], npay[j]
            fle = floorf(kind, hj, F0, npj * 0); flf = floorf(kind, hj, F1, npj)
            tgt = np.maximum(R['tgt'], bdj / R['cons']) if R['cons'] else np.full(P, float(R['tgt']))
            Ae = np.minimum(np.maximum(tgt - bj, 50.0), ep[1] * R['tgt']); Be = ep[2] * (bj - fle)
            locked = (npj > 0) if kind == 'mff150' else (flf >= (0.0 if kind == 'ph150' else 100.0))
            Af = np.where(locked, fp[3], fp[1] * R['lockd']); Bf = np.where(locked, fp[4], fp[2]) * (bj - flf)
            ce, we = day_pnl(T, kind, d, ep[0], Ae, Be, t, cost(kind, ep[0], t)); cf, wf = day_pnl(T, kind, d, fp[0], Af, Bf, t, cost(kind, fp[0], t))
            c = np.where(ev, ce, np.where(fu, cf, 0.0)); w = np.where(ev, we, np.where(fu, wf, 0.0)); fl = np.where(ev, fle, flf)
            act = ev | fu; brk = act & (bj + w <= fl)
            bj = np.where(act, np.where(brk, fl, bj + c), bj); hj = np.where(act, np.maximum(hj, bj), hj)
            bust = act & (brk | (bj <= np.where(ev, floorf(kind, hj, F0, npj * 0), floorf(kind, hj, F1, npj))))
            bdj = np.where(act & ~bust, np.maximum(bdj, c), bdj); ndj = nd[j] + ev
            tg2 = np.maximum(R['tgt'], bdj / R['cons']) if R['cons'] else R['tgt']
            passed = ev & ~bust & (bj >= tg2) & (ndj >= R['mind'])
            live = fu & ~bust
            amt, ok, sp, qj = payout(kind, bj, c, live, q[j], bdj, bj - c0[j], npj)
            cash += sp * amt; PAID += sp * amt; bj = bj - amt; npj = npj + ok
            c0j = np.where(ok, bj, c0[j]); qj = np.where(ok, 0, qj); bdj = np.where(ok, 0, bdj)
            closed = live & (npj >= 5) if kind in ('l150', 'fn150') else np.zeros(P, bool)
            reset = passed | bust | closed
            ph[j] = np.where(passed, 1, np.where(bust | closed, 3, ph[j]))
            for arr, val in ((b, bj), (h, hj), (bd, bdj), (nd, ndj), (q, qj), (c0, c0j), (npay, npj)):
                arr[j] = np.where(reset, 0.0, val)
        if day in snaps: out[day] = (cash - bank, FEES.copy(), PAID.copy(), NEV.copy())
    return out
