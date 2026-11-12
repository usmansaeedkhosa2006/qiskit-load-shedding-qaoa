"""Run the full study: formulation -> QAOA (Qiskit) -> classical baselines -> figures.

    python run_experiments.py            # full run (~3-5 min on a laptop)
    python run_experiments.py --quick    # smoke test (~30 s)
"""
import argparse
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap

from loadshed.instance import default_instance, large_instance
from loadshed.qubo import (build_qubo, all_costs, qubo_to_ising, decode, bits_from_index,
                           evaluate_schedule, qubo_value)
from loadshed.qaoa import QAOASolver
from loadshed.baselines import brute_force, greedy_rotation, simulated_annealing

OUT = "results"


def feasibility_mask(inst):
    return np.array([evaluate_schedule(inst, bits_from_index(k, inst.n_qubits))["feasible"]
                     for k in range(2 ** inst.n_qubits)])


def run_qaoa(inst, alpha, p_max, restarts, maxiter, shots, seed=7):
    Q, off = build_qubo(inst)
    _, h, J, _ = qubo_to_ising(Q, off)
    costs = all_costs(Q, off)
    k_opt = int(np.argmin(costs))
    feas = feasibility_mask(inst)
    solver = QAOASolver(inst.n_qubits, h, J, costs, alpha=alpha, maxiter=maxiter,
                        restarts=restarts, seed=seed)
    hist = solver.train(p_max=p_max)
    rows = []
    for p, r in hist.items():
        # exact distribution of the real Qiskit circuit at the trained angles
        probs = solver.qiskit_probs(r["circuit"], r["params"], r["theta"])
        counts = solver.sample(r["circuit"], r["params"], r["theta"], shots=shots)
        most_freq = max(counts, key=counts.get)
        best_sampled = min(counts, key=lambda k: costs[k])
        e = float(probs @ costs)
        rows.append({
            "p": p,
            "p_opt": float(probs[k_opt]),
            "p_feasible": float(probs[feas].sum()),
            "expected_cost": e,
            "approx_ratio": (costs.max() - e) / (costs.max() - costs.min()),
            "shots": shots,
            "opt_hits_in_shots": int(counts.get(k_opt, 0)),
            "most_frequent": int(most_freq),
            "most_frequent_is_opt": most_freq == k_opt,
            "best_sampled": int(best_sampled),
            "best_sampled_cost": float(costs[best_sampled]),
            "best_sampled_is_opt": best_sampled == k_opt,
            "optimizer_evals": r["evals"],
            "train_seconds": round(r["seconds"], 2),
            "theta": [float(t) for t in r["theta"]],
            "_counts": counts,
            "_circuit": r["circuit"],
        })
    return rows, costs, k_opt, feas


def circuit_stats(qc, n):
    backend = GenericBackendV2(num_qubits=n, basis_gates=["cz", "rz", "sx", "x"],
                               coupling_map=CouplingMap.from_grid(3, int(np.ceil(n / 3))).get_edges(),
                               seed=1)
    bound = qc.assign_parameters([0.1] * qc.num_parameters)
    t = transpile(bound, backend, optimization_level=3, seed_transpiler=1)
    ops = t.count_ops()
    return {"logical_2q_gates": bound.count_ops().get("rzz", 0),
            "transpiled_depth": t.depth(),
            "transpiled_cz": int(ops.get("cz", 0))}


def schedule_table(inst, x):
    return [[int(x[inst.var_index(f, h)]) for h in range(inst.n_hours)]
            for f in range(inst.n_feeders)]


