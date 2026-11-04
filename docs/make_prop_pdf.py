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
    c.drawString(0.7 * inch, 0.45 * inch, 'Prop-firm strategy - research notes (model results, not a forecast)')
    c.drawRightString(7.8 * inch, 0.45 * inch, f'page {d.page}'); c.restoreState()


S = []
# ================================================================ 1. title / bottom line
S += [p('Prop-Firm Strategy: Playbook, Results, Rules and Replication Guide', ParagraphStyle('T', parent=H1, fontSize=19, leading=23)),
      p('Research notes, updated November 2026. Repository: <b>EnderWiggin2027/Quantconnect-Data</b>, branch <b>claude/festive-dirac-jgT5l</b>. '
        'Everything here is a <b>simulation</b> of futures prop-firm accounts on real ES data (2022-2026). The numbers are model outputs, not guarantees.'),
      p('1. Bottom line', H1),
      *bullets([
        'The trading rules have <b>no edge of their own</b>. On real ES the gross result is about 0 points per trade, and a normal-account backtest lost money. '
        '<b>All the modeled profit comes from the prop-firm payoff</b>: a failed evaluation costs only its fee, while payouts are real cash.',
        '<b>The final plan uses three firms and two account types.</b> The 150K accounts use a "one-trade" playbook that is only valid where the drawdown is checked at the '
        '<b>end of the day</b> (not intraday). The 25K accounts use the earlier "loop" playbook.',
        '<b>Day 1:</b> Lucid 3 x 150K Flex + 2 x 25K Pro, and FundedNext 2 x 25K Pro. <b>When cash reaches $30,000:</b> FundedNext 3 x 150K Flex, '
        'and MyFundedFutures 3 x 150K + 2 x 25K. That is 15 accounts at full build-out, the maximum of 5 per firm.',
        '<b>Median result at about 1 tick of slippage</b>, starting with $12,000, after each firm\'s real commissions: '
        '<b>+$40k at 2 months</b> (2.0% chance of being down), <b>+$303k at 6 months</b>, <b>+$697k at 12 months</b>. '
        'At 3 ticks: +$29k / +$241k / +$564k.',
        'This is a high-volume business: about 500 evaluations a year, about $94k of fees spent against about $790k of payouts received (medians, 1 tick).',
        'The biggest unknowns are <b>firm rules and enforcement</b> (a rule change, payout denial, or ban removes the edge), <b>your real slippage</b>, and '
        '<b>end-of-day versus intraday breach</b>. If a 150K account liquidates intraday, the one-trade playbook roughly breaks even and must not be used.'])]
S += [p('<b>Read before trading.</b> Confirm every rule in section 6 with each firm\'s current terms. Confirm that running the same strategy on many '
                 'accounts is allowed. Never run this strategy with your own capital: without the prop payoff it loses money.', NOTE)]

