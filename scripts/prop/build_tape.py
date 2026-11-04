"""Build the daily trade tape for all 10 presets from 1-minute RTH bars (09:31-16:00 ET, bar END timestamps).
Output columns per preset: <name>_pts (points per 1 contract, before costs), <name>_n (trades), <name>_tr (worst intraday point, incl. open trade).
Usage: python scripts/prop/build_tape.py data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz data/tapes/ES_tape_2022-2026.csv"""
import numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presets import PRESETS, NAMES
def run_file(path):
    df = pd.read_csv(path); t = pd.to_datetime(df.time.str[:19]); df['date'] = t.dt.date; df['m'] = t.dt.hour * 60 + t.dt.minute
    rows = []
    for day, g in df.groupby('date', sort=True):
        m, o, h, l, c = (g[k].to_numpy() for k in ('m', 'open', 'high', 'low', 'close'))
        if m[0] != 571: continue
        close_m = m[-1]; day_open = o[0]; d = None
        st = {n: dict(pos=False, e=0.0, pts=0.0, n=0, done=False, tr=0.0) for n in NAMES}
        for i in range(len(m)):
            tt = m[i]; mtc = close_m - tt
            if d is None and tt >= 600:
                diff = c[i] - day_open; d = 1 if diff > 0 else (-1 if diff < 0 else 0)
            if not d: continue
            closing = tt >= 959 or mtc <= 2
            for nm, (start, S, T, cap) in PRESETS.items():
                s = st[nm]
                if s['done']: continue
                if s['pos']:
                    e = s['e']; sp, tp = e - d * S, e + d * T; x = None
                    adv = l[i] if d > 0 else h[i]
                    s['tr'] = min(s['tr'], s['pts'] + max(d * (adv - e), d * (min(o[i], sp) - e) if d > 0 else d * (max(o[i], sp) - e), -S) if True else 0)
                    if d > 0:
                        if o[i] <= sp: x = o[i]
                        elif o[i] >= tp: x = o[i]
                        elif l[i] <= sp: x = sp
                        elif h[i] >= tp: x = tp
                    else:
                        if o[i] >= sp: x = o[i]
                        elif o[i] <= tp: x = o[i]
                        elif h[i] >= sp: x = sp
                        elif l[i] <= tp: x = tp
                    if x is None and closing: x = c[i]
                    if x is not None:
                        s['pts'] += d * (x - e); s['n'] += 1; s['pos'] = False; s['tr'] = min(s['tr'], s['pts'])
                        if s['pts'] >= cap or s['n'] >= 8 or closing: s['done'] = True
                    continue
                if closing: s['done'] = True; continue
                if start <= tt <= 930 and mtc > 30: s['pos'] = True; s['e'] = c[i]
        if d:
            rows.append([pd.Timestamp(day), d] + [v for nm in NAMES for v in (st[nm]['pts'], st[nm]['n'], st[nm]['tr'])])
    return pd.DataFrame(rows, columns=['date', 'dir'] + [f"{n}_{k}" for n in NAMES for k in ('pts', 'n', 'tr')])
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    T = run_file(src); T.to_csv(dst, index=False); print(f'{len(T)} trading days -> {dst}')
