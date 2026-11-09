# SPY 0DTE 10-delta, $1-wide PUT CREDIT SPREAD - eval pass-rate model with INTRADAY drawdown
#
# Question it answers
# -------------------
# Start with a $10,000 account. Pass the eval by reaching +$700 profit; fail if you hit -$300 (3% of $10k).
# Each trade is a 0DTE SPY put credit spread sized to win ~$500. What is the chance to pass when the
# -$300 line is checked INTRADAY on the open position (mark-to-market, every minute), not just at the close?
#
# How it works
# ------------
# 1. Every day, 30 min after the open, it "opens" (measure-only, no orders) the 0DTE put spread whose short
#    put is closest to 10 delta, long put $1 lower. Contracts N are sized so a full win ~ WIN_TARGET dollars
#    (capped so the max loss never exceeds the account).
# 2. Every minute it marks the spread and tracks the worst open P&L (max adverse excursion).
# 3. 1 minute before the close it settles the spread on SPY's price (intrinsic value) -> final P&L.
# 4. At the end it takes those real daily results and runs the eval many times, two ways:
#       - BOOTSTRAP: random days drawn from the sample (iid)
#       - HISTORICAL: start the eval on each real day and walk forward through actual consecutive days
#    under three rule sets:
#       close  = only fail when CLOSED P&L reaches -$300            (your original model)
#       static = fail when closed P&L + open-trade drawdown reaches -$300 from the starting balance, intraday
#       daily  = fail when a single day's open drawdown reaches -$300 (daily loss limit), or closed P&L <= -$300
#    and two pricing scenarios:
#       MID = entry and marks at mid prices        NAT = sell short at bid / buy long at ask, marks at the
#                                                         closing side (short ask - long bid): very conservative
# Pass is checked at the close (cumulative closed P&L >= PROFIT_TARGET).

#region imports
from AlgorithmImports import *
import numpy as np
#endregion


