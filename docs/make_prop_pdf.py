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
    c.drawString(0.7 * inch, 0.45 * inch, 'Prop-firm strategy v3 - research notes (model results, not a forecast)')
    c.drawRightString(7.8 * inch, 0.45 * inch, f'page {d.page}'); c.restoreState()


WARN = ParagraphStyle('WARN', parent=B, backColor=colors.HexColor('#fde8e8'), borderPadding=6, borderColor=colors.HexColor('#c0392b'), borderWidth=0.7, spaceBefore=4, spaceAfter=8)
S = []
# ================================================================ 1. bottom line
S += [p('Prop-Firm Strategy: Research Notes (v3, intraday-breach update)', ParagraphStyle('T', parent=H1, fontSize=19, leading=23)),
      p('Updated November 2026. Repository <b>EnderWiggin2027/Quantconnect-Data</b>, branch <b>claude/festive-dirac-jgT5l</b>. '
        'All results are <b>simulations</b> on real ES (2022-2026), SPY x10 (2018-2025) and synthetic ES. They are model outputs, not forecasts.'),
      p('<b>Important change.</b> Earlier versions assumed the drawdown was checked only at the end of the day. The firms used here fail an account the moment '
        '<b>intraday</b> equity touches the drawdown level. Under that rule the earlier plan (+$40k at 2 months, +$697k at 12 months) <b>loses the whole $12,000 bankroll '
        'in about 99% of simulations</b>. Do not trade the earlier plan unless a firm confirms in writing that its breach is end-of-day only (Appendix A).', WARN),
      p('1. Bottom line', H1),
      *bullets([
        '<b>The strategy has almost no edge, and intraday breach removes most of what the prop payoff offered.</b> With zero-edge trading, the firm rules cap the '
        'pass rate near drawdown / (target + drawdown) and cap the money a funded account can pay out (section 2).',
        '<b>Best found: "dynamic bold play"</b> (section 3). It places one trade a day at 10:00 in the 10:00 direction, with the stop at the drawdown floor and a target sized to what the '
        'account still needs. It uses a small, real "trend-day" effect: tight-stop/far-target trades in the 10:00 direction have positive expectancy '
        '(t-stat about 1.5-2.3 on real ES, and also on SPY 2018-2021 out of sample).',
        '<b>Expected value per attempt (real ES, 1.5 ticks):</b> Lucid 150K +$86, FundedNext 150K +$82, Lucid 25K Pro +$61, FundedNext 25K Pro +$29. '
        'MFF 25K, MFF 150K and Phidias 150K are negative.',
        '<b>As a business it is small and risky:</b> 2 x Lucid 25K Pro with $12,000 has a 12-month median of +$5.8k (mean +$7.3k) and a 28% chance of a loss. '
        'Five or more accounts on $12,000 usually go broke, because fees burn the bankroll before the lumpy payouts arrive.',
        '<b>Recommendation:</b> do not treat this as income. If you go ahead, forward test first (section 7), use at most 1-2 Lucid 25K Pro accounts, and stop if '
        'slippage exceeds about 2 ticks. The large profits need either a firm with true end-of-day breach (Appendix A) or a stronger edge.'])]

# ================================================================ 2. what changed
S += [p('2. Why intraday breach changes everything', H1),
      p('Under <b>end-of-day breach</b>, intraday dips below the floor do not count, so a no-stop position had a much larger effective drawdown. That created the large '
        'convex payoff the earlier plan used. Under <b>intraday breach</b>, a zero-edge account balance behaves like a fair coin game that ends at the floor. Two limits follow '
        'from that:'),
      *bullets(['<b>Evaluation:</b> pass probability is at most about drawdown / (target + drawdown), whatever the strategy. A trailing floor and consistency rules lower it further.',
                '<b>Funded:</b> expected withdrawals are at most about the drawdown x the chance the account dies before its floor locks, times the profit split.']),
      table([['Account (fee)', 'Max pass rate', 'Max $ per funded account', 'Max EV per attempt', 'Earlier plan under intraday breach'],
             ['Lucid 25K Pro ($100)', '44%', 'about $430', 'about +$90', '25K loops: whole bankroll lost'],
             ['FundedNext 25K Pro ($85)', '40%', 'about $430', 'about +$86', ''],
             ['MFF 25K ($98)', '40% (lower with 30% rule)', 'about $430', 'about +$73', ''],
             ['Lucid 150K Flex ($265)', '33% (lower with 40% rule)', 'about $2,000', 'about +$400', '-$10k to -$12k, 78-90% loss chance'],
             ['FundedNext 150K ($260)', '33% (lower with 40% rule)', 'about $1,880', 'about +$365', 'same'],
             ['MFF 150K ($334)', '33% (lower with 50% rule)', 'about $1,500', 'about +$165', 'same'],
             ['Phidias 150K ($190)', '33%', 'about $1,800', 'about +$410', '-']], [1.45, 1.35, 1.35, 1.1, 1.75]),
      p('These are rough upper bounds before commissions, slippage and payout caps, for a strategy with no edge. The 150K bounds look large, but the 30-50% consistency '
        'rules and payout timing make them unreachable in practice (section 4).', SM)]

