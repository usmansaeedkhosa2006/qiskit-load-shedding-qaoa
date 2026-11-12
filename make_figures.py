"""Regenerate all report graphics in the report's colour theme.

    python make_figures.py

Needs results/results.json (from run_experiments.py).  Writes:
  results/fig_*.png         - themed result figures (histogram is re-sampled from the
                              saved QAOA angles with a fixed seed, so it is reproducible)
  report_assets/*.jpg|png   - cover art, statement page, back cover, icons
"""
import json
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle, Wedge, Arc

from loadshed import theme as T
from loadshed.instance import default_instance
from loadshed.qubo import build_qubo, qubo_to_ising, all_costs, bits_from_index
from loadshed.baselines import brute_force, greedy_rotation
from loadshed.qaoa import QAOASolver, qaoa_circuit
import run_experiments as RE

A = "report_assets"
os.makedirs(A, exist_ok=True)
R = json.load(open("results/results.json"))
W_IN, H_IN, DPI = 11.69, 8.27, 200  # A4 landscape


# ---------------------------------------------------------------- page art
def _canvas(bg, stripe):
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_IN * 72); ax.set_ylim(0, H_IN * 72); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), W_IN * 72, H_IN * 72, color=bg, zorder=0))
    for x in np.arange(-H_IN * 72, W_IN * 72, 3.2):  # fine diagonal texture
        ax.plot([x, x + H_IN * 72], [0, H_IN * 72], color=stripe, lw=0.5, alpha=0.18, zorder=1)
    return fig, ax


def _fit_text(fig, ax, x, y, s, max_w, size, **kw):
    t = ax.text(x, y, s, fontsize=size, fontfamily=T.HEAD_FONT, va="baseline", zorder=5, **kw)
    r = fig.canvas.get_renderer()
    w = t.get_window_extent(r).width * 72 / DPI
    if w > max_w:
        t.set_fontsize(size * max_w / w)
    return t


def _grid_motif(ax, color, x0, y0, w, h, seed=4):
    """Faint feeder-network motif: nodes joined by grid lines."""
    rng = np.random.default_rng(seed)
    pts = np.c_[rng.uniform(x0, x0 + w, 26), rng.uniform(y0, y0 + h, 26)]
    for i, p in enumerate(pts):
        d = np.linalg.norm(pts - p, axis=1)
        for j in np.argsort(d)[1:3]:
            ax.plot([p[0], p[0], pts[j][0]], [p[1], pts[j][1], pts[j][1]],
                    color=color, lw=1.0, alpha=0.55, zorder=2)
    ax.scatter(pts[:, 0], pts[:, 1], s=26, color=color, alpha=0.8, zorder=3)


def cover():
    fig, ax = _canvas(T.INK, "#6366F1")
    _grid_motif(ax, T.INK2, 500, 30, 330, 230)
    W = W_IN * 72
    lines = [("FAIR LOAD-SHEDDING", 40), ("WITH QUANTUM", 140), ("OPTIMISATION", 230)]
    y = 505
    for s, x in lines:
        _fit_text(fig, ax, x, y, s, W - x - 40, 96, color=T.AMBER)
        y -= 104
    # banner
    bx, by, bw, bh = 470, 150, 372, 44
    ax.add_patch(Polygon([[bx + 14, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh]],
                         color=T.AMBER, zorder=4))
    ax.text(bx + 34, by + 12, "HACKATHON REPORT", fontsize=28, fontfamily=T.HEAD_FONT,
            color=T.INK, zorder=5)
    ax.text(40, 92, "QISKIT FALL FEST 2026", fontsize=17, fontfamily=T.HEAD_FONT, color="white", zorder=5)
    ax.text(40, 70, "ENERGY & SMART INFRASTRUCTURE  ·  CVaR-QAOA IN QISKIT", fontsize=12,
            fontfamily=T.HEAD_FONT, color=T.AMBER_LIGHT, zorder=5)
    fig.savefig(f"{A}/cover.jpg", dpi=DPI, pil_kwargs={"quality": 90})
    plt.close(fig)