class Spy0DteEvalModel(QCAlgorithm):

    # ---------------- settings you can change ----------------
    ACCOUNT = 10000
    PROFIT_TARGET = 700          # pass level (closed P&L)
    DRAWDOWN_LIMIT = 300         # fail level = 3% of 10k
    WIN_TARGET = 500             # size each trade so a full win is about this many dollars
    TARGET_DELTA = 0.10
    DELTA_TOLERANCE = 0.03
    SPREAD_WIDTH = 1
    MINUTES_AFTER_OPEN = 30      # entry time: 10:00 ET
    MAX_TRADES_PER_EVAL = 60     # give up (count as unresolved) after this many trading days
    BOOTSTRAP_RUNS = 10000
    START = (2022, 6, 1)
    END = (2024, 12, 31)
    # ----------------------------------------------------------

    def initialize(self):
        self.set_start_date(*self.START)
        self.set_end_date(*self.END)
        self.set_cash(self.ACCOUNT)

        equity = self.add_equity("SPY", Resolution.MINUTE, data_normalization_mode=DataNormalizationMode.RAW)
        self.spy = equity.symbol

        option = self.add_option("SPY", Resolution.MINUTE)
        # same-day expiry only, puts only
        option.set_filter(lambda u: u.puts_only().include_weeklys().strikes(-40, 2).expiration(0, 0))
        self.option_symbol = option.symbol

        self.trade = None
        self.days = []   # one dict per completed trade-day (dollar results)

        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.after_market_open(self.spy, self.MINUTES_AFTER_OPEN),
            self.open_trade)
        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.before_market_close(self.spy, 1),
            self.close_trade)

    # ------------------------------------------------------------------
    def open_trade(self) -> None:
        self.trade = None
        slice = self.current_slice
        if slice is None:
            return
        chain = slice.option_chains.get(self.option_symbol)
        if not chain:
            return
        today = self.time.date()
        puts = {c.strike: c for c in chain
                if c.right == OptionRight.PUT and c.expiry.date() == today}
        quoted = [c for c in puts.values()
                  if c.bid_price > 0 and c.ask_price > 0 and c.greeks.delta != 0]
        if not quoted:
            return

        short = min(quoted, key=lambda c: abs(abs(c.greeks.delta) - self.TARGET_DELTA))
        if abs(abs(short.greeks.delta) - self.TARGET_DELTA) > self.DELTA_TOLERANCE:
            return
        long = puts.get(short.strike - self.SPREAD_WIDTH)
        if long is None or long.ask_price <= 0:
            return

        credit_mid = (short.bid_price + short.ask_price) / 2 - (long.bid_price + long.ask_price) / 2
        credit_nat = short.bid_price - long.ask_price
        if credit_mid < 0.01:
            return

        # size: ~WIN_TARGET dollars if the spread expires worthless, but max loss must fit in the account
        n = max(1, round(self.WIN_TARGET / (credit_mid * 100)))
        n_cap = int(self.ACCOUNT / ((self.SPREAD_WIDTH - credit_mid) * 100))
        n = max(1, min(n, n_cap))

        self.trade = {
            "short": short.symbol, "long": long.symbol,
            "ks": float(short.strike), "kl": float(long.strike),
            "credit_mid": credit_mid, "credit_nat": credit_nat, "n": n,
            "delta": abs(short.greeks.delta),
            "min_mid": 0.0, "min_nat": 0.0,       # worst open P&L per share so far
        }

    def on_data(self, slice: Slice) -> None:
        t = self.trade
        if t is None:
            return
        chain = slice.option_chains.get(self.option_symbol)
        if not chain:
            return
        by_symbol = {c.symbol: c for c in chain}
        s = by_symbol.get(t["short"])
        l = by_symbol.get(t["long"])
        if s is None or l is None:
            return
        if (s.bid_price <= 0 and s.ask_price <= 0) or (l.ask_price <= 0 and l.bid_price <= 0):
            return  # no quote this minute

        cost_mid = (s.bid_price + s.ask_price) / 2 - (l.bid_price + l.ask_price) / 2
        cost_nat = s.ask_price - l.bid_price          # cost to close on the unfavourable side
        t["min_mid"] = min(t["min_mid"], t["credit_mid"] - cost_mid)
        t["min_nat"] = min(t["min_nat"], t["credit_nat"] - cost_nat)

    def close_trade(self) -> None:
        t = self.trade
        if t is None:
            return
        self.trade = None
        spot = self.securities[self.spy].price
        if spot <= 0:
            return
        cost_final = max(0.0, t["ks"] - spot) - max(0.0, t["kl"] - spot)   # intrinsic value of the spread
        pnl_mid = t["credit_mid"] - cost_final
        pnl_nat = t["credit_nat"] - cost_final
        mult = t["n"] * 100.0
        self.days.append({
            "n": t["n"], "delta": t["delta"], "kept_full": cost_final == 0.0,
            "pnl_mid": pnl_mid * mult, "min_mid": min(t["min_mid"], pnl_mid) * mult,
            "pnl_nat": pnl_nat * mult, "min_nat": min(t["min_nat"], pnl_nat) * mult,
        })

    # ------------------------------------------------------------------
    def _walk(self, order, pnl, mn, mode):
        """Run one eval over the trades in `order`. 1 = pass, 0 = fail, -1 = unresolved."""
        L, T = self.DRAWDOWN_LIMIT, self.PROFIT_TARGET
        cum = 0.0
        for i in order:
            if mode == "static" and cum + mn[i] <= -L:
                return 0
            if mode == "daily" and (mn[i] <= -L or cum + pnl[i] <= -L):
                return 0
            cum += pnl[i]
            if mode == "close" and cum <= -L:
                return 0
            if cum >= T:
                return 1
        return -1

    def _rates(self, results):
        r = np.array(results)
        resolved = r[r >= 0]
        n_pass, n_fail, n_unres = int((r == 1).sum()), int((r == 0).sum()), int((r == -1).sum())
        rate = 100.0 * n_pass / len(resolved) if len(resolved) else float("nan")
        return rate, n_pass, n_fail, n_unres

    def on_end_of_algorithm(self) -> None:
        d = self.days
        n = len(d)
        self.log("=" * 100)
        self.log(f"SPY 0DTE {int(self.TARGET_DELTA * 100)}-DELTA ${self.SPREAD_WIDTH}-WIDE PUT CREDIT SPREAD - EVAL MODEL "
                 f"(${self.ACCOUNT:,} acct, pass +${self.PROFIT_TARGET}, fail -${self.DRAWDOWN_LIMIT} = "
                 f"{100 * self.DRAWDOWN_LIMIT / self.ACCOUNT:.0f}%)")
        self.log("=" * 100)
        if n < 20:
            self.log(f"Only {n} valid trade-days - not enough data. Widen the date range or check option data/greeks.")
            return

        kept = np.array([x["kept_full"] for x in d])
        contracts = np.array([x["n"] for x in d])
        self.log(f"Trade-days: {n} | contracts/trade: avg {contracts.mean():.0f}, median {np.median(contracts):.0f}, "
                 f"min {contracts.min()}, max {contracts.max()} | avg short |delta| {np.mean([x['delta'] for x in d]):.3f}")
        self.log(f"Win rate (spread expires worthless / kept full credit): {100 * kept.mean():.1f}%")

        for scen in ("mid", "nat"):
            pnl = np.array([x[f"pnl_{scen}"] for x in d])
            mn = np.array([x[f"min_{scen}"] for x in d])
            hit = mn <= -self.DRAWDOWN_LIMIT
            wins = pnl > 0
            self.log("")
            self.log(f"--- Pricing scenario: {scen.upper()} ---")
            self.log(f"  Profitable days: {100 * wins.mean():.1f}% | avg win ${pnl[wins].mean() if wins.any() else 0:,.0f} | "
                     f"avg loss ${pnl[~wins].mean() if (~wins).any() else 0:,.0f} | worst day ${pnl.min():,.0f}")
            self.log(f"  Days the open trade touched -${self.DRAWDOWN_LIMIT} intraday: {100 * hit.mean():.1f}% "
                     f"({int(hit.sum())} of {n})")
            self.log(f"  ...of the days that FINISHED profitable, touched -${self.DRAWDOWN_LIMIT} intraday anyway: "
                     f"{100 * (hit & wins).sum() / max(1, wins.sum()):.1f}% ({int((hit & wins).sum())} days)")
            self.log(f"  Worst intraday open drawdown: ${mn.min():,.0f} | median worst-intraday: ${np.median(mn):,.0f}")

            rng = np.random.default_rng(42)
            self.log(f"  EVAL PASS RATE (pass +${self.PROFIT_TARGET} before -${self.DRAWDOWN_LIMIT}):")
            self.log(f"    {'rule':<8} | {'bootstrap pass%':>15} (pass/fail/unres) | {'historical pass%':>16} (pass/fail/unres)")
            for mode, label in (("close", "close"), ("static", "static"), ("daily", "daily")):
                boot = [self._walk(rng.integers(0, n, size=self.MAX_TRADES_PER_EVAL), pnl, mn, mode)
                        for _ in range(self.BOOTSTRAP_RUNS)]
                hist = [self._walk(range(s, n), pnl, mn, mode) for s in range(n)]
                b = self._rates(boot)
                h = self._rates(hist)
                self.log(f"    {label:<8} | {b[0]:>14.1f}% ({b[1]}/{b[2]}/{b[3]}) | {h[0]:>15.1f}% ({h[1]}/{h[2]}/{h[3]})")

        self.log("")
        self.log("close  = fail only when CLOSED P&L <= -limit (your original model)")
        self.log("static = fail when closed P&L + open-trade drawdown <= -limit, checked every minute")
        self.log("daily  = fail when one day's open drawdown <= -limit (or closed P&L <= -limit)")
        self.log("historical = eval started on every real day, walking real consecutive days (unres = ran out of data)")
        self.log("Settlement uses SPY price 1 min before close (intrinsic value). Measure-only: no orders placed.")