# ================================================================ 3. dynamic bold play
S += [p('3. The new strategy: dynamic bold play', H1),
      p('One trade per account per day. The stop and target are set in <b>dollars</b> from the account\'s current state, then converted to points for the position size.'),
      *bullets(['<b>Direction:</b> at the 10:00 ET bar close, long if ES is above the 09:30 open, short if below, no trade if equal. All accounts trade the same direction.',
                '<b>Entry:</b> market order at the 10:00 bar close.',
                '<b>Stop ($):</b> cushion above the drawdown floor minus 2 x the round-trip cost. A stop-out therefore lands just above the floor and never breaches it.',
                '<b>Target ($):</b> what the account still needs, capped per day. The cap keeps the best day under the consistency limits.',
                '<b>Exit:</b> at the stop, the target, or market at 15:59. Stop points = (stop $) / ($50 x minis); target points = (target $ + cost) / ($50 x minis).',
                '<b>Funded accounts</b> use two modes: before the floor locks, aim for the lock level; after it locks, take small daily targets to collect qualifying days and payouts.']),
      table([['Account', 'Evaluation', 'Funded, before floor locks', 'Funded, after floor locks'],
             ['Lucid 25K Pro', '1 mini. Target: rest of the $1,250. Stop: full cushion.', '1 mini. Target $660/day. Stop: full cushion.', '1 mini. Target $700/day. Stop: full cushion above the +$100 floor.'],
             ['FundedNext 25K Pro', '1 mini. Target: rest of the $1,500. Stop: full cushion.', '5 micros. Target $660/day. Stop: full cushion.', '5 micros. Target $260/day. Stop: full cushion.'],
             ['Lucid 150K Flex', '5 minis. Target: rest of $9,000, max $3,600/day. Stop: full cushion.', '2 minis. Target $5,060 (in practice, hold to the close). Stop: full cushion.', '2 minis. Target $600/day. Stop: full cushion.'],
             ['FundedNext 150K', '4 minis. Target: rest of $8,000, max $3,200/day. Stop: full cushion.', '2 minis. Target $4,510 (hold to the close). Stop: full cushion.', '2 minis. Target $600/day. Stop: full cushion.']],
            [1.25, 1.85, 1.85, 1.75]),
      p('<b>Example, Lucid 25K Pro, day 1 of an evaluation:</b> cushion $1,000, 1 mini, cost about $22. Stop = ($1,000 - $44) / $50 = 19 points. '
        'Target = ($1,250 + $22) / $50 = 25.5 points. If the stop is hit, the balance is about $24,022, still above the floor, so the account survives to try again.', SM),
      p('How the policies were chosen: about 80 evaluation x 400-600 funded policy combinations per account type were scored on synthetic ES (seeds 1-3), '
        'then checked on real ES and synthetic seeds 4-10. Tight-stop policies looked best on synthetic data but failed on real ES and were discarded. '
        'The policies above held up on every data set.', SM)]