# ================================================================ 2. easy playbook
S += [PageBreak(), p('2. The easy playbook', H1),
      p('2.1 What to buy', H2),
      table([['When', 'Lucid', 'FundedNext', 'MyFundedFutures'],
             ['Day 1 (cost about $1,166)', '3 x 150K Flex ($265.30 each) + 2 x 25K Pro, loss limit OFF ($100 each)', '2 x 25K Pro ($85 each)', '-'],
             ['When cash reaches $30,000', '-', 'add 3 x 150K Flex ($259.99 each)', 'add 3 x 150K ($334 each) + 2 x 25K ($98 each)'],
             ['Always', 'Keep 5 slots full: when an account busts or closes, buy a new evaluation the next day', 'Same', 'Same']],
            [1.45, 2.15, 1.55, 1.55]),
      p('"Cash" means your starting $12,000 plus all payouts received minus all fees paid.', SM),
      p('2.2 Daily routine (all times ET)', H2),
      table([['Time', 'What to do'],
             ['09:30', 'Note the opening price of ES (the first 1-minute bar\'s open).'],
             ['10:00', '<b>Set the day\'s direction.</b> ES above the 09:30 open: everyone goes LONG today. Below: everyone goes SHORT. Equal: no trading. '
                       'Then open the 150K one-trade positions and start the 25K "A" loops.'],
             ['11:00', 'Start the 25K "B" loops.'],
             ['15:30', 'No new 25K loop entries after this time.'],
             ['15:59', 'Flatten everything that is still open, on every account.']], [0.7, 6.0]),
      p('2.3 Account cards', H2),
      p('<b>150K one-trade playbook.</b> At 10:00, buy (or sell) at market at max size in the day\'s direction. Place a <b>limit</b> take-profit X points away. '
        '<b>No stop.</b> If the target fills, you are done for the day. If not, close at market at 15:59.', B),
      table([['Firm, 150K account', 'Evaluation: size / target', 'Funded: size / target', 'Pass rate (model)', 'Avg paid per funded account'],
             ['Lucid 150K Flex', '10 minis / +7 points', '10 minis / +3 points', '56%', 'about $4,930'],
             ['FundedNext 150K Flex', '8 minis / +8 points', '8 minis / +3 points', '53%', 'about $5,770'],
             ['MyFundedFutures 150K', '9 minis / +11 points', '9 minis / +4 points', '58% (min 2 days)', 'about $5,810 (33% get any payout)']],
            [1.45, 1.4, 1.3, 1.05, 1.5], hl=[1, 2, 3]),
      p('Why no stop: with end-of-day breach and a $4,000-4,500 drawdown, an intraday swing does not end the account. Only the close counts. '
        'Bold play (max size, one shot) passes more often than any cautious sizing tested.', SM),
      Spacer(1, 4),
      p('<b>25K loop playbook</b> (Lucid 25K Pro, FundedNext 25K Pro, MFF 25K: two accounts each, called A and B). From the start time, enter at market in the day\'s direction '
        'with a stop and a target. When the trade exits, re-enter on the next bar. Stop for the day once that day\'s closed profit reaches +6 points '
        '(per contract), or after 8 trades.', B),
      table([['Account', 'Evaluation: start / stop / target / day cap / size', 'Funded: start / stop / target / day cap / size', 'After first payout'],
             ['A', '10:00 / 8 / 8 / +6 pts / 20 micros', '10:00 / 12 / 8 / +6 pts / 18 micros', 'Halve to 9 micros'],
             ['B', '11:00 / 8 / 8 / +6 pts / 20 micros', '11:00 / 12 / 8 / +6 pts / 18 micros', 'Halve to 9 micros']],
            [0.75, 2.3, 2.3, 1.35]),
      p('2.4 Events', H2),
      table([['Event', 'Action'],
             ['Evaluation passes', 'Switch that account to its funded card the next day.'],
             ['Account busts (closes at or below the floor)', 'Buy a new evaluation for that slot the next day (only if cash covers the fee).'],
             ['Payout becomes allowed', 'Request it immediately, every time. Payouts refill cash and fund new evaluations.'],
             ['Funded account hits its payout limit (Lucid and FN 150K: 5 payouts)', 'It closes. Buy a new evaluation for the slot.'],
             ['Cash reaches $30,000', 'Buy the FundedNext 150Ks and the MFF 150Ks + 25Ks (section 2.1).']], [2.6, 4.1]),
      p('2.5 Golden rules', H2),
      *bullets(['Every account trades the <b>same direction</b>. Never hold opposite positions across accounts (all firms ban hedging).',
                'Never use the no-stop 150K playbook on an account that liquidates <b>intraday</b>.',
                'Stay inside each firm\'s max size and its news rules. Be flat by the firm\'s cutoff (for example, Lucid at 4:45pm).',
                'Do not add accounts early, size up after wins, or skip the direction rule. Every such change was tested and made results worse.'])]