def statement():
    cv = R["qaoa_cvar"]
    best = max(cv, key=lambda r: r["p_opt"])
    amp = best["p_opt"] * R["instance"]["search_space"]
    fig, ax = _canvas(T.AMBER, "white")
    lines = [(f"{R['instance']['search_space']:,} POSSIBLE SCHEDULES.", T.INK),
             (f"ONLY {R['instance']['n_valid_schedules']} FOLLOW EVERY RULE.", T.INK),
             ("QAOA FOUND THE BEST ONE,", "white"),
             (f"~{amp:.0f}× MORE OFTEN THAN GUESSING.", "white")]
    y = 430
    for s, c in lines:
        _fit_text(fig, ax, 60, y, s, 720, 60, color=c)
        y -= 82
    ax.text(62, 70, f"Best of {best['shots']} shots at depth p = {best['p']} = exact optimum   ·   "
            f"{best['opt_hits_in_shots']} optimal shots   ·   12 qubits, Qiskit {('2.6')}",
            fontsize=12, color=T.INK, fontfamily="Calibri", weight="bold", zorder=5)
    fig.savefig(f"{A}/statement.jpg", dpi=DPI, pil_kwargs={"quality": 90})
    plt.close(fig)


def back_cover():
    fig, ax = _canvas(T.INK, "#6366F1")
    _grid_motif(ax, T.INK2, 40, 40, 780, 220, seed=9)
    _fit_text(fig, ax, 60, 440, "THANK YOU", 720, 140, color=T.AMBER)
    fig.savefig(f"{A}/back.jpg", dpi=DPI, pil_kwargs={"quality": 90})
    plt.close(fig)