# ================================================================ 4. results
S += [p('4. Results under intraday breach', H1),
      p('4.1 Per evaluation attempt', H2),
      table([['Account (fee)', 'Real ES 22-26, 1.5 ticks', 'Real ES, 3 ticks', 'SPY x10 2018-21 (out of sample), 1.5 ticks', 'SPY x10 2022-25, 1.5 ticks'],
             ['Lucid 150K Flex ($265)', 'pass 24% | $1,481 | <b>+$86</b>', '+$24', 'pass 28% | $2,171 | +$331', '+$122'],
             ['FundedNext 150K ($260)', 'pass 24% | $1,455 | <b>+$82</b>', '+$21', 'pass 27% | $2,005 | +$278', '+$115'],
             ['Lucid 25K Pro ($100)', 'pass 42% | $380 | <b>+$61</b>', '+$37', 'pass 46% | $526 | +$141', '+$81'],
             ['FundedNext 25K Pro ($85)', 'pass 38% | $303 | <b>+$29</b>', '+$16', 'pass 39% | $431 | +$83', '+$40'],
             ['MFF 25K / MFF 150K / Phidias 150K', 'negative (-$34 / -$61 / -$37)', 'negative', 'not tested', '-']], [1.55, 1.55, 0.8, 1.7, 1.1]),
      p('Cells: pass rate | $ received per funded account (after split) | expected value per attempt (net of the fee).', SM),
      p('4.2 As a business (12 months, 1.5 ticks)', H2),
      table([['Setup', 'Real ES 2022-26: median / mean / P(loss)', 'SPY 2018-21 (out of sample)', 'SPY 2022-25'],
             ['Lucid 25K Pro x1, $12k', '+$2.9k / +$3.7k / 28%', '+$4.7k / +$5.5k / 16%', '+$4.1k / +$4.9k / 19%'],
             ['<b>Lucid 25K Pro x2, $12k</b>', '<b>+$5.8k / +$7.3k / 28%</b>', '+$9.5k / +$11.1k / 16%', '+$8.2k / +$9.8k / 19%'],
             ['Lucid 150K x1 + FN 150K x1, $30k', '+$6.5k / +$7.9k / 37%', '+$20.9k / +$21.9k / 14%', '+$9.4k / +$10.7k / 32%'],
             ['Lucid 25K Pro x5, $12k', '+$10.9k / +$15.9k / 38%', '+$22.7k / +$26.4k / 20%', '+$18.4k / +$22.0k / 28%'],
             ['Five 150Ks, $12k', 'goes broke in 60-80% of runs', '', '']], [1.9, 1.75, 1.6, 1.45], hl=[2]),
      *bullets(['At 2 months every setup is roughly a coin flip (52-59% chance of being down). Results only build up over a year.',
                'Identical accounts trade the same day, so they win and lose together. Two accounts double the bet; they do not diversify it.',
                'More accounts per dollar of bankroll raise the median but sharply raise the chance of going broke.'])]