# ================================================================ 3. results
S += [PageBreak(), p('3. Expected results (final plan, real ES 2022-2026)', H1),
      p('Each row shows medians of 10,000 simulated paths with a $12,000 start. "Spent" is evaluation fees paid. "Payouts" is cash received after the profit split. '
        '"Net" is the change in cash. The 5th percentile is a bad 1-in-20 outcome.'),
      table([['Slippage', 'Horizon', 'Spent', 'Payouts', 'Net (median)', 'Net, 5th pct', 'P(loss)', 'Evals bought'],
             ['1 tick', '2 months', '$12,241', '$54,494', '<b>+$40,244</b>', '+$5,993', '2.0%', '71'],
             ['1 tick', '6 months', '$44,966', '$349,355', '<b>+$303,369</b>', '+$129,785', '0.3%', '244'],
             ['1 tick', '12 months', '$93,687', '$790,496', '<b>+$696,534</b>', '+$432,079', '0.3%', '503'],
             ['3 ticks', '2 months', '$12,191', '$43,482', '+$29,041', '+$2,530', '3.5%', '74'],
             ['3 ticks', '6 months', '$47,430', '$290,094', '+$241,482', '+$83,483', '0.8%', '266'],
             ['3 ticks', '12 months', '$100,397', '$665,164', '+$563,604', '+$321,504', '0.7%', '555']],
            [0.65, 0.8, 0.8, 0.9, 1.0, 0.95, 0.65, 0.95], hl=[1, 2, 3]),
      p('Medians do not add exactly (median spent + median net differs from median payouts). Commissions are per firm (section 6.2). Taxes, platform and data fees are '
        '<b>not</b> included. Reproduce with: python scripts/prop/run_final_plan.py (about 10 s).', SM),
      p('3.1 How to read this', H2),
      *bullets(['The first two months carry almost all the risk: cash is thin, and only Lucid and the FundedNext 25Ks are running. '
                'Staging the FundedNext and MFF 150Ks until $30k keeps the 2-month loss chance at about 2-3.5%.',
                'Spending roughly equals or exceeds the starting bankroll in the first 2 months. Payouts are recycled into new evaluations; '
                'you never need more than the $12,000 at once in the model.',
                'Slippage matters more than commissions. Real per-firm commissions cost about 2-3% of profit; going from 1 to 3 ticks costs about 20%.',
                'Twelve-month figures assume the firms keep accepting about 500 evaluations and hundreds of payouts a year from one person. '
                'That is the least certain assumption in the whole study.'])]

# ================================================================ 4. why it works
S += [p('4. Why it works', H1),
      p('4.1 The convex payoff', H2),
      p('An evaluation is an option: the downside is the fee ($85-$334), and the upside is a funded account paying thousands. With zero-edge trades, the pass '
        'probability depends on the <b>shape</b> of the daily profit and loss relative to the target and the drawdown, not on prediction skill. Tests confirmed this: '
        'a random-direction version passed evaluations about as often as the momentum version. '
        'The 10:00 direction rule only helps in the funded phase.'),
      p('4.2 Bold play on the 150Ks', H2),
      p('For a fair game, the best way to reach a target before a floor is to bet big and as few times as possible ("bold play"). On a 150K with a $9,000 target, '
        '10 minis x +7 points is $3,500 a day, so a pass needs about 3 good days, and the $4,500 end-of-day drawdown absorbs most losing days. '
        'Cushion-based (timid) sizing was tested and passed less often. In the funded phase the target drops to +3/+4 points, '
        'so payouts are collected before the account wanders down to the floor.'),
      p('4.3 Why end-of-day breach is essential', H2),
      p('With no stop, an open position can be thousands of dollars down at midday and still finish fine. If the firm liquidates at the intraday floor, those days become '
        'busts. Modeled with intraday liquidation, the 150K one-trade playbook was about break-even (EV of -$55 to +$25 per attempt), so it was rejected for that case. '
        'Lucid, FundedNext and MFF 150K were modeled as end-of-day breach. <b>Confirm this before trading.</b>'),
      KeepTogether([p('4.4 Why the 25Ks still loop', H2),
      p('The 25K accounts cap size at 2 minis and have a tiny $1,000 drawdown, so bold play is impossible. The loop with a small daily profit cap '
        'creates many small winning days and passes the easy $1,250-$1,500 targets quickly. These accounts carry the early months while the 150Ks are being bought.')])]