# ---------------------------------------------------------------- icons
def _icon_axes(bg_circle=False):
    fig = plt.figure(figsize=(1.6, 1.6), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    if bg_circle:
        ax.add_patch(Circle((50, 50), 49, color=T.INK))
    return fig, ax


def _draw(ax, name, c, lw=6):
    k = dict(color=c, lw=lw, solid_capstyle="round")
    f = dict(fc="none", ec=c, lw=lw)
    if name == "target":
        for r in (36, 23, 10):
            ax.add_patch(Circle((50, 50), r, **f))
        ax.plot([50, 86], [50, 86], **k)
    elif name == "percent":
        ax.text(50, 47, "%", ha="center", va="center", fontsize=70, color=c, fontfamily=T.HEAD_FONT)
    elif name == "shield":
        ax.add_patch(Polygon([[50, 90], [82, 78], [78, 40], [50, 12], [22, 40], [18, 78]], closed=True, **f))
        ax.plot([50, 50], [34, 68], **k); ax.plot([34, 66], [51, 51], **k)
    elif name == "clock":
        ax.add_patch(Circle((50, 50), 36, **f)); ax.plot([50, 50, 70], [76, 50, 50], **k)
    elif name == "chip":
        ax.add_patch(Rectangle((28, 28), 44, 44, **f))
        for t in (38, 50, 62):
            ax.plot([t, t], [14, 28], **k); ax.plot([t, t], [72, 86], **k)
            ax.plot([14, 28], [t, t], **k); ax.plot([72, 86], [t, t], **k)
        ax.text(50, 49, "Q", ha="center", va="center", fontsize=28, color=c, fontfamily=T.HEAD_FONT)
    elif name == "wave":
        x = np.linspace(12, 88, 200); ax.plot(x, 50 + 22 * np.sin((x - 12) / 76 * 4 * np.pi) * np.exp(-(x - 12) / 120), **k)
    elif name == "layers":
        for y in (30, 48, 66):
            ax.add_patch(Polygon([[50, y + 14], [84, y], [50, y - 14], [16, y]], closed=True, **f))
    elif name == "loop":
        ax.add_patch(Arc((50, 50), 64, 64, theta1=20, theta2=170, **f))
        ax.add_patch(Arc((50, 50), 64, 64, theta1=200, theta2=350, **f))
        ax.add_patch(Polygon([[12, 60], [24, 50], [30, 66]], color=c))
        ax.add_patch(Polygon([[88, 40], [76, 50], [70, 34]], color=c))
    elif name == "nodes":
        P = [(25, 70), (75, 70), (25, 30), (75, 30), (50, 50)]
        for a in P[:4]:
            ax.plot([a[0], 50], [a[1], 50], **k)
        ax.plot([25, 75], [70, 70], **k); ax.plot([25, 75], [30, 30], **k)
        for p in P:
            ax.add_patch(Circle(p, 9, color=c))
    elif name == "fork":
        ax.plot([50, 50], [14, 48], **k); ax.plot([50, 22], [48, 82], **k); ax.plot([50, 78], [48, 82], **k)
        ax.plot([50, 50], [48, 86], color=c, lw=lw, ls=(0, (2, 2)))
    elif name == "hourglass":
        ax.add_patch(Polygon([[24, 86], [76, 86], [50, 50], [76, 14], [24, 14], [50, 50]], closed=True, **f))
        ax.add_patch(Polygon([[36, 20], [64, 20], [50, 36]], color=c))
    elif name == "dice":
        ax.add_patch(FancyBboxPatch((20, 20), 60, 60, boxstyle="round,pad=0,rounding_size=10", **f))
        for p in [(35, 65), (50, 50), (65, 35)]:
            ax.add_patch(Circle(p, 6, color=c))
    elif name == "sliders":
        for x, h in ((28, 64), (50, 34), (72, 52)):
            ax.plot([x, x], [16, 84], **k); ax.add_patch(Rectangle((x - 9, h - 6), 18, 12, color=c))
    elif name == "blocks":
        for i, (x, y) in enumerate([(16, 16), (44, 16), (72, 16), (30, 44), (58, 44), (44, 72)]):
            ax.add_patch(Rectangle((x, y), 24, 22, **dict(f, lw=4)))
    elif name == "database":
        for y in (72, 50, 28):
            ax.add_patch(Arc((50, y), 56, 18, theta1=180, theta2=360, **f))
        ax.add_patch(Circle((50, 72), 1, color=c)); ax.add_patch(Arc((50, 72), 56, 18, **f))
        ax.plot([22, 22], [28, 72], **k); ax.plot([78, 78], [28, 72], **k)
    elif name == "warning":
        ax.add_patch(Polygon([[50, 86], [88, 18], [12, 18]], closed=True, **f))
        ax.plot([50, 50], [40, 64], **k); ax.add_patch(Circle((50, 29), 4, color=c))
    elif name == "bolt":
        ax.add_patch(Polygon([[56, 90], [26, 46], [48, 46], [40, 10], [74, 56], [52, 56]], color=c))
    elif name == "house":
        ax.add_patch(Polygon([[14, 50], [50, 84], [86, 50]], closed=False, **f))
        ax.add_patch(Rectangle((26, 16), 48, 40, **f)); ax.add_patch(Rectangle((44, 16), 12, 20, color=c))
    elif name == "hospital":
        ax.add_patch(FancyBboxPatch((18, 18), 64, 64, boxstyle="round,pad=0,rounding_size=12", **f))
        ax.add_patch(Rectangle((43, 30), 14, 40, color=c)); ax.add_patch(Rectangle((30, 43), 40, 14, color=c))
    elif name == "scale":
        ax.plot([50, 50], [16, 82], **k); ax.plot([18, 82], [70, 70], **k); ax.plot([34, 66], [16, 16], **k)
        for x in (22, 78):
            ax.plot([x, x - 12], [70, 44], **dict(k, lw=3)); ax.plot([x, x + 12], [70, 44], **dict(k, lw=3))
            ax.add_patch(Wedge((x, 44), 14, 180, 360, color=c))
    elif name == "arrow":
        ax.plot([16, 76], [50, 50], **k); ax.add_patch(Polygon([[86, 50], [66, 66], [66, 34]], color=c))
    elif name == "split":
        for y in (22, 50, 78):
            ax.add_patch(Rectangle((58, y - 9), 26, 18, **dict(f, lw=4)))
            ax.plot([16, 40, 58], [50, 50, y], **dict(k, lw=4))
    elif name == "book":
        ax.add_patch(Polygon([[50, 22], [14, 30], [14, 82], [50, 74]], closed=True, **f))
        ax.add_patch(Polygon([[50, 22], [86, 30], [86, 82], [50, 74]], closed=True, **f))
    else:
        raise ValueError(name)


ICONS = ["target", "percent", "shield", "clock", "chip", "wave", "layers", "loop", "nodes", "fork",
         "hourglass", "dice", "sliders", "blocks", "database", "warning", "bolt", "house",
         "hospital", "scale", "arrow", "split", "book"]


def icons():
    for n in ICONS:
        fig, ax = _icon_axes()
        _draw(ax, n, "white")
        fig.savefig(f"{A}/icon_{n}.png", transparent=True); plt.close(fig)
        fig, ax = _icon_axes(bg_circle=True)
        ax.set_xlim(-18, 118); ax.set_ylim(-18, 118)
        ax.patches[0].set_radius(66); ax.patches[0].set_center((50, 50))
        _draw(ax, n, "white", lw=7)
        fig.savefig(f"{A}/circle_{n}.png", transparent=True); plt.close(fig)


def bracket():
    fig = plt.figure(figsize=(10.4, 0.35), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 10); ax.axis("off")
    xs = [12.5, 37.5, 62.5, 87.5]
    ax.plot([50, 50], [10, 6], color=T.MUTED, lw=1.5)
    ax.plot([xs[0], xs[-1]], [6, 6], color=T.MUTED, lw=1.5)
    for x in xs:
        ax.plot([x, x], [6, 0], color=T.MUTED, lw=1.5)
    fig.savefig(f"{A}/bracket.png", transparent=True); plt.close(fig)


# ---------------------------------------------------------------- result figures
def result_figures():
    inst = default_instance()
    Q, off = build_qubo(inst)
    x_opt, _, costs = brute_force(Q, off)
    cv = R["qaoa_cvar"]
    best = max(cv, key=lambda r: r["p_opt"])
    RE.plot_schedules(inst, [("Greedy loss-based rule", greedy_rotation(inst)),
                             (f"CVaR-QAOA (p={best['p']}) result", bits_from_index(best["best_sampled"], 12)),
                             ("Exact optimum (brute force)", x_opt)], "results/fig_schedules.png")
    RE.plot_depth(cv, R["qaoa_standard"], inst.n_qubits, "results/fig_depth.png")
    # re-sample the trained circuit (same seed as run_experiments -> same counts)
    _, h, J, _ = qubo_to_ising(Q, off)
    solver = QAOASolver(inst.n_qubits, h, J, costs)
    qc, g, b = qaoa_circuit(inst.n_qubits, h, J, best["p"], solver.scale)
    counts = solver.sample(qc, list(g) + list(b), np.array(best["theta"]), shots=best["shots"])
    assert counts.get(int(np.argmin(costs)), 0) == best["opt_hits_in_shots"], "re-sample mismatch"
    row = dict(best, _counts=counts)
    feas = RE.feasibility_mask(inst)
    RE.plot_histogram(inst, row, costs, int(np.argmin(costs)), feas, "results/fig_histogram.png")


if __name__ == "__main__":
    cover(); statement(); back_cover(); icons(); bracket()
    result_figures()
    subprocess.run([sys.executable, "make_architecture.py"], check=True)
    print("figures and report assets written")
