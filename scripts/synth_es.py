"""
Synthetic ES 1-minute RTH data: Merton jump-diffusion + GARCH volatility clustering + Markov regime shifts.

Model (all in log-price):
  * Daily regime r_t in {calm, normal, crisis}: Markov chain, scales volatility and jump intensity.
  * Daily base variance h_t: GARCH(1,1) on the previous day's standardized diffusive return.
  * Overnight gap: Normal(drift, overnight vol) + rare Merton gap jump (mostly down).
  * Intraday: 390 one-minute bars, each built from SUBSTEPS Brownian sub-steps with
      - a U-shaped time-of-day volatility profile (calibrated to real ES),
      - an AR(1) intraday log-volatility component (short-term clustering),
      - Poisson Merton jumps (Normal size, negative mean), more frequent in the crisis regime.
  * Volume: real ES time-of-day volume profile scaled by the day's volatility.
Prices are rounded to the 0.25 ES tick. Output format matches data/ES_1m_RTH/*.csv.gz.

Usage:  python scripts/synth_es.py --years 10 --seed 1 --out data/synthetic/ES_synth_1m_10y_seed1.csv.gz
"""
import argparse, numpy as np, pandas as pd

PARAMS = dict(
    start_price=5000.0,
    ann_drift=0.07,
    # regimes: calm, normal, crisis
    regime_vol_mult=np.array([0.62, 1.0, 2.5]),
    regime_jump_mult=np.array([0.4, 1.0, 5.0]),
    regime_P=np.array([[0.980, 0.020, 0.000],
                       [0.014, 0.981, 0.005],
                       [0.000, 0.070, 0.930]]),
    # GARCH(1,1) on standardized daily diffusive returns
    garch_a=0.06, garch_b=0.90,
    target_intra_sd=0.0072, target_on_sd=0.0055,      # diffusive parts (jumps add the rest)
    # intraday Merton jumps (per day, normal regime), log size ~ N(mu, sd)
    jump_lam=0.8, jump_mu=-0.0004, jump_sd=0.0022,
    # rare large news spikes (per day, normal regime), symmetric
    spike_lam=0.05, spike_sd=0.0075,
    # overnight Merton gap jumps (prob per night, normal regime)
    gap_p=0.025, gap_mu=-0.006, gap_sd=0.014,
    # intraday AR(1) log-vol noise (per minute)
    iv_phi=0.985, iv_sd=0.45,
    # microstructure noise (bid/ask bounce) on observed prices, log units (~1 tick)
    micro_sd=0.00014,
    substeps=6,
)

# real ES (2022-2026) time-of-day profiles: relative minute volatility and mean volume, 390 values each
def load_profiles(path):
    df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['m'] = t.dt.hour * 60 + t.dt.minute; df['date'] = t.dt.date
    full = df.groupby('date').filter(lambda g: len(g) == 390 and g.m.iloc[0] == 571)
    lr = np.log(full.close).diff().to_numpy().copy(); first = (full.m == 571).to_numpy()
    lr[first] = np.log(full.close / full.open).to_numpy()[first]
    mi = (full.m - 571).to_numpy()
    prof = pd.Series(lr ** 2).groupby(mi).mean().to_numpy() ** 0.5
    prof = prof / np.sqrt((prof ** 2).mean())
    vprof = full.groupby(mi).volume.mean().to_numpy()
    return prof, vprof