# ================================================================ 5. exact rules
S += [p('5. Exact mechanical rules', H1),
      p('<b>Instrument:</b> ES and MES futures (1 point = $50 per mini, $5 per micro). Regular session 09:30-16:00 ET. Times are 1-minute bar <b>end</b> times.'),
      p('5.1 Direction (all accounts)', H2),
      *bullets(['At the 10:00 bar close compare price with the 09:30 open (open of the first bar). Above: long only. Below: short only. Equal: no trading.']),
      p('5.2 150K one-trade', H2),
      *bullets(['Entry: market at the 10:00 bar close, in the day\'s direction, at the card size.',
                'Exit: limit at entry +/- target points. No stop. If the target is not filled, exit at market at 15:59 (or 2 minutes before an early close).',
                'At most one trade per day. Simulation fills: the target fills when a later bar\'s high (long) or low (short) reaches it.']),
      p('5.3 25K loop ("Portfolio B" slots 1 and 2)', H2),
      *bullets(['From the start time, enter at the bar close with stop S and target T. When a trade exits, re-enter on the next bar with the same S and T.',
                'Stop for the day at +cap points closed (per contract, gross) or after 8 trades. No entries after 15:30. Flatten at 15:59.',
                'If a bar touches both the stop and the target, the stop is assumed to fill first. If a bar opens beyond a level, the fill is at the open.',
                'Funded size halves after the account\'s first payout (18 to 9 micros). This was the one tuning that raised profit and cut risk.']),
      p('5.4 Account management', H2),
      *bullets(['Up to 5 accounts per firm. Refill a slot the day after it busts or closes, if cash covers the fee. Request payouts the first day they are allowed.',
                'FundedNext and MFF 150K, plus MFF 25K, start only when cash is at least $30,000. After that they are refilled like the others.'])]

