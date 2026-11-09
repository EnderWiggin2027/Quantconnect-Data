# SPY 10-delta, $1-wide PUT CREDIT SPREAD - credit statistics
#
# What it does
# ------------
# Every trading day (30 min after the open) it looks at the SPY option chain and, for each target
# days-to-expiration (DTE_TARGETS), it:
#   1. picks the put whose delta is closest to -TARGET_DELTA (the SHORT leg),
#   2. picks the put SPREAD_WIDTH dollars lower (the LONG leg),
#   3. records the credit you would collect for selling that spread.
# Nothing is traded - it only measures. At the end of the backtest it prints the average, median,
# the middle 50% (25th to 75th percentile) and more into the QuantConnect cloud console / Logs tab.
#
# Credit is reported two ways:
#   MID     = mid(short) - mid(long)         (realistic fill if you work the order)
#   NATURAL = short bid  - long ask          (worst-case market-order fill)
# Per-share numbers are in dollars per share; "per contract" = x100.
#
# Runtime note: this subscribes to a lot of SPY option contracts. If the backtest is slow, shorten the
# date range, drop DTE targets, or set OPTION_RESOLUTION to Resolution.HOUR.

#region imports
from AlgorithmImports import *
import numpy as np
from collections import defaultdict
#endregion


class Spy10DeltaPutSpreadStats(QCAlgorithm):

    # ---------------- settings you can change ----------------
    TARGET_DELTA = 0.10                  # absolute delta of the short put
    DELTA_TOLERANCE = 0.03               # skip the day if the closest delta is further than this from target
    SPREAD_WIDTH = 1                     # strike distance between short and long put, in dollars
    DTE_TARGETS = [0, 7, 30]             # days to expiration to study (0 = same-day expiry); add 45 if you like
    MAX_DTE = 40                         # option filter reaches this far out (keep >= largest target + its tolerance)
    MINUTES_AFTER_OPEN = 30              # sample time: 10:00 ET
    OPTION_RESOLUTION = Resolution.MINUTE
    START = (2023, 1, 1)
    END = (2024, 12, 31)
    # ----------------------------------------------------------

    def initialize(self):
        self.set_start_date(*self.START)
        self.set_end_date(*self.END)
        self.set_cash(100000)

        equity = self.add_equity("SPY", Resolution.MINUTE, data_normalization_mode=DataNormalizationMode.RAW)
        self.spy = equity.symbol

        option = self.add_option("SPY", self.OPTION_RESOLUTION)
        option.set_filter(lambda u: u.puts_only().include_weeklys().strikes(-50, 5).expiration(0, self.MAX_DTE))
        self.option_symbol = option.symbol

        # samples[dte_target] -> lists of observations
        self.samples = {t: {"mid": [], "nat": [], "delta": [], "mid_pct": []} for t in self.DTE_TARGETS}
        # by_year[dte_target][year] -> list of mid credits
        self.by_year = {t: defaultdict(list) for t in self.DTE_TARGETS}
        self.attempts = {t: 0 for t in self.DTE_TARGETS}

        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.after_market_open(self.spy, self.MINUTES_AFTER_OPEN),
            self.sample_chain)

    # ------------------------------------------------------------------
    def _dte_tolerance(self, target):
        # 0-DTE must be exactly today's expiry; others allow +-25% (at least 1 day)
        return 0 if target == 0 else max(1, round(0.25 * target))

    def sample_chain(self) -> None:
        slice = self.current_slice
        if slice is None:
            return
        chain = slice.option_chains.get(self.option_symbol)
        if not chain:
            return

        today = self.time.date()
        puts = [c for c in chain if c.right == OptionRight.PUT]
        if not puts:
            return

        for target in self.DTE_TARGETS:
            self.attempts[target] += 1
            tol = self._dte_tolerance(target)

            # choose the expiry whose DTE is closest to the target
            candidates = {c.expiry for c in puts if abs((c.expiry.date() - today).days - target) <= tol}
            if not candidates:
                continue
            expiry = min(candidates, key=lambda e: abs((e.date() - today).days - target))
            leg_pool = {c.strike: c for c in puts if c.expiry == expiry}

            # short leg: closest |delta| to target, with a real two-sided quote and a computed delta
            quoted = [c for c in leg_pool.values()
                      if c.bid_price > 0 and c.ask_price > 0 and c.greeks.delta != 0]
            if not quoted:
                continue
            short = min(quoted, key=lambda c: abs(abs(c.greeks.delta) - self.TARGET_DELTA))
            if abs(abs(short.greeks.delta) - self.TARGET_DELTA) > self.DELTA_TOLERANCE:
                continue

            # long leg: SPREAD_WIDTH below
            long = leg_pool.get(short.strike - self.SPREAD_WIDTH)
            if long is None or long.ask_price <= 0 or long.bid_price < 0:
                continue

            short_mid = (short.bid_price + short.ask_price) / 2
            long_mid = (long.bid_price + long.ask_price) / 2
            credit_mid = short_mid - long_mid
            credit_nat = short.bid_price - long.ask_price

            s = self.samples[target]
            s["mid"].append(credit_mid)
            s["nat"].append(credit_nat)
            s["delta"].append(abs(short.greeks.delta))
            s["mid_pct"].append(100.0 * credit_mid / self.SPREAD_WIDTH)
            self.by_year[target][self.time.year].append(credit_mid)

    # ------------------------------------------------------------------
    @staticmethod
    def _stats_line(name, values, scale=1.0, unit="$", decimals=3):
        a = np.array(values, dtype=float) * scale
        p = np.percentile(a, [5, 10, 25, 50, 75, 90, 95])
        f = lambda x: f"{unit}{x:.{decimals}f}" if unit == "$" else f"{x:.{decimals}f}{unit}"
        return (f"  {name:<22} avg {f(a.mean())} | median {f(p[3])} | "
                f"MIDDLE 50% [{f(p[2])} - {f(p[4])}] | "
                f"p5/p95 [{f(p[0])} - {f(p[6])}] | p10/p90 [{f(p[1])} - {f(p[5])}] | "
                f"min {f(a.min())} max {f(a.max())} | std {f(a.std())}")

    def on_end_of_algorithm(self) -> None:
        w = self.SPREAD_WIDTH
        self.log("=" * 100)
        self.log(f"SPY {int(self.TARGET_DELTA * 100)}-DELTA, ${w}-WIDE PUT CREDIT SPREAD - CREDIT STATS  "
                 f"({self.START[0]}-{self.START[1]:02d}-{self.START[2]:02d} to "
                 f"{self.END[0]}-{self.END[1]:02d}-{self.END[2]:02d}, sampled {self.MINUTES_AFTER_OPEN} min after open)")
        self.log("=" * 100)

        for target in self.DTE_TARGETS:
            s = self.samples[target]
            n = len(s["mid"])
            label = "0 DTE (same day)" if target == 0 else f"~{target} DTE"
            self.log("")
            self.log(f"--- {label}: {n} valid samples out of {self.attempts[target]} trading days ---")
            if n == 0:
                self.log("  no valid samples (no matching expiry / delta / quotes in this period)")
                continue

            self.log(self._stats_line("Credit per share (MID)", s["mid"]))
            self.log(self._stats_line("Credit per contract MID", s["mid"], scale=100, unit="$", decimals=2))
            self.log(self._stats_line("Credit per share (NAT)", s["nat"]))
            self.log(self._stats_line("Credit per contract NAT", s["nat"], scale=100, unit="$", decimals=2))
            self.log(self._stats_line("Credit % of width (MID)", s["mid_pct"], unit="%", decimals=1))
            self.log(f"  Avg short-put |delta| actually used: {np.mean(s['delta']):.3f}   "
                     f"Avg max loss per contract: ${(w - np.mean(s['mid'])) * 100:.2f}   "
                     f"Avg breakeven win-rate needed: {100 * (w - np.mean(s['mid'])) / w:.1f}%")

            self.log("  By year (MID credit per share):  year | n | avg | median | middle 50%")
            for year in sorted(self.by_year[target]):
                v = np.array(self.by_year[target][year])
                q1, med, q3 = np.percentile(v, [25, 50, 75])
                self.log(f"    {year} | {len(v):>4} | ${v.mean():.3f} | ${med:.3f} | [${q1:.3f} - ${q3:.3f}]")

        self.log("")
        self.log("Notes: MID = mid-to-mid fill; NAT = sell short at bid / buy long at ask. "
                 "Middle 50% = 25th to 75th percentile of daily samples.")