def generate(years=10, seed=1, real_path='data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz', start='2027-01-04', p=PARAMS):
    rng = np.random.default_rng(seed)
    prof, vprof = load_profiles(real_path)
    ndays = int(round(252 * years)); M = 390; S = p['substeps']
    # regime chain
    reg = np.empty(ndays, int); reg[0] = 1
    for t in range(1, ndays):
        reg[t] = rng.choice(3, p=p['regime_P'][reg[t - 1]])
    vm = p['regime_vol_mult']; jm = p['regime_jump_mult']
    # stationary E[m^2] so the long-run variance hits the target
    w_, v_ = np.linalg.eig(p['regime_P'].T); pi = np.real(v_[:, np.argmin(np.abs(w_ - 1))]); pi /= pi.sum()
    em2 = (pi * vm ** 2).sum()
    a, b = p['garch_a'], p['garch_b']; w = (1 - a - b)          # unconditional base variance = 1
    h = 1.0; eps_prev = 0.0
    mu_min = p['ann_drift'] / 252 / (M + 1)                       # drift share per minute (overnight counts as 1)
    rows_t, O, H, L, C, V = [], [], [], [], [], []
    logp = np.log(p['start_price'])
    days = pd.bdate_range(start, periods=ndays)
    base_t = np.arange(M) + 571                                   # bar END minute 09:31..16:00
    x = 0.0
    for t in range(ndays):
        h = w + a * eps_prev ** 2 + b * h
        scale = np.sqrt(h / em2) * vm[reg[t]]
        # ---- overnight gap
        # Merton compensator: add back the expected jump drift so long-run drift = ann_drift
        comp_on = -min(1.0, p['gap_p'] * jm[reg[t]]) * (p['gap_mu'] + 0.5 * p['gap_sd'] ** 2)
        comp_in = -jm[reg[t]] * (p['jump_lam'] * (p['jump_mu'] + 0.5 * p['jump_sd'] ** 2) + p['spike_lam'] * 0.5 * p['spike_sd'] ** 2) / M
        on = mu_min + comp_on + p['target_on_sd'] * scale * rng.standard_normal()
        if t > 0 and rng.random() < min(1.0, p['gap_p'] * jm[reg[t]]):
            on += rng.normal(p['gap_mu'], p['gap_sd'])
        if t > 0: logp += on
        # ---- intraday
        sig_min = p['target_intra_sd'] * scale / np.sqrt(M) * prof            # per-minute diffusive sd
        noise = np.empty(M)
        for i in range(M):
            x = p['iv_phi'] * x + np.sqrt(1 - p['iv_phi'] ** 2) * p['iv_sd'] * rng.standard_normal(); noise[i] = x
        sig_min = sig_min * np.exp(noise - p['iv_sd'] ** 2)                       # E[exp(2x - 2var)] = 1
        z = rng.standard_normal((M, S)) * (sig_min / np.sqrt(S))[:, None] + (mu_min + comp_in) / S
        lam = p['jump_lam'] * jm[reg[t]] / M * (prof ** 2)                        # jumps more likely at volatile times
        nj = rng.poisson(lam)
        for i in np.flatnonzero(nj):
            z[i, rng.integers(S)] += rng.normal(p['jump_mu'], p['jump_sd'], nj[i]).sum()
        ns = rng.poisson(p['spike_lam'] * jm[reg[t]] / M * (prof ** 2))
        for i in np.flatnonzero(ns):
            z[i, rng.integers(S)] += rng.normal(0.0, p['spike_sd'], ns[i]).sum()
        path = logp + np.cumsum(z.ravel()).reshape(M, S)
        obs = path + rng.normal(0, p['micro_sd'], path.shape)          # observed prices incl. bid/ask bounce
        opens = np.concatenate(([logp], path[:-1, -1]))
        hi = np.maximum(obs.max(1), opens); lo = np.minimum(obs.min(1), opens); cl = obs[:, -1]
        day_ret = path[-1, -1] - logp
        eps_prev = (day_ret + (on if t > 0 else 0.0)) / (np.sqrt(p['target_intra_sd'] ** 2 + p['target_on_sd'] ** 2) * vm[reg[t]])
        logp = path[-1, -1]
        q = lambda arr: np.round(np.exp(arr) * 4) / 4
        o_, h_, l_, c_ = q(opens), q(hi), q(lo), q(cl)
        h_ = np.maximum.reduce([h_, o_, c_]); l_ = np.minimum.reduce([l_, o_, c_])
        dayvol = (scale) ** 0.8 * rng.lognormal(0, 0.2)
        V.append(np.maximum(0, np.round(vprof * dayvol * rng.lognormal(-0.06, 0.35, M))))
        O.append(o_); H.append(h_); L.append(l_); C.append(c_)
        rows_t.append(pd.DatetimeIndex([days[t] + pd.Timedelta(minutes=int(mm)) for mm in base_t]))
    idx = pd.DatetimeIndex(np.concatenate([r.values for r in rows_t])).tz_localize('America/New_York')
    out = pd.DataFrame({'time': idx.strftime('%Y-%m-%d %H:%M:%S%z').str.replace(r'(\d{2})(\d{2})$', r'\1:\2', regex=True),
                        'open': np.concatenate(O), 'high': np.concatenate(H), 'low': np.concatenate(L),
                        'close': np.concatenate(C), 'volume': np.concatenate(V)})
    return out, reg, days

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', type=float, default=10); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--out', default='data/synthetic/ES_synth_1m_10y_seed1.csv.gz')
    a = ap.parse_args()
    df, reg, days = generate(a.years, a.seed)
    df.to_csv(a.out, index=False)
    pd.DataFrame({'date': days.date, 'regime': np.array(['calm', 'normal', 'crisis'])[reg]}).to_csv(a.out.replace('.csv.gz', '_regimes.csv'), index=False)
    print(f"wrote {len(df):,} bars, {len(days)} days -> {a.out}")