# ================================================================ 6. firm rules
S += [p('6. Firm rules as modeled', H1),
      p('"(A)" marks an <b>assumption</b> where the material provided did not state the rule. If any rule differs, edit scripts/prop/prop_sim.py and rerun.', NOTE),
      p('6.1 150K accounts', H2),
      table([['Rule', 'Lucid 150K Flex', 'FundedNext 150K Flex', 'MyFundedFutures 150K'],
             ['Price', '$265.30', '$259.99', '$334'],
             ['Target / drawdown', '$9,000 / $4,500 end-of-day trailing', '$8,000 / $4,000 end-of-day trailing', '$9,000 / $4,500 end-of-day trailing'],
             ['Breach', 'End of day only', 'End of day only (A)', 'End of day only (A)'],
             ['Eval consistency', '40%: target = max($9,000, best day / 0.4)', '40% (best day $3,200 at the base target)', '50%: target = max($9,000, best day / 0.5)'],
             ['Min eval days', '-', '3', '2'],
             ['Max size', '10 minis', '8 minis', '9 minis'],
             ['Funded floor lock', 'Locks at +$100 once balance reaches $154,600, or at first payout', 'Locks at +$100 once up $4,100, or at first payout', 'Locks at +$100 after first payout'],
             ['Payout conditions', '5 days of $250+ since last payout; cycle profit &gt; 0', '5 days of $250+; cycle profit at least $500', 'Every 10 funded trading days (about 14 calendar days) (A)'],
             ['Payout amount', '50% of profit, cap $3,000, min $500', '50% of profit, cap $4,000', '60% of profit (A), min $1,000'],
             ['Split / payout limit', '90% / closes after 5 payouts', '95% / closes after 5 payouts', '80% / no limit (A)']],
            [1.25, 1.85, 1.8, 1.8]),
      p('6.2 25K accounts', H2),
      table([['Rule', 'Lucid 25K Pro', 'FundedNext 25K Pro', 'MyFundedFutures 25K'],
             ['Price', '$100 (daily loss limit OFF)', '$85', '$98'],
             ['Target / drawdown', '$1,250 / $1,000 end-of-day', '$1,500 / $1,000 end-of-day', '$1,500 / $1,000 end-of-day'],
             ['Eval consistency / min days', 'None', 'None', '30% (target bump) / 4 days'],
             ['Funded floor', 'Locks at +$100', 'Locks at +$100 (A)', 'Locks at +$100'],
             ['Payout conditions', '$250+ since last payout; best day at most 40% of cycle; $1,100 buffer', 'Every 3 trading days (A); best day at most 40%', 'Daily; $250+ net; $1,100 buffer'],
             ['Payout amount', 'Profit - $1,100, cap $1,000 first, $1,500 later; min $500', '50% of profit (A), cap $800, min $250', 'Profit - $1,100, min $500'],
             ['Split', '90%', '90%', '90%']],
            [1.25, 1.85, 1.8, 1.8]),
      p('6.3 Commissions (round trip, per contract)', H2),
      table([['Firm', 'ES mini', 'MES micro', 'Source'],
             ['Lucid', '$3.50', '$1.00', '$1.75 / $0.50 per side (user-provided)'],
             ['FundedNext', '$5.76', '$1.74 (A)', '$2.88 per side (user-provided)'],
             ['MyFundedFutures', '$4.68', '$1.74', 'User-provided'],
             ['Slippage (all)', '1 or 3 ticks x $12.50 per mini-equivalent per trade', '', 'Model input']], [1.4, 1.5, 1.2, 2.6])]

# ================================================================ 7. rejected
S += [PageBreak(), p('7. What was tested and rejected', H1),
      table([['Option', 'Why it was rejected'],
             ['150K one-trade with <b>intraday</b> liquidation', 'Roughly break-even (EV of -$55 to +$25 per attempt). Midday swings bust accounts that would recover by the close.'],
             ['Cushion / timid sizing on the 150Ks', 'Lower pass rate than bold play at max size.'],
             ['Lucid 25K Pro with the daily loss limit ON ($84)', 'Loses: the $600 pause cuts the loop\'s recovery trades (12-month median about +$7.7k, 24% loss chance).'],
             ['Lucid 50K Flex ($150)', 'Works, but the 2-month loss chance is about 18%. Replaced by the 150K Flex.'],
             ['FundedNext 50K Flex ($140)', 'Works alone (about +$55k a year), but is weaker than the FN 25K Pro + 150K pair.'],
             ['Apex 50K', '$1,000 daily loss limit, safety-net payouts and a 50% consistency rule: lost money at every size tested.'],
             ['Tradeify (all accounts)', 'Excluded by choice. The 25K v1 lost money; the v2 was weak.'],
             ['Filters, other entries and exits, brute-force mixes', 'VIX, gap and opening-range filters; pullback, breakout, trailing and breakeven exits; 1,500 random portfolios. '
                                                                 'Improvements did not hold out of sample.'],
             ['Adding all firms on day 1', 'More money at 12 months, but a 2-month loss chance of 8-19%. Staging at $30k is the better trade-off.']], [2.4, 4.3]),
      p('8. How the plan evolved', H1),
      p('Before the 150K accounts, the best plan used only 25K accounts (5 per firm, all on the loop). Results on real ES, at Lucid-style $3.50 commissions:'),
      table([['Slippage', 'All-25K plan', '2 months', '6 months', '12 months'],
             ['1 tick', 'A: Lucid Pro + FN Pro day 1, MFF at $30k', '+16,836 / -1,099 / 6.3%', '+77,978 / +25,468 / 0.2%', '+175,875 / +97,882 / 0.2%'],
             ['1 tick', 'B: Lucid Pro day 1, FN Pro + MFF at $30k', '+10,868 / -29 / 5.1%', '+59,296 / +15,221 / 0.1%', '+157,475 / +80,815 / 0.0%'],
             ['3 ticks', 'A', '+10,607 / -5,117 / 15.3%', '+46,561 / +7,737 / 2.1%', '+110,847 / +40,672 / 1.2%'],
             ['3 ticks', 'B', '+6,875 / -2,296 / 12.4%', '+28,926 / +7,263 / 0.8%', '+93,843 / +29,498 / 0.1%']],
            [0.7, 2.2, 1.25, 1.25, 1.3]),
      p('Cells: median net / 5th percentile / chance of loss. Reproduce with python scripts/prop/run_25k_plans.py. '
        'Adding the end-of-day 150K accounts with the one-trade playbook raised the 12-month median about 4x (+$176k to +$697k) and cut the 2-month loss chance from 6.3% to 2.0%.', SM),
      p('8.1 Multiple markets (synthetic test, still open)', H2),
      p('Running accounts on independent synthetic markets cut early risk 3-10x (for example, the 1-month loss chance fell from 16% to 3% with 10 markets). '
        'Synthetic markets are perfectly independent, so this is an upper bound. The real test needs CL, GC, SI, HG and NG 1-minute data '
        '(multi_market_download.ipynb, split by year), with the playbooks rescaled to each market\'s volatility. Reproduce: run_25k_plans.py --multimarket.')]