# ================================================================ 5. trend-day edge
S += [p('5. The trend-day edge', H1),
      p('Trades in the 10:00 direction with a tight stop and a far target earn a small positive amount on average. This fits published "intraday momentum" findings: '
        'the first half-hour\'s direction tends to persist on trend days. It is the only edge found in this study.'),
      table([['Gross points per trade (t-stat)', 'Stop 2 / target 20', 'Stop 3 / target 30', 'Stop 5 / target 40', 'Stop 10 / target 40'],
             ['Real ES 2022-2026 (1,199 days)', '+0.30 (1.5)', '+0.45 (1.6)', '+0.95 (2.3)', '+0.97 (1.8)'],
             ['SPY x10 2018-2021, out of sample (898 days)', '+0.34 (1.6)', '+0.56 (1.9)', '+0.88 (2.3)', '+0.94 (1.9)'],
             ['SPY x10 2022-2025 (982 days)', '+0.69 (3.0)', '+0.84 (2.6)', '+1.35 (2.9)', '+1.24 (2.1)'],
             ['Synthetic ES seeds 4-10 (17,500 days)', '+0.48 (9.1)', '+0.33 (4.5)', '+0.35 (3.3)', '+0.10 (0.7)']], [2.3, 1.1, 1.1, 1.1, 1.1]),
      *bullets(['The effect is small: about 1 point per trade before costs. Costs are about 0.4-0.9 points per trade at 1.5-3 ticks.',
                'The t-stats of about 2 are suggestive, not proof. Several stop/target pairs were looked at, so some of it may be chance.',
                'The synthetic generator shows the effect more strongly than real markets. Selection therefore used synthetic data, but only policies that also worked on real data were kept.']),
      p('6. What would make this worthwhile', H1),
      *bullets(['<b>A firm with true end-of-day breach</b> (intraday dips allowed). The earlier plan works there (Appendix A). Confirm the exact wording in writing.',
                '<b>Cheaper evaluations:</b> discounts and coupons raise EV directly. At half price, the Lucid 25K Pro EV per attempt roughly doubles.',
                '<b>A stronger edge:</b> test the trend-day effect on more years and markets (CL, GC, NQ); combine with filters that do not overfit.',
                '<b>Lower costs:</b> slippage is the biggest controllable factor. At 3 ticks most of the edge is gone.']),
      p('6.1 What the firms say about breach timing (checked November 2026)', H2),
      table([['Firm / account', 'Breach timing', 'Official wording (summary)'],
             ['FundedNext Futures (all account types)', '<b>Intraday</b>', '"Updates only at the end of the trading day (EOD), not in real time" but "if your floating loss reaches the maximum loss limit during an active trade, your account will be instantly breached."'],
             ['MyFundedFutures (EOD trailing)', '<b>Intraday</b>', '"open equity losses are taken into consideration... if an open position dips your account balance below the minimum account balance, your evaluation attempt will fail."'],
             ['Lucid (LucidFlex 150K, LucidPro 25K)', 'Unclear', '"End-of-Day Drawdown system" and "If your account balance reached the MLL, your account will be breached." Open P&amp;L is not addressed.'],
             ['Phidias 150K', 'Unclear, probably intraday', '"Your liquidation price remains fixed for the day" and "if your balance reaches... your drawdown limit, you will be liquidated."'],
             ['Apex, Topstep, Alpha Futures, Tradeify, Earn2Trade', 'Intraday (third-party summaries)', 'For example "calculated end of day, enforced intraday".']], [1.85, 1.05, 3.8]),
      p('No reputable futures firm was found that clearly checks the drawdown only at the close. "EOD drawdown" almost always means the <b>level</b> moves at the close '
        'while a touch during the session still fails the account. Ask Lucid and Phidias support in writing: "Does an open-position loss that touches the MLL intraday '
        'fail the account if the closing balance is above it?" Sources: helpfutures.fundednext.com, help.myfundedfutures.com, support.lucidtrading.com, phidiaspropfirm.com/rules.', SM),
      p('7. Before risking money', H1),
      *bullets(['<b>Age and terms:</b> prop firms and NinjaTrader require you to be 18 or older; check each firm\'s terms.',
                '<b>Confirm the rules</b> for every account: breach type, consistency, payout rules, account limits, and whether automated or copied trading is allowed.',
                '<b>Forward test</b> on simulation or with the paper tracker for at least a month. Record real fills and slippage on the 10:00 entry and the stop.',
                '<b>Start with 1 Lucid 25K Pro</b> ($100). Expect most months to be flat or down; the edge shows only over many attempts.',
                '<b>Stop rules:</b> stop if measured slippage averages more than 2 ticks, or if 30 attempts produce fewer than 9 passes (about 30%).'])]

# ================================================================ appendix A: EOD plan
S += [PageBreak(), p('Appendix A. The end-of-day-breach plan (only if a firm truly checks the drawdown at the close)', H1),
      p('Valid <b>only</b> where intraday dips below the drawdown level do not fail the account. It used no stop on the 150Ks, which is fatal under intraday breach.', NOTE),
      table([['Account', 'Evaluation', 'Funded'],
             ['Lucid 150K Flex', '10 minis, limit +7 pts, no stop, done when filled, else exit 15:59', '10 minis, +3 pts'],
             ['FundedNext 150K', '8 minis, +8 pts, no stop', '8 minis, +3 pts'],
             ['MyFundedFutures 150K', '9 minis, +11 pts, no stop', '9 minis, +4 pts'],
             ['Phidias 150K', '17 minis, +12 pts, no stop (passes in 1 day)', '6 minis, +2 pts'],
             ['25K accounts (A/B loops)', 'From 10:00 (A) / 11:00 (B): stop 8 / target 8, re-enter, stop at +6 pts or 8 trades, 20 micros', 'Stop 12 / target 8, 18 micros, halve after 1st payout']],
            [1.6, 3.3, 1.8]),
      table([['End-of-day breach, real ES, $12k start', '2-month median (P(loss))', '12-month median (5th pct)'],
             ['Final plan, 1 tick', '+$40.2k (2.0%)', '+$697k (+$432k)'],
             ['Final plan, realistic costs (1.5 ticks, 5 on red days, limit trade-through)', '+$32.6k (2.9%)', '+$592k (+$344k)'],
             ['Final plan + 5 Phidias 150K at $30k, realistic costs', '+$33.6k (3.4%)', '+$723k (+$436k)']], [3.4, 1.6, 1.7]),
      p('Plan: Lucid 3 x 150K + 2 x 25K Pro and FundedNext 2 x 25K Pro on day 1; FundedNext 3 x 150K, MFF 3 x 150K + 2 x 25K (and optionally Phidias 5 x 150K) when cash reaches $30k. '
        'Reproduce: python scripts/prop/run_final_plan.py', SM),
      p('Appendix B. Robustness tests (end-of-day plan)', H1),
      table([['Test', 'Result'],
             ['Look-ahead leak: gross points per trade', 'About -1 to 0 for every shape: no leak'],
             ['Replace the 10:00 direction with a coin flip', 'Similar results: profit came from the payoff structure, not a hidden signal'],
             ['Limit fills need 1-2 ticks of trade-through', '-6% to -14%'],
             ['Choose targets on half the data, test on the other half (8 markets)', 'Selection bias about 1% at 12 months, about 7% at 2 months'],
             ['7 synthetic markets never used for selection', 'All strongly positive (12-month medians $569k to $1.19M)'],
             ['1.5 ticks + 5 ticks on red-folder days (12%) + trade-through', 'About -15% versus the 1-tick headline'],
             ['<b>Intraday breach</b>', '<b>Whole bankroll lost in about 99% of runs</b>']], [3.3, 3.4])]

