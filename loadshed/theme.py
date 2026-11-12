"""Shared colour palette and fonts for figures and the report."""
INK = "#1E1B4B"        # deep indigo: headings, dark tiles
INK2 = "#312E81"       # lighter indigo: texture, accents
AMBER = "#F59E0B"      # amber: banners, highlights
AMBER_LIGHT = "#FCD34D"
SOFT = "#EEF2FF"       # pale indigo: light panels
TEXT = "#1F2937"
MUTED = "#64748B"
TEAL = "#0F766E"       # protected feeders
LINE = "#CBD5E1"

HEAD_FONT = "Impact"
BODY_FONT = "Calibri"


def use_matplotlib_theme():
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": ["Calibri", "DejaVu Sans"],
        "axes.edgecolor": MUTED,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