# ================================================================ 9. method
S += [PageBreak(), p('9. Method', H1),
      *bullets(['<b>Data:</b> continuous front-month ES 1-minute RTH bars, Jan 2022 - Nov 2026 (data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz, from QuantConnect via '
                'ES_download.ipynb). Full days only (first bar 09:31, at least 300 bars): 1,199 days.',
                '<b>Tapes:</b> build_tape.py records each 25K preset\'s daily points and trade count. build_shapes.py does the same for the five 150K one-trade shapes. '
                'Day $ = 50 x size x points - trades x (commission + size x ticks x $12.50).',
                '<b>Monte Carlo:</b> 10,000 paths at seed 3. Each path draws trading days at random from the tape, and <b>all accounts trade the same drawn day</b>, '
                'so cross-account correlation is kept. The shared bankroll starts at $12,000. Horizons are 42, 126 and 252 trading days.',
                '<b>Every rule in section 6 is applied daily:</b> fees, end-of-day trailing floors and locks, consistency as a target bump, minimum days, payout '
                'conditions, caps, splits, payout limits and the $30k start trigger.',
                '<b>Anti-overfitting:</b> playbooks were selected on synthetic ES (seeds 1-3, scripts/synth_es.py: jump-diffusion + GARCH + regimes) or on older data, '
                'then judged on real ES. Searches that did not hold out of sample were dropped.',
                '<b>Known weaknesses:</b> 2022-2026 is a single, mostly rising period; the bootstrap ignores multi-day streaks; payouts and rebuys are instant; '
                'some firm rules are assumed (A).'])]
S += [p('10. Risks', H1),
      *bullets(['<b>Rules and enforcement:</b> the whole profit depends on the firms. Rule changes, payout reviews, or bans for running the same strategy across many accounts would end it.',
                '<b>Scale:</b> about 500 evaluations and hundreds of payouts a year may draw scrutiny. The 6- and 12-month numbers assume nothing changes.',
                '<b>No-stop exposure:</b> a 150K position at 10 minis can lose $5,000+ on a crash day. The firm absorbs it in the model, but a gap past the floor may still count.',
                '<b>Correlation:</b> all accounts trade one direction in one market, so bad days hit everything at once.',
                '<b>Slippage:</b> 3 ticks costs about 20% of profit. Measure it on a simulated account before going live.',
                '<b>Taxes and fees:</b> income tax on payouts, platform and data fees, and activation fees are not modeled.'])]

