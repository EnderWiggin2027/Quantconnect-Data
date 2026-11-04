"""Builds docs/prop_firm_strategy.pdf. Run: python docs/make_prop_pdf.py"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, KeepTogether

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prop_firm_strategy.pdf')
ss = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=ss['Heading1'], fontSize=16, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor('#1f3a5f'))
H2 = ParagraphStyle('H2', parent=ss['Heading2'], fontSize=12.5, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#1f3a5f'))
B = ParagraphStyle('B', parent=ss['BodyText'], fontSize=9.5, leading=13, spaceAfter=5)
BL = ParagraphStyle('BL', parent=B, leftIndent=12, bulletIndent=2, spaceAfter=2)
SM = ParagraphStyle('SM', parent=B, fontSize=8, leading=10, spaceAfter=0)
SMB = ParagraphStyle('SMB', parent=SM, fontName='Helvetica-Bold')
CODE = ParagraphStyle('CODE', parent=ss['Code'], fontSize=7.6, leading=9.4, backColor=colors.HexColor('#f4f4f4'), borderPadding=5, leftIndent=4)
NOTE = ParagraphStyle('NOTE', parent=B, backColor=colors.HexColor('#fff6e0'), borderPadding=6, borderColor=colors.HexColor('#e0b040'), borderWidth=0.5, spaceBefore=4, spaceAfter=8)

def p(t, st=B): return Paragraph(t, st)
def bullets(items): return [Paragraph(i, BL, bulletText='-') for i in items]
def table(rows, widths, head=1, hl=None):
    data = [[Paragraph(str(c), SMB if r < head else SM) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=head)
    st = [('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b8c2cc')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('BACKGROUND', (0, 0), (-1, head - 1), colors.HexColor('#dfe8f2')), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
    for r in (hl or []): st.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#e6f4e6')))
    t.setStyle(TableStyle(st)); return t
def footer(c, d):
    c.saveState(); c.setFont('Helvetica', 7.5); c.setFillColor(colors.grey)
    c.drawString(0.7 * inch, 0.45 * inch, 'Prop-firm loop strategy - research notes (model results, not a forecast)')
    c.drawRightString(7.8 * inch, 0.45 * inch, f'page {d.page}'); c.restoreState()

S = []
# ---------------------------------------------------------------- title / summary
S += [p('Prop-Firm "Loop" Strategy: Rules, Method, Results and Replication Guide', ParagraphStyle('T', parent=H1, fontSize=19, leading=23)),
      p('Research notes compiled November 2026. Repository: <b>EnderWiggin2027/Quantconnect-Data</b>, branch <b>claude/festive-dirac-jgT5l</b>. '
        'Everything here is a <b>simulation</b> of futures prop-firm accounts; numbers are model outputs, not guarantees.'),
      p('1. Bottom line', H1),
      *bullets([
        'The trading strategy (an intraday ES "momentum loop") has <b>no edge of its own</b>: on real ES 2022-2026 its gross result is about 0 points per trade, '
        'and a normal-account QuantConnect backtest lost money after costs. <b>All modeled profit comes from the prop-firm payoff structure</b>: '
        'losses are capped at the evaluation fee, while payouts are real cash.',
        'The strategy is shaped for that structure: many small winning days, occasional larger losing days, fast passes, and payouts taken before accounts bust.',
        '<b>Best accounts found</b> (all 25K, end-of-day drawdown, no daily loss limit): Lucid 25K Pro (loss limit OFF), FundedNext 25K Pro, MyFundedFutures 25K.',
        '<b>Recommended plan at ~1 tick slippage</b> (real ES, $12,000 start): 5 x Lucid 25K Pro + 5 x FundedNext 25K Pro from day 1, add 5 x MyFundedFutures 25K '
        'when cash reaches $30,000. Median result +$16.8k at 2 months (6.3% chance of being down), +$78k at 6 months, +$176k at 12 months.',
        '<b>At 2-3 ticks slippage</b>: start with Lucid 25K Pro only, add FundedNext 25K Pro and MFF at $30,000 cash. Median +$6.9k / +$29k / +$94k at 2 / 6 / 12 months.',
        'Spreading accounts across <b>uncorrelated markets</b> (crude, gold, copper, nat gas, ES...) sharply cuts early risk in synthetic tests; this still needs real multi-market data.',
        'Biggest real-world unknowns: <b>your actual slippage</b>, the exact firm rules marked "assumed" below, and whether firms change their rules.'])]
S += [p('2. Core idea (why this can make money with a zero-edge strategy)', H1),
      p('A prop evaluation is a <b>convex payoff</b>: if you fail you lose only the fee (here $85-$100); if you pass, the funded account can pay out thousands. '
        'With a random-walk strategy the chance of passing depends mostly on the <b>shape</b> of the daily P&amp;L (win size vs loss size vs drawdown vs target), '
        'not on prediction skill. In tests, a <b>random-direction</b> version of the loop passed evaluations as often as the momentum version; '
        'the momentum signal mattered only in the funded phase (it roughly doubled payouts). The model treats firms as a repeated business: '
        'buy evaluations, pass some, extract payouts before funded accounts bust, recycle the slot.')]
# ---------------------------------------------------------------- strategy rules
S += [PageBreak(), p('3. The strategy - exact mechanical rules', H1),
      p('<b>Instrument:</b> ES / MES futures (1 ES point = $50 per mini, $5 per micro). Regular session 09:30-16:00 ET. All times below are 1-minute bar <b>end</b> times, ET.'),
      p('3.1 Daily direction (shared by every account - no hedging)', H2),
      *bullets(['At 10:00 ET compare the price at 10:00 (close of the 10:00 bar) with the 09:30 opening price (open of the first bar).',
                'Above the open: every account may only go <b>long</b> today. Below: every account may only go <b>short</b>. Equal: no trading today.',
                'Because all accounts trade the same direction, no account is ever opposite another (firms prohibit hedging across accounts).']),
      p('3.2 The loop (per account)', H2),
      *bullets(['From the account\'s start time, enter at market (bar close) in the day\'s direction with a stop S points away and a target T points away.',
                'When the trade exits (stop or target), re-enter on the next bar in the same direction with the same S and T.',
                'Stop for the day when the day\'s closed result reaches <b>+cap points</b> (per contract, gross) or after <b>8 trades</b>.',
                'No new entries after 15:30 ET or within 30 minutes of an early close. Flatten everything at 15:59 (or 2 minutes before an early close).',
                'Simulation fill rules: entry at the signal bar close; exits checked from the next bar; if a bar touches both stop and target, the stop is assumed hit first; '
                'if a bar opens beyond the stop or target, the fill is at the bar open.']),
      p('3.3 Presets ("Portfolio B" slots)', H2),
      table([['Slot', 'Evaluation preset: start / stop / target / daily cap', 'Funded preset: start / stop / target / daily cap'],
             ['1', '10:00 / 8 / 8 / +6 pts', '10:00 / 12 / 8 / +6 pts'],
             ['2', '11:00 / 8 / 8 / +6 pts', '11:00 / 12 / 8 / +6 pts'],
             ['3', '10:00 / 12 / 12 / +10 pts', '10:00 / 8 / 8 / +6 pts'],
             ['4', '11:00 / 12 / 12 / +6 pts', '10:00 / 12 / 12 / +6 pts'],
             ['5', '13:00 / 8 / 8 / +6 pts', '10:00 / 8 / 20 / +6 pts']], [0.5, 3.1, 3.1]),
      p('Each firm runs 5 accounts = slots 1-5. An account uses its slot\'s evaluation preset until it passes, then its slot\'s funded preset.', SM),
      p('3.4 Position sizes', H2),
      table([['Account type', 'Evaluation size (minis) slots 1-5', 'Funded size (minis) slots 1-5', 'After first payout'],
             ['25K accounts, 2-mini cap (Lucid 25K Pro, FundedNext 25K Pro, MFF 25K)', '2 / 2 / 1.5 / 1.5 / 2  (= 20/20/15/15/20 micros)', '1.8 / 1.8 / 2 / 1.8 / 2', 'Halve the funded size'],
             ['Lucid 50K Flex (comparison only)', '3.5 / 3.5 / 2.5 / 2.5 / 3.5', '3 / 3 / 4 / 3 / 4', 'Halve'],
             ['FundedNext 50K Flex (alternative)', '3 / 3 / 2.1 / 2.1 / 3', '2.6 / 2.6 / 3 / 2.6 / 3', 'Halve']], [2.5, 1.7, 1.4, 1.1]),
      p('25K sizes are Portfolio B x 0.6 (the most the 2-mini cap allows); they were chosen on synthetic data and validated on real ES. '
        '<b>Halving size after an account\'s first payout</b> was the one optimisation that improved both profit (+10-13%) and risk.', SM),
      p('3.5 Account management', H2),
      *bullets(['Keep 5 accounts per firm running. When an evaluation busts, buy a new one the next day; when a funded account busts or closes, buy a new evaluation.',
                'Request every payout as soon as the firm\'s rules allow. Payouts go back into the shared bankroll and pay for new evaluations.',
                'Add the next firm only when total cash (start + payouts - fees) reaches the trigger (e.g. $30,000).',
                'Never let accounts hold opposite positions; skip tier-1 news on MFF funded accounts (rule).'])]
# ---------------------------------------------------------------- firm rules
S += [PageBreak(), p('4. Prop-firm rules as modeled', H1),
      p('"(A)" marks an <b>assumption</b> where the screenshots did not state the rule. Re-check every rule against the firm\'s current terms before trading; '
        'if a rule differs, change it in scripts/prop/prop_sim.py and rerun.', NOTE),
      table([['Rule', 'Lucid 25K Pro', 'FundedNext 25K Pro', 'MyFundedFutures 25K'],
             ['Price', '$100 incl. tax (daily loss limit OFF)', '$85 (reset $84.99)', '$98 incl. tax'],
             ['Eval target / drawdown', '$1,250 / $1,000 EOD trailing', '$1,500 / $1,000 EOD', '$1,500 / $1,000 EOD'],
             ['Eval daily loss limit', 'Optional $600 (pauses). Use OFF.', 'None', 'None'],
             ['Eval consistency', 'None', 'None', '30%: target = max($1,500, best day / 0.3) (A: target bump, not fail)'],
             ['Min eval days', '-', '-', '4 trading days'],
             ['Max size', '2 minis / 20 micros', '2 minis / 20 micros', '2 minis / 20 micros'],
             ['Funded drawdown', '$1,000 EOD, locks at +$100 once up $1,100 (A)', '$1,000 EOD, locks at +$100 (A)', '$1,000 EOD, locks at +$100'],
             ['Payout conditions', '>= $250 profit since last payout; best day <= 40% of cycle profit; $1,100 buffer not withdrawable; any day (A)',
              'Every 3 trading days (A); best day <= 40% of cycle profit; cycle profit > 0', 'Daily; >= $250 net since last payout; $1,100 buffer'],
             ['Payout amount', 'profit - $1,100, cap $1,000 (1st), $1,500 (later); min $500', '50% of profit (A), cap $800, min $250 (A)', 'profit - $1,100, no cap (A), min $500'],
             ['Split', '90%', '90%', '90%'],
             ['Account limit', '5 Lucid accounts total (Pro + Flex combined)', '5 (A)', '5 (A)'],
             ['Other', 'Flat by 4:45pm; no hedging; micro-scalp rule', 'Max withdrawal $800', 'No tier-1 news trading when funded']], [1.35, 1.85, 1.75, 1.75]),
      Spacer(1, 6),
      p('4.1 Accounts tested and rejected (or weaker)', H2),
      table([['Account', 'Key rules modeled', 'Result (real ES, 5 accounts, $12k, 1 tick)'],
             ['Lucid 50K Flex ($150)', '$3,000 target, $2,000 EOD, 50% consistency read as $1,500/day cap; payouts 5 days of $150+, from $1,000 profit, 50% capped $2,000; '
              'floor +$100 after 1st payout; $8k live review ($900 cashout)', 'Works: 12-mo median about +$84-94k but 2-mo loss chance about 18% (vs 5% for 25K Pro)'],
             ['Lucid 25K Pro, loss limit ON ($84)', '$600 daily loss limit pauses trading; on-demand payouts', 'Loses: 12-mo median +$7.7k, 24% chance of loss. The limit stops the loop\'s recovery trades.'],
             ['Lucid 150K Flex ($250-450, A)', '$9,000 target, $4,500 EOD, 40% consistency ($3,600/day), 10 minis', 'Worse than 50K: harder target/drawdown ratio; high loss risk unless fee about $250 and bankroll $24k'],
             ['Apex 50K EOD (fee A $150)', '$1,000 daily loss limit; payout needs $2,600+ (safety net), 50% consistency, $200 days, 6-payout cap', 'Loses at every size tested; positive only with deep fee discounts'],
             ['FundedNext 50K Flex ($140, reset $85)', '$2,500 target, $1,500 EOD, 40% rule bumps target; payouts 5 days $200+, 50% cap $1,500, 5-payout cap, 95% split',
              'Works (12-mo about +$55k alone); weaker than FN 25K Pro as a partner when started on day 1'],
             ['Tradeify 25K v1 ($59)', 'Always-on $600 loss limit, 1 mini, 35% funded consistency', 'Loses'],
             ['Tradeify 25K v2 ($76)', 'No eval loss limit, 1 mini; Daily path ($600 cap, $500 limit)', 'Weak (+$17k/yr alone). Adds about +$11k/yr as a 4th firm - excluded by choice']], [1.5, 3.0, 2.2])]
# ---------------------------------------------------------------- methodology
S += [PageBreak(), p('5. Method (how the numbers were produced)', H1),
      p('5.1 Data', H2),
      *bullets(['<b>Real ES:</b> data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz - continuous front-month ES (open-interest roll, raw prices on the 0.25 grid), '
                '1-minute bars 09:31-16:00 ET (bar end time), Jan 2022 - Nov 2026, 1,249 days. Downloaded from QuantConnect with ES_download.ipynb.',
                '<b>Synthetic ES:</b> scripts/synth_es.py - Merton jump-diffusion + GARCH(1,1) volatility clustering + 3-state Markov regimes (calm/normal/crisis), '
                'U-shaped intraday volatility and volume taken from real ES, bid/ask bounce, 0.25 tick rounding. Calibrated to real ES daily volatility (1.07%), overnight gaps, '
                'clustering and drift. Each seed is an independent 10-year market; used for (a) choosing sizes without touching real data and (b) multi-market tests.',
                'Earlier phases used SPY 1-minute data x10 as an ES proxy (SPY_1m_Cleaned Parquet.parquet); real-ES results later matched those closely.']),
      p('5.2 Trade tape', H2),
      p('scripts/prop/build_tape.py simulates all 10 presets bar-by-bar for every day and records, per preset and day: points per 1 contract before costs, '
        'number of trades, and the worst intraday point (needed for daily-loss-limit rules). The QuantConnect version of the same logic (LoopTape algorithm) matched this '
        'tape exactly on 19 of 25 sampled days and within a few ticks on the rest.'),
      p('5.3 Costs', H2),
      p('Per contract per trade: $3.50 commission round trip (E-mini) + slippage of 1 or 3 ticks x $12.50. Day $ = size x (50 x points - trades x cost). '
        'Costs scale with contract count (micros modeled as fractional minis).'),
      p('5.4 Monte Carlo of the prop business', H2),
      *bullets(['Each simulated path draws trading days at random (with replacement) from the tape; <b>all accounts in a path trade the same drawn day</b>, so correlation between accounts is preserved.',
                '10,000 paths, horizons 1, 2, 6, 12 months (21/42/126/252 trading days), shared cash bankroll starting at $12,000.',
                'Every rule in section 4 is applied each day: fees and resets, end-of-day trailing drawdown and locks, targets, consistency rules, minimum days, payout conditions, '
                'caps, buffers, splits, payout-count limits, live-review closures, and firm start triggers.',
                'Reported: <b>median</b>, <b>5th percentile</b> (bad 1-in-20 outcome) and <b>chance of a net loss</b> of cash at each horizon.']),
      p('5.5 Avoiding overfitting', H2),
      *bullets(['Strategy shapes were first selected on SPY 2018-2022 and checked on 2023-2025; sizes for each new firm were selected on <b>synthetic</b> data and only then run on real ES.',
                'Several searches (1,500 random portfolios; filters; entry/exit models) were checked out of sample and rejected when the improvement did not hold.',
                'Remaining weaknesses: real ES 2022-2026 is a single, mostly rising period; synthetic data has thinner tails than real data; firm rules are partly assumed.'])]
# ---------------------------------------------------------------- results
S += [PageBreak(), p('6. Results', H1),
      p('6.1 Final plans, real ES 2022-2026 (cells: median / 5th percentile / chance of loss)', H2),
      table([['Slippage', 'Plan', '1 month', '2 months', '6 months', '12 months'],
             ['1 tick', 'A: Lucid Pro + FN Pro day 1, add MFF at $30k', '+5,915 / -4,685 / 21.9%', '+16,836 / -1,099 / 6.3%', '+77,978 / +25,468 / 0.2%', '+175,875 / +97,882 / 0.2%'],
             ['1 tick', 'B: Lucid Pro day 1, add FN Pro + MFF at $30k', '+3,736 / -2,429 / 20.0%', '+10,868 / -29 / 5.1%', '+59,296 / +15,221 / 0.1%', '+157,475 / +80,815 / 0.0%'],
             ['1 tick', 'C: all three from day 1', '+7,594 / -7,436 / 25.3%', '+24,288 / -3,593 / 8.4%', '+89,425 / +29,819 / 1.8%', '+186,956 / +100,499 / 1.7%'],
             ['3 ticks', 'A', '+2,934 / -5,925 / 33.6%', '+10,607 / -5,117 / 15.3%', '+46,561 / +7,737 / 2.1%', '+110,847 / +40,672 / 1.2%'],
             ['3 ticks', 'B', '+2,058 / -3,100 / 30.1%', '+6,875 / -2,296 / 12.4%', '+28,926 / +7,263 / 0.8%', '+93,843 / +29,498 / 0.1%'],
             ['3 ticks', 'C', '+3,052 / -9,154 / 37.8%', '+13,841 / -10,257 / 19.1%', '+55,948 / -11,930 / 6.6%', '+119,364 / -11,932 / 5.9%']],
            [0.55, 2.0, 1.05, 1.05, 1.05, 1.1], hl=[1, 5]),
      p('Highlighted rows = recommended plan for that slippage level. Reproduce with: python scripts/prop/run_final_plan.py', SM),
      p('6.2 Single firms, real ES (5 accounts, $12k start)', H2),
      table([['Account (fee)', '1 tick: 2 mo', '1 tick: 6 mo', '1 tick: 12 mo', '3 ticks: 2 mo', '3 ticks: 12 mo'],
             ['Lucid 25K Pro ($100)', '+10,872 / 5.1%', '+39,065 / 0.0%', '+81,462 / 0.0%', '+6,875 / 12.4%', '+55,631 / 0.0%'],
             ['FundedNext 25K Pro ($85)', '+6,555 / 8.6%', '+23,050 / 0.2%', '+47,262 / 0.0%', '+3,715 / 20.2%', '+31,992 / 0.3%'],
             ['MyFundedFutures 25K ($98)', '+6,818 / 15.4%', '+27,383 / 1.2%', '+58,552 / 0.1%', '+3,115 / 30.0%', '+33,110 / 1.6%'],
             ['Lucid 50K Flex ($150)', '+10,132 / 17.9%', '+43,986 / 1.6%', '+93,582 / 0.6%', '+4,775 / 31.1%', '+57,137 / 4.0%']],
            [1.8, 1.0, 1.0, 1.05, 1.0, 1.0]),
      p('Cells: median / chance of loss.', SM),
      p('6.3 Spreading accounts across independent markets (synthetic, upper bound; Plan C = all three firms from day 1)', H2),
      table([['Slippage', 'Markets', '1 month', '2 months', '6 months', '12 months'],
             ['1 tick', '1', '+10,916 / -5,356 / 16.2%', '+30,648 / +2,276 / 3.4%', '+107,551 / +52,279 / 0.4%', '+221,970 / +142,448 / 0.4%'],
             ['1 tick', '5', '+9,530 / -2,003 / 9.2%', '+26,291 / +7,537 / 0.9%', '+92,679 / +58,049 / 0.0%', '+191,753 / +141,822 / 0.0%'],
             ['1 tick', '10', '+9,829 / +722 / 3.4%', '+26,799 / +11,718 / 0.1%', '+93,674 / +65,594 / 0.0%', '+193,286 / +152,530 / 0.0%'],
             ['3 ticks', '1', '+5,683 / -7,704 / 28.5%', '+18,671 / -5,209 / 10.8%', '+70,359 / +19,562 / 2.2%', '+147,500 / +72,359 / 2.0%'],
             ['3 ticks', '10', '+5,001 / -2,677 / 15.8%', '+15,933 / +2,979 / 1.8%', '+59,270 / +34,723 / 0.0%', '+124,160 / +88,480 / 0.0%']],
            [0.6, 0.6, 1.3, 1.3, 1.35, 1.4]),
      p('Synthetic markets are perfectly independent, so this overstates the benefit. Lucid lists about 5-6 roughly independent groups (stock indexes, crude, nat gas, '
        'gold/silver, platinum, copper). The loop must be re-scaled to each market\'s volatility and session before use. Reproduce: run_final_plan.py --multimarket', SM),
      p('6.4 What helped and what did not', H2),
      table([['Helped', 'Did not help (tested, rejected)'],
             ['Loop (re-enter after exit, small daily profit cap) instead of one trade per day: about 3x more money',
              'Day filters (VIX, overnight gap, opening-range size), fewer accounts, slower evaluation buying, spending stop-loss'],
             ['Halving funded size after the first payout: +10-13% profit, lower risk',
              'Other entries/exits: pullback, breakout, trailing stop, breakeven stop, time exits; VWAP-fade and gap-fill signals'],
             ['25K accounts with easy target/drawdown ratio (1.25-1.5) and no daily loss limit',
              'Brute-force search of 1,500 structure mixes (did not hold out of sample); martingale; sizing up after profit'],
             ['Adding firms only after cash reaches about $30k (more money, same early risk)',
              'Daily loss limits (any firm): cut the loop\'s recovery trades'],
             ['Different start times / stop-target shapes per account (diversification within ES)', 'Delaying the first payout; changing base sizes away from Portfolio B'],
             ['Independent markets per account (synthetic): early risk cut by 3-10x', 'Same-direction "day-locked" variants could not reach 1-3% risk at 2 months on one market']],
            [3.35, 3.35])]
# ---------------------------------------------------------------- plan + caveats
S += [PageBreak(), p('7. Operating checklist', H1),
      *bullets(['<b>1.</b> Paper-trade the loop on a free simulated account for 2+ weeks; measure real slippage on stop exits (ticks per trade). Choose Plan A (about 1 tick) or Plan B (2-3 ticks).',
                '<b>2.</b> Confirm every "(A)" rule in section 4 with each firm, plus account limits and whether running the same strategy on many accounts is allowed.',
                '<b>3.</b> Start: 5 x Lucid 25K Pro with the daily loss limit OFF (and 5 x FundedNext 25K Pro on day 1 for Plan A). Sizes per section 3.4.',
                '<b>4.</b> Each day: set direction at 10:00 ET; run each account\'s preset; flat by 15:59; no opposite positions anywhere.',
                '<b>5.</b> Request payouts as soon as allowed; halve that account\'s funded size after its first payout; rebuy busted slots the next day.',
                '<b>6.</b> When cash reaches $30,000 add the next firm(s). Track results against the medians in section 6; if live results fall well below the 5th percentile, stop and re-measure costs.',
                '<b>7.</b> Next research step: real CL, GC, SI, HG, NG 1-minute data (multi_market_download.ipynb, split by year) to test cross-market diversification.'])]
S += [p('8. Risks and limitations', H1),
      *bullets(['<b>No edge:</b> profit depends entirely on firm rules. Rule changes, fee changes, payout denials or bans for "farming" behaviour would remove it.',
                '<b>Correlation:</b> 15 accounts on one strategy, one direction, one market lose together on bad days. Multi-market spreading helps only if real correlations are low.',
                '<b>Slippage:</b> 3 ticks roughly halves profit and triples early loss risk versus 1 tick. Stop orders in fast markets can be worse.',
                '<b>Data:</b> real ES covers 2022-2026 only; bootstrap draws days independently (ignores multi-day streaks beyond the data\'s own clustering).',
                '<b>Model simplifications:</b> instant payouts and rebuys; no platform/data fees; fractional mini sizes via micros; payout timing rules partly assumed.',
                '<b>Normal account:</b> the same strategy loses money with real capital (QuantConnect backtest with $100k lost most of it). Never trade it with your own capital.'])]
# ---------------------------------------------------------------- replication
S += [PageBreak(), p('9. Replication guide', H1),
      p('9.1 Files in the repository', H2),
      table([['Path', 'What it is'],
             ['data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz', 'Real ES 1-minute RTH bars (input)'],
             ['data/tapes/ES_tape_2022-2026.csv', 'Daily trade tape for the 10 presets (built from the bars)'],
             ['scripts/prop/presets.py', 'Preset definitions (section 3.3)'],
             ['scripts/prop/build_tape.py', 'Bars -> daily tape (section 5.2)'],
             ['scripts/prop/prop_sim.py', 'Monte Carlo of all firms and rules (section 4/5.4); edit FEE and rule constants here'],
             ['scripts/prop/run_final_plan.py', 'Reproduces tables 6.1 (and 6.3 with --multimarket)'],
             ['scripts/synth_es.py', 'Synthetic ES generator (jump-diffusion + GARCH + regimes)'],
             ['data/synthetic/ES_synth_1m_10y_seed1.csv.gz', 'Example synthetic 10-year market'],
             ['ES_download.ipynb, multi_market_download.ipynb', 'QuantConnect Research notebooks to download 1-minute futures data'],
             ['docs/make_prop_pdf.py', 'Regenerates this PDF']], [3.0, 3.7]),
      p('9.2 Commands', H2),
      Preformatted('git clone https://github.com/EnderWiggin2027/Quantconnect-Data && cd Quantconnect-Data\n'
                   'git checkout claude/festive-dirac-jgT5l\n'
                   'pip install numpy pandas pyarrow reportlab\n'
                   'python scripts/prop/run_final_plan.py                 # table 6.1 (about 20 s)\n'
                   'python scripts/prop/run_final_plan.py --multimarket   # + table 6.3 (generates 10 synthetic markets, about 15 min)\n'
                   'python scripts/prop/build_tape.py <bars.csv.gz> <tape.csv>   # tape for any other market file', CODE),
      p('9.3 Prompt to give an AI assistant', H2),
      Preformatted(
        'I have a repository (EnderWiggin2027/Quantconnect-Data, branch claude/festive-dirac-jgT5l) containing a prop-firm\n'
        'strategy study. Read docs/prop_firm_strategy.pdf and the code in scripts/prop/.\n'
        '1. Install numpy, pandas, pyarrow. Run python scripts/prop/run_final_plan.py and confirm the medians match\n'
        '   table 6.1 of the PDF within a few hundred dollars.\n'
        '2. Strategy: at 10:00 ET set the day direction (price vs 09:30 open); every account trades only that direction;\n'
        '   each account loops stop/target trades from its start time until +cap points or 8 trades (presets.py).\n'
        '3. Firm rules are encoded in prop_sim.py (function sim, kinds pro / fnpro / mff). Sizes are in accounts().\n'
        '4. To test a new firm: add a new kind with its fee, target, drawdown, lock, consistency, payout rules, caps\n'
        '   and split; choose sizes on synthetic data (scripts/synth_es.py) first; then run on the real ES tape.\n'
        '5. Report median, 5th percentile and P(loss) at 1, 2, 6 and 12 months, at 1 and 3 ticks of slippage.\n'
        'Keep the same anti-overfitting protocol: select on synthetic or older data, judge on data not used for selection.', CODE),
      p('9.4 Key parameters at a glance', H2),
      Preformatted('Costs per contract per trade: commission $3.50 + ticks x $12.50 (ES tick = 0.25 pt = $12.50)\n'
                   'Monte Carlo: 10,000 paths, rng seed 3, bankroll $12,000, horizons 21/42/126/252 trading days\n'
                   'Fees: Lucid 25K Pro $100 | FundedNext 25K Pro $85 | MFF 25K $98 | Lucid 50K Flex $150 | FN 50K Flex $140 (+$85 reset)\n'
                   'Post-first-payout size multiplier: 0.5 | Firm start trigger: cash >= $30,000 (MFF in Plan A; FN Pro + MFF in Plan B)', CODE)]

SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                  title='Prop-firm loop strategy', author='Research notes').build(S, onFirstPage=footer, onLaterPages=footer)
print('wrote', OUT)