def plot_schedules(inst, panels, path):
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.4))
    names = [f"{f.name}  ({f.kind}, loss {int(f.loss_rate*100)}%)" for f in inst.feeders]
    for ax, (title, x) in zip(axes, panels):
        grid = []
        for feeder in inst.feeders:
            if feeder.protected:
                grid.append([-1] * inst.n_hours)
            else:
                f = inst.sheddable.index(feeder)
                grid.append([x[inst.var_index(f, h)] for h in range(inst.n_hours)])
        grid = np.array(grid)
        cmap = matplotlib.colors.ListedColormap(["#2e7d32", "#e8eef3", "#c62828"])
        ax.imshow(grid, cmap=cmap, vmin=-1, vmax=1)
        ev = evaluate_schedule(inst, x)
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                lab = {-1: "never", 0: "on", 1: "OFF"}[grid[i, j]]
                ax.text(j, i, lab, ha="center", va="center", fontsize=8,
                        color="white" if grid[i, j] != 0 else "#333")
        ax.set_xticks(range(inst.n_hours), inst.hour_labels)
        ax.set_yticks(range(len(names)), names if ax is axes[0] else [""] * len(names), fontsize=8)
        sub = (f"shed {ev['shed_mw']} MW vs need {inst.deficits_mw}\n"
               f"over-shed {ev['over_shed_mw']} MW, back-to-back {ev['back_to_back_cuts']}")
        ax.set_title(f"{title}\n{sub}", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_depth(rows_cvar, rows_exp, n, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    ps = [r["p"] for r in rows_cvar]
    axes[0].plot(ps, [100 * r["p_opt"] for r in rows_cvar], "o-", label="CVaR-QAOA (α=0.1)")
    axes[0].plot([r["p"] for r in rows_exp], [100 * r["p_opt"] for r in rows_exp], "s--",
                 label="standard QAOA (expectation)")
    axes[0].axhline(100 / 2 ** n, color="grey", ls=":", label=f"random guess (1/{2**n})")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("QAOA depth p"); axes[0].set_ylabel("P(optimal schedule) %")
    axes[0].legend(fontsize=8); axes[0].set_title("Probability of measuring the optimum", fontsize=10)
    axes[1].plot(ps, [100 * r["p_feasible"] for r in rows_cvar], "o-", label="CVaR-QAOA (α=0.1)")
    axes[1].plot([r["p"] for r in rows_exp], [100 * r["p_feasible"] for r in rows_exp], "s--",
                 label="standard QAOA")
    axes[1].axhline(100 * 2 / 2 ** n, color="grey", ls=":", label="random guess")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("QAOA depth p"); axes[1].set_ylabel("P(valid schedule) %")
    axes[1].legend(fontsize=8); axes[1].set_title("Probability of a constraint-satisfying schedule", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def plot_histogram(inst, row, costs, k_opt, feas, path, top=15):
    counts = row["_counts"]
    items = sorted(counts.items(), key=lambda kv: -kv[1])[:top]
    labels, vals, colors = [], [], []
    for k, c in items:
        sched = decode(inst, bits_from_index(k, inst.n_qubits))
        labels.append(" | ".join("+".join(v) or "-" for v in sched.values()))
        vals.append(c)
        colors.append("#c62828" if k == k_opt else ("#ef9a9a" if feas[k] else "#90a4ae"))
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.barh(range(len(vals))[::-1], vals, color=colors)
    ax.set_yticks(range(len(vals))[::-1], labels, fontsize=7)
    ax.set_xlabel(f"counts out of {row['shots']} shots")
    ax.set_title(f"Top {top} measured schedules at p={row['p']}  "
                 "(dark red = optimal, pink = valid, grey = violates a rule)\n"
                 "label = feeders OFF at 18:00 | 19:00 | 20:00", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def strip(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    cfg = dict(p_max=3, restarts=2, maxiter=150, shots=1024) if args.quick else \
        dict(p_max=8, restarts=10, maxiter=400, shots=2048)
    t0 = time.time()
    summary = {"config": cfg}

    # ---------- main instance ----------
    inst = default_instance()
    Q, off = build_qubo(inst)
    print(f"Instance: {inst.n_feeders} sheddable feeders x {inst.n_hours} hours = {inst.n_qubits} qubits")
    x_opt, c_opt, costs = brute_force(Q, off)
    x_greedy = greedy_rotation(inst)
    x_sa, c_sa = simulated_annealing(Q, off)
    feas = feasibility_mask(inst)
    summary["instance"] = {
        "feeders": [vars(f) for f in inst.feeders],
        "deficits_mw": inst.deficits_mw,
        "n_qubits": inst.n_qubits,
        "search_space": 2 ** inst.n_qubits,
        "n_valid_schedules": int(feas.sum()),
    }
    summary["baselines"] = {
        "exact_bruteforce": {"cost": c_opt, "schedule": decode(inst, x_opt), **evaluate_schedule(inst, x_opt)},
        "greedy_rule": {"cost": qubo_value(Q, off, x_greedy), "schedule": decode(inst, x_greedy),
                        **evaluate_schedule(inst, x_greedy)},
        "simulated_annealing": {"cost": c_sa, "schedule": decode(inst, x_sa), **evaluate_schedule(inst, x_sa)},
    }
    print("Exact optimum:", decode(inst, x_opt), "cost", round(c_opt, 3))
    print("Greedy rule  :", decode(inst, x_greedy), evaluate_schedule(inst, x_greedy))

    print("Training CVaR-QAOA ...")
    rows_cvar, costs, k_opt, feas = run_qaoa(inst, 0.1, **cfg)
    print("Training standard QAOA ...")
    rows_exp, *_ = run_qaoa(inst, 1.0, **cfg)
    for r in rows_cvar:
        print(f"  p={r['p']}: P(opt)={r['p_opt']:.4f}  P(valid)={r['p_feasible']:.4f}  "
              f"approx_ratio={r['approx_ratio']:.3f}  best-sampled-is-opt={r['best_sampled_is_opt']}")
    best = max(rows_cvar, key=lambda r: r["p_opt"])
    x_q = bits_from_index(best["best_sampled"], inst.n_qubits)
    summary["qaoa_cvar"] = strip(rows_cvar)
    summary["qaoa_standard"] = strip(rows_exp)
    summary["qaoa_answer"] = {"p": best["p"], "schedule": decode(inst, x_q), **evaluate_schedule(inst, x_q),
                              "matches_exact": best["best_sampled"] == k_opt}
    summary["circuit"] = {f"p={r['p']}": circuit_stats(r["_circuit"], inst.n_qubits)
                          for r in rows_cvar if r["p"] in (1, best["p"])}

    plot_schedules(inst, [("Greedy loss-based rule", x_greedy),
                          (f"CVaR-QAOA (p={best['p']}) result", x_q),
                          ("Exact optimum (brute force)", x_opt)],
                   os.path.join(OUT, "fig_schedules.png"))
    plot_depth(rows_cvar, rows_exp, inst.n_qubits, os.path.join(OUT, "fig_depth.png"))
    plot_histogram(inst, best, costs, k_opt, feas, os.path.join(OUT, "fig_histogram.png"))

    # ---------- scaling check: 15 qubits ----------
    big = large_instance()
    print(f"Scaling check: {big.n_qubits} qubits ...")
    Qb, ob = build_qubo(big)
    xb, cb, _ = brute_force(Qb, ob)
    big_cfg = dict(cfg, p_max=min(cfg["p_max"], 4), restarts=max(2, cfg["restarts"] // 3))
    rows_big, *_ = run_qaoa(big, 0.1, **big_cfg)
    summary["scaling_15q"] = {"exact": {"cost": cb, "schedule": decode(big, xb)},
                              "n_valid_schedules": int(feasibility_mask(big).sum()),
                              "qaoa_cvar": strip(rows_big)}
    for r in rows_big:
        print(f"  15q p={r['p']}: P(opt)={r['p_opt']:.4f}  P(valid)={r['p_feasible']:.4f}")

    summary["runtime_seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"Done in {summary['runtime_seconds']} s. Results in ./{OUT}/")


if __name__ == "__main__":
    main()