# ================================================================ method / replication
S += [PageBreak(), p('8. Method', H1),
      *bullets(['<b>Data:</b> continuous front-month ES 1-minute RTH bars 2022-2026; SPY 1-minute 2018-2025 x10 (out-of-sample check); synthetic ES '
                '(jump-diffusion + GARCH + regimes, scripts/synth_es.py) seeds 1-10.',
                '<b>Trade engine (dyn.py):</b> for each day it stores the bar at which every favourable and adverse distance (0.25-pt steps) is first reached, so any '
                'stop/target pair is evaluated exactly. If a bar reaches both, the stop counts first.',
                '<b>Breach:</b> the account fails if the day\'s worst intraday equity (closed + open, after costs) touches the floor set at the previous close. '
                'Floors, locks, targets, consistency, minimum days, payout rules, caps and splits follow the firm rules encoded in prop_sim.py.',
                '<b>Monte Carlo:</b> 10,000 paths, days drawn at random with replacement, all accounts trade the same drawn day, shared bankroll, fees paid on purchase.',
                '<b>Costs:</b> per-firm commissions (Lucid $3.50 per mini, FundedNext $5.76, MFF $4.68, Phidias $4.00 assumed) plus slippage of 1.5 or 3 ticks x $12.50 per mini per trade.']),
      p('9. Risks', H1),
      *bullets(['<b>Firm rules and enforcement:</b> any rule change, payout review or ban removes the edge. Several rules are assumptions.',
                '<b>Weak statistics:</b> the trend-day edge has a t-stat of about 2. It may shrink or vanish.',
                '<b>Variance:</b> even with positive EV, about 1 in 4 to 1 in 3 one-year runs lose money, and early months are a coin flip.',
                '<b>Execution:</b> large stops near the floor; a gap or fast market can slip past the stop and breach the account.',
                '<b>Taxes and fees</b> (platform, data, activation) are not modeled.']),
      p('10. Replication', H1),
      table([['File', 'Purpose'],
             ['scripts/prop/dyn.py', 'Dynamic bold play: first-hit tables, trade engine, evaluation/funded policies, business simulation'],
             ['scripts/prop/run_intraday.py', 'Reproduces sections 4-5 (add --spy for the SPY checks)'],
             ['scripts/prop/prop_sim.py', 'Firm rules, floors, payouts; optional intraday-breach mode'],
             ['scripts/prop/build_shapes_intraday.py', 'Fixed stop/target shape grid with worst intraday point (section 2 search)'],
             ['scripts/prop/run_final_plan.py, run_25k_plans.py', 'End-of-day plan (Appendix A)'],
             ['docs/make_prop_pdf.py', 'Regenerates this PDF']], [2.8, 3.9]),
      Preformatted('pip install numpy pandas pyarrow reportlab\n'
                   'python scripts/prop/run_intraday.py          # intraday-breach results (about 30 s)\n'
                   'python scripts/prop/run_intraday.py --spy    # + SPY 2018-2021 out-of-sample check\n'
                   'python scripts/prop/run_final_plan.py        # end-of-day plan (Appendix A)\n'
                   'python docs/make_prop_pdf.py                 # rebuild this PDF', CODE)]

SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                  title='Prop-firm strategy', author='Research notes').build(S, onFirstPage=footer, onLaterPages=footer)
print('wrote', OUT)
