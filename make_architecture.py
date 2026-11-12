"""Draw the solution architecture diagram -> results/fig_architecture.png"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

os.makedirs("results", exist_ok=True)
fig, ax = plt.subplots(figsize=(12, 6.4))
ax.set_xlim(0, 12); ax.set_ylim(0, 6.4); ax.axis("off")

CLASSICAL, QUANTUM, CHECK = "#e3f2fd", "#fce4ec", "#e8f5e9"


def box(x, y, w, h, title, body, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc=color, ec="#37474f", lw=1.2))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=9.5, weight="bold")
    ax.text(x + w / 2, y + h - 0.55, body, ha="center", va="top", fontsize=7.8, linespacing=1.35)


def arrow(x1, y1, x2, y2, label="", curve=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#37474f",
                                connectionstyle=f"arc3,rad={curve}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", fontsize=7.5, style="italic")


# row 1: classical pre-processing
box(0.2, 4.2, 2.3, 1.9, "1. Grid data", "feeder loads (MW)\nloss rates (%)\nhourly deficit (MW)\nprotected feeders", CLASSICAL)
box(2.9, 4.2, 2.4, 1.9, "2. Pre-processing", "drop protected feeders\n(hospital, water) =\nhard rule, 0 qubits\nscale MW -> 10 MW blocks", CLASSICAL)
box(5.7, 4.2, 2.6, 1.9, "3. QUBO model", "x[f,h] in {0,1}\nharm  +  A·(deficit gap)²\n+  B·(back-to-back cuts)\n12 binary variables", CLASSICAL)
box(8.7, 4.2, 3.1, 1.9, "4. Ising Hamiltonian", "x = (1 - Z)/2\nH = Σ hᵢZᵢ + Σ JᵢⱼZᵢZⱼ\nqiskit SparsePauliOp\n12 Z + 26 ZZ terms", CLASSICAL)

# row 2: hybrid loop
box(6.3, 1.5, 3.0, 2.1, "5. QAOA circuit (Qiskit)", "H on 12 qubits\nrepeat p times:\n  cost layer  RZZ / RZ (γ)\n  mixer layer RX (β)\nmeasure", QUANTUM)
box(2.6, 1.5, 3.0, 2.1, "6. Classical optimiser", "COBYLA (SciPy)\nminimise CVaR₀.₁ of cost\nINTERP warm start p -> p+1\n10 random restarts", CLASSICAL)
box(9.8, 1.5, 2.0, 2.1, "7. Sampler", "StatevectorSampler\n2048 shots\n-> schedule\ncandidates", QUANTUM)

# row 3: evaluation
box(0.2, 0.15, 2.0, 2.5, "9. Output", "load-shedding\nrotation table\n(feeder x hour)\nfor control room", CHECK)
box(2.6, 0.15, 7.0, 1.0, "8. Evaluation vs classical baselines",
    "exact brute force (4096 states)  ·  greedy loss-based rule  ·  simulated annealing", CHECK)

arrow(2.5, 5.15, 2.9, 5.15)
arrow(5.3, 5.15, 5.7, 5.15)
arrow(8.3, 5.15, 8.7, 5.15)
arrow(10.25, 4.2, 8.6, 3.6, "H_C")
arrow(6.3, 2.85, 5.6, 2.85, "CVaR(γ,β)")
arrow(5.6, 2.15, 6.3, 2.15, "new γ, β")
arrow(9.3, 2.5, 9.8, 2.5, "trained")
arrow(10.8, 1.5, 9.6, 0.75)
arrow(2.6, 0.65, 2.2, 0.9)

ax.text(4.1, 3.85, "hybrid quantum-classical loop", fontsize=8, color="#ad1457", ha="center")
ax.legend(handles=[matplotlib.patches.Patch(fc=CLASSICAL, ec="#37474f", label="classical"),
                   matplotlib.patches.Patch(fc=QUANTUM, ec="#37474f", label="quantum (simulated)"),
                   matplotlib.patches.Patch(fc=CHECK, ec="#37474f", label="validation / output")],
          loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=3, fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("results/fig_architecture.png", dpi=180)
print("saved results/fig_architecture.png")
