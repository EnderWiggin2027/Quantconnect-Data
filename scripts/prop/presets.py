"""Portfolio B loop presets. (start minute ET, stop pts, target pts, daily profit cap pts). Points are ES index points."""
PRESETS = {
    "eval_1":   (600, 8, 8, 6),    "eval_2":   (660, 8, 8, 6),    "eval_3":   (600, 12, 12, 10),
    "eval_4":   (660, 12, 12, 6),  "eval_5":   (780, 8, 8, 6),
    "funded_1": (600, 12, 8, 6),   "funded_2": (660, 12, 8, 6),   "funded_3": (600, 8, 8, 6),
    "funded_4": (600, 12, 12, 6),  "funded_5": (600, 8, 20, 6),
}
NAMES = list(PRESETS)
MAX_TRADES, DIR_TIME, LAST_ENTRY, FLAT_TIME = 8, 600, 930, 959   # minutes after midnight ET (bar END times)