# ================================================================ 11. replication
S += [PageBreak(), p('11. Replication guide', H1),
      table([['Path', 'What it is'],
             ['data/ES_1m_RTH/ES_1m_RTH_2022-2026.csv.gz', 'Real ES 1-minute RTH bars (input)'],
             ['data/tapes/ES_tape_2022-2026.csv', '25K loop tape (built automatically if missing)'],
             ['data/tapes/ES_shapes_2022-2026.pkl', '150K one-trade shape tape (built automatically if missing)'],
             ['scripts/prop/presets.py, build_tape.py', '25K loop presets and the tape builder'],
             ['scripts/prop/build_shapes.py', '150K one-trade shapes (targets 7, 8, 11, 3, 4 points)'],
             ['scripts/prop/prop_sim.py', 'Monte Carlo of all firms (kinds l150, pro, fn150, fnpro, mff150, mff). Fees and rules live here.'],
             ['scripts/prop/run_final_plan.py', 'Final plan: section 3 table, with per-firm commissions'],
             ['scripts/prop/run_25k_plans.py', 'Earlier all-25K plans (section 8); --multimarket for the synthetic test'],
             ['scripts/synth_es.py', 'Synthetic ES generator'],
             ['docs/make_prop_pdf.py', 'Regenerates this PDF']], [2.9, 3.8]),
      Spacer(1, 6),
      Preformatted('git clone https://github.com/EnderWiggin2027/Quantconnect-Data && cd Quantconnect-Data\n'
                   'git checkout claude/festive-dirac-jgT5l\n'
                   'pip install numpy pandas reportlab\n'
                   'python scripts/prop/run_final_plan.py          # final plan, section 3 (about 10 s)\n'
                   'python scripts/prop/run_25k_plans.py           # earlier 25K plans, section 8 (about 20 s)\n'
                   'python docs/make_prop_pdf.py                   # rebuild this PDF', CODE),
      p('11.1 Prompt to give an AI assistant', H2),
      Preformatted(
        'Repository EnderWiggin2027/Quantconnect-Data, branch claude/festive-dirac-jgT5l, contains a prop-firm study.\n'
        'Read docs/prop_firm_strategy.pdf and scripts/prop/.\n'
        '1. Run python scripts/prop/run_final_plan.py and confirm the medians match section 3 of the PDF.\n'
        '2. Direction: 10:00 ET close vs 09:30 open; all accounts trade that direction only.\n'
        '   150K accounts: one market entry at 10:00, limit target, no stop, exit 15:59 (build_shapes.py).\n'
        '   25K accounts: stop/target loop with a daily profit cap (presets.py, build_tape.py).\n'
        '3. Firm rules are in prop_sim.py (function sim). Sizes and commissions are in run_final_plan.py.\n'
        '4. To test a new firm, add a kind with its fee, target, drawdown, lock, consistency, payout rules, caps\n'
        '   and split. Choose sizes on synthetic data first (scripts/synth_es.py), then run on real ES.\n'
        '5. Report median, 5th percentile and P(loss) at 2, 6 and 12 months, at 1 and 3 ticks, plus fees spent\n'
        '   and payouts received.', CODE),
      p('11.2 Key parameters', H2),
      Preformatted('Monte Carlo: 10,000 paths, seed 3, bankroll $12,000, horizons 42/126/252 trading days\n'
                   'Fees: Lucid 150K $265.30, 25K Pro $100 | FN 150K $259.99, 25K Pro $85\n'
                   '      MFF 150K $334, 25K $98\n'
                   'Start trigger: FN 150K, MFF 150K and MFF 25K at cash >= $30,000\n'
                   '25K funded size: 1.8 minis, halved to 0.9 after the first payout. 150K funded size = eval size', CODE)]

SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                  title='Prop-firm strategy', author='Research notes').build(S, onFirstPage=footer, onLaterPages=footer)
print('wrote', OUT)
