"""Build the hackathon report (Report.docx) from results/results.json and the figures.

    python make_report.py      (needs: pip install python-docx)
"""
import json
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

R = json.load(open("results/results.json"))
inst = R["instance"]
base = R["baselines"]
cv = R["qaoa_cvar"]
st = R["qaoa_standard"]
ans = R["qaoa_answer"]
big = R["scaling_15q"]
best = max(cv, key=lambda r: r["p_opt"])
N = inst["n_qubits"]
RAND = 1 / inst["search_space"]
HOURS = ["18:00", "19:00", "20:00"]

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Inches(0.9)
    s.top_margin = s.bottom_margin = Inches(0.8)
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(10.5)
normal.paragraph_format.space_after = Pt(6)
for lvl, size in ((1, 15), (2, 12)):
    hs = doc.styles[f"Heading {lvl}"]
    hs.font.name = "Calibri"
    hs.font.size = Pt(size)
    hs.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    hs.paragraph_format.space_before = Pt(12)
    hs.paragraph_format.space_after = Pt(4)
    hs.paragraph_format.keep_with_next = True


def P(text="", bold_lead=None, italic=False, size=None, align=None):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead).bold = True
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
    return p


def bullet(text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(text)
    return p


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def table(header, rows, widths=None, font=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(font)
        shade(c, "DCE6F0")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(v)).font.size = Pt(font)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def figure(path, caption, width=6.6):
    doc.add_picture(path, width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(caption, italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)


def sched_str(s):
    return "  |  ".join(f"{HOURS[int(h)]}: {'+'.join(v) or 'none'}" for h, v in s.items())


def pct(x, d=2):
    return f"{100 * x:.{d}f}%"


# ------------------------------------------------------------------ title
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Fair Load-Shedding Rotation with QAOA")
r.bold = True
r.font.size = Pt(20)
r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
P("Qiskit Fall Fest 2026 Hackathon  ·  Domain: Energy & Smart Infrastructure",
  align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
P("Team: [team name / members]   ·   Code: [GitHub link]   ·   Video: [Drive link]",
  align=WD_ALIGN_PARAGRAPH.CENTER, size=10, italic=True)

# ------------------------------------------------------------------ 1
doc.add_heading("1. Summary", 1)
P(f"Electricity distribution companies in Pakistan (e.g. LESCO, K-Electric) routinely face supply "
  f"shortfalls and must decide, hour by hour, which feeders to switch off. We formulate this as a "
  f"binary optimisation problem with competing goals: shed exactly the megawatt deficit, prefer "
  f"high-loss feeders (loss-based load management), never cut hospital and water-pumping feeders, "
  f"and never cut the same feeder in two consecutive hours. A 4-feeder × 3-hour instance becomes a "
  f"{N}-qubit QUBO that we solve with a CVaR-QAOA implemented in Qiskit 2.6, and compare against an "
  f"exact brute-force solver, a greedy rule of the kind used in practice, and simulated annealing.")
P(f"QAOA recovered the exact optimal schedule (best measured sample at p = {best['p']} was the true "
  f"optimum, {best['opt_hits_in_shots']} of {best['shots']} shots), raising the probability of "
  f"measuring the optimum from {pct(RAND, 3)} (random) to {pct(best['p_opt'])}, about "
  f"{best['p_opt'] / RAND:.0f}× amplification. From p = "
  f"{min(r['p'] for r in cv if r['most_frequent_is_opt'])} upward the single most frequently measured "
  f"schedule is the optimum. The greedy rule produced a schedule that over-sheds "
  f"{base['greedy_rule']['over_shed_mw']} MW. Classical solvers remain far faster at this size, and "
  f"QAOA's success probability fell sharply at 15 qubits. Both points are discussed honestly in Section 8.",
  bold_lead="Key result. ")

# ------------------------------------------------------------------ 2
doc.add_heading("2. Problem and who it serves", 1)
P("When generation cannot meet demand, a DISCO must shed load. Today this is commonly done with fixed "
  "rotation tables and loss-based categories: feeders with higher losses (theft, non-payment) get "
  "longer outages. Building these tables by hand for hundreds of feeders, every day, with changing "
  "deficits, is error-prone: operators either shed too little (risking frequency collapse and "
  "grid-wide tripping) or too much (unnecessary outages for paying customers), and fairness "
  "between neighbourhoods is hard to guarantee.")
P("Who it serves: ", bold_lead=None)
bullet("grid control-room operators, who need a valid rotation table quickly;", "Operators: ")
bullet("paying customers on low-loss feeders, who should be cut least;", "Consumers: ")
bullet("hospitals and water-pumping stations, which must never lose supply;", "Critical services: ")
bullet("the regulator, who wants a transparent and auditable rule.", "Regulator (NEPRA): ")

# ------------------------------------------------------------------ 3
doc.add_heading("3. Formulation", 1)
doc.add_heading("3.1 Test instance", 2)
rows = []
for f in inst["feeders"]:
    rows.append([f["name"], f["kind"], f["load_mw"], f"{int(f['loss_rate'] * 100)}%",
                 "PROTECTED (never shed)" if f["protected"] else "sheddable"])
table(["Feeder", "Type", "Load (MW)", "Loss rate", "Status"], rows, [0.6, 2.3, 0.8, 0.8, 1.9])
P(f"Hourly deficits: {', '.join(f'{h} → {d} MW' for h, d in zip(HOURS, inst['deficits_mw']))}. "
  f"All data are illustrative (hypothetical feeders), chosen to resemble a DISCO evening peak. "
  f"Search space: 2^{N} = {inst['search_space']} schedules, of which only "
  f"{inst['n_valid_schedules']} satisfy every rule exactly. That makes this a needle-in-a-haystack instance.")

doc.add_heading("3.2 Decision variables", 2)
P("x[f,h] ∈ {0,1} equals 1 if sheddable feeder f is switched off during hour h. With 4 sheddable "
  "feeders and 3 hours this gives 12 binary variables, i.e. 12 qubits. The protected feeder F5 is "
  "removed before the quantum step: a hard rule enforced classically costs zero qubits and can "
  "never be violated.")

doc.add_heading("3.3 Objective and constraints", 2)
P("minimise  C(x) = Σ_f,h c_f·x[f,h]  +  A·Σ_h (Σ_f L_f·x[f,h] − D_h)²  +  B·Σ_f Σ_h x[f,h]·x[f,h+1]",
  bold_lead=None).runs[0].font.name = "Consolas"
bullet("c_f = L_f·(1 − loss_f) is the MW of paying customers cut. Shedding a high-loss feeder "
       "costs less per MW, which reproduces loss-based load management as a soft objective.",
       "Harm term: ")
bullet("A·(shed − deficit)² penalises both under-shedding (grid risk) and over-shedding "
       "(needless outages). Loads are in 10 MW blocks; A = 3.", "Deficit constraint: ")
bullet("B·x[f,h]·x[f,h+1] is a pairwise penalty, the natural form for qubits (one ZZ "
       "interaction per pair); B = 3.", "Fairness constraint: ")
bullet("removed in pre-processing (x fixed to 0).", "Protected feeders: ")
P("Penalty weights were checked by brute force: the global minimum of C(x) is a schedule that "
  "satisfies every constraint, and the cheapest rule-breaking schedule costs more than the most "
  "expensive valid one. Substituting x = (1 − Z)/2 gives an Ising Hamiltonian with 12 single-Z and "
  "26 ZZ terms, built as a qiskit SparsePauliOp. A unit test checks that its diagonal equals C(x) "
  "for all 4096 states.")

# ------------------------------------------------------------------ 4
doc.add_heading("4. Why QAOA", 1)
bullet("The problem is natively a QUBO with only linear and pairwise terms, exactly the structure "
       "QAOA's cost layer (RZ and RZZ gates) implements.", "Natural fit: ")
bullet("Every measurement is directly a candidate rotation table, so the quantum output is the "
       "solution itself, not a side calculation.", "Quantum does the real work: ")
bullet("Shallow circuits plus a classical optimiser suit today's noisy hardware and run on a laptop "
       "simulator at 12–15 qubits.", "NISQ-friendly: ")
bullet("We optimise CVaR (the mean cost of the best 10% of outcomes) instead of the plain "
       "expectation, because for optimisation we care about the best samples, not the average "
       "(Barkoutsos et al., Quantum 2020). Depth is grown with INTERP warm-starts (Zhou et al., "
       "PRX 2020).", "Design choices: ")
P("Alternatives considered: VQE with a hardware-efficient ansatz (more parameters, no problem "
  "structure); Grover adaptive search (needs deep circuits and an oracle); quantum annealing "
  "(not available in Qiskit).")

# ------------------------------------------------------------------ 5
doc.add_heading("5. Architecture", 1)
figure("results/fig_architecture.png",
       "Figure 1. Solution architecture: classical pre-processing → QUBO/Ising → hybrid QAOA loop → "
       "sampling → validation against classical baselines.")

# ------------------------------------------------------------------ 6
doc.add_heading("6. Implementation", 1)
bullet("instance.py: feeder data; qubo.py: QUBO builder, Ising mapping, schedule metrics; "
       "qaoa.py: QAOA circuit, CVaR, COBYLA loop, Qiskit Sampler; baselines.py: brute force, greedy "
       "rule, simulated annealing; run_experiments.py: everything end to end.", "Code layout: ")
bullet("Qiskit 2.6.2 (QuantumCircuit, ParameterVector, SparsePauliOp, Statevector, "
       "StatevectorSampler, transpile, GenericBackendV2), SciPy COBYLA, NumPy, Matplotlib.", "Stack: ")
bullet(f"p = 1…{R['config']['p_max']}, {R['config']['restarts']} restarts, ≤{R['config']['maxiter']} "
       f"COBYLA iterations each, {R['config']['shots']} shots for the final sample.", "Settings: ")
bullet("During training the QAOA state is computed with an equivalent NumPy routine (a diagonal "
       "phase plus RX on every qubit), because rebuilding the Qiskit circuit on every optimiser call "
       "was too slow. A test verifies it agrees with qiskit.quantum_info.Statevector to 1e-16. All "
       "reported probabilities and samples come from the actual Qiskit circuit.", "Honesty note: ")
cs = R["circuit"]
crow = [[k, v["logical_2q_gates"], v["transpiled_cz"], v["transpiled_depth"]] for k, v in cs.items()]
P("Circuit cost when compiled to a 3×4 grid device with native {CZ, RZ, SX, X} gates:")
table(["Depth", "RZZ gates (logical)", "CZ after transpile", "Transpiled depth"], crow, [1.0, 1.6, 1.6, 1.6])

# ------------------------------------------------------------------ 7
doc.add_heading("7. Results and classical comparison", 1)
doc.add_heading("7.1 Schedules", 2)
rows = []
for name, key in (("Exact (brute force, 4096 states)", "exact_bruteforce"),
                  ("Greedy loss-based rule", "greedy_rule"),
                  ("Simulated annealing", "simulated_annealing")):
    b = base[key]
    rows.append([name, sched_str(b["schedule"]), round(b["cost"], 2), b["over_shed_mw"],
                 b["unmet_mw"], b["back_to_back_cuts"], "yes" if b["feasible"] else "no"])
rows.append([f"CVaR-QAOA (p={ans['p']}, best sample)", sched_str(ans["schedule"]),
             round(best["best_sampled_cost"], 2), ans["over_shed_mw"], ans["unmet_mw"],
             ans["back_to_back_cuts"], "yes" if ans["feasible"] else "no"])
table(["Method", "Feeders OFF per hour", "QUBO cost", "Over-shed MW", "Unmet MW", "Back-to-back",
       "Valid"], rows, [1.4, 2.5, 0.6, 0.6, 0.6, 0.6, 0.5], font=8)
figure("results/fig_schedules.png",
       "Figure 2. Rotation tables. The greedy rule cuts F2+F3 at 19:00 (40 MW for a 30 MW deficit). "
       "QAOA and the exact solver find a schedule that meets every deficit exactly with no "
       "back-to-back cuts.")
P(f"Interpretation: the optimum sheds the high-loss feeder F1 at the 19:00 peak and rotates the "
  f"others around it. Paying-customer MW cut: {base['exact_bruteforce']['paying_mw_cut']} (optimal) "
  f"vs {base['greedy_rule']['paying_mw_cut']} (greedy), and the greedy plan also blacks out "
  f"{base['greedy_rule']['over_shed_mw']} MW more than needed.")

doc.add_heading("7.2 QAOA performance vs depth", 2)
rows = []
for r, s in zip(cv, st):
    rows.append([r["p"], pct(r["p_opt"]), f"{r['p_opt'] / RAND:.0f}×", pct(r["p_feasible"]),
                 f"{r['approx_ratio']:.3f}", f"{r['opt_hits_in_shots']}/{r['shots']}",
                 "yes" if r["best_sampled_is_opt"] else "no", pct(s["p_opt"])])
table(["p", "P(optimum)", "vs random", "P(valid)", "Approx. ratio", "Optimum hits",
       "Best sample = opt?", "Standard QAOA P(opt)"], rows, [0.4, 0.8, 0.8, 0.8, 0.8, 0.9, 0.9, 1.0], font=8)
figure("results/fig_depth.png",
       "Figure 3. Probability of measuring the optimal (left) and any valid (right) schedule vs QAOA "
       "depth, log scale. The dotted line is uniform random guessing.")
figure("results/fig_histogram.png",
       f"Figure 4. Most frequent measured schedules at p = {best['p']}. Dark red = optimal, "
       "pink = valid, grey = breaks a rule.")

doc.add_heading("7.3 Scaling check (15 qubits)", 2)
rows = [[r["p"], pct(r["p_opt"], 3), pct(r["p_feasible"], 3),
         "yes" if r["best_sampled_is_opt"] else "no"] for r in big["qaoa_cvar"]]
table(["p", "P(optimum)", "P(valid)", "Best sample = opt?"], rows, [0.6, 1.4, 1.4, 1.6])
P(f"Adding one feeder (5 × 3 = 15 qubits, 32,768 states, {big['n_valid_schedules']} valid) made "
  f"QAOA noticeably worse at the depths we could afford. This is a known weakness of penalty-based "
  f"QAOA and is the main limitation of this work.")

# ------------------------------------------------------------------ 8
doc.add_heading("8. Limitations (honest assessment)", 1)
bullet("Brute force solves the 12-qubit instance in milliseconds and simulated annealing finds the "
       "optimum instantly. A real DISCO with hundreds of feeders would use MILP solvers. We claim no "
       "speedup.", "No quantum advantage: ")
bullet(f"Even at the best depth only {pct(best['p_opt'])} of shots are optimal. We rely on taking "
       "the best of many samples, which is fine at 4096 states but scales poorly.",
       "Low success probability: ")
bullet("Penalties for the deficit and fairness constraints create a rugged landscape with a huge "
       "cost range (7.7 to 240). A and B were hand-tuned, and different values change QAOA "
       "performance. Constraint-preserving mixers (XY-mixers) would be better but were out of scope.",
       "Penalty tuning: ")
bullet("The squared deficit penalty requires sheds to match deficits exactly in 10 MW blocks. Real "
       "deficits would need a slack-variable inequality, adding qubits.", "Equality approximation: ")
bullet("We used a noiseless statevector simulator. On real hardware the p = 8 circuit (hundreds of "
       "CZ gates after routing) would be overwhelmed by noise.", "Noiseless simulation: ")
bullet("The single-p, multi-restart COBYLA loop is a classical bottleneck: thousands of circuit "
       "evaluations per depth.", "Training cost: ")
bullet("Feeder data are illustrative, not from a utility. The model ignores network topology, "
       "voltage limits, and customer counts per feeder.", "Data realism: ")
bullet("At 15 qubits QAOA saw the optimum only once in 2048 shots (p = 3 and 4) and never at "
       "p = 1–2. Standard (expectation-based) QAOA was worse than CVaR at every depth except p = 2, "
       "and at p = 1 it essentially never produced a valid schedule.", "What didn't work: ")

doc.add_heading("9. Future work", 1)
bullet("XY / constraint-preserving mixers so the fairness rule is never violated.")
bullet("Decompose by hour or by grid station so each quantum sub-problem stays small.")
bullet("Warm-start QAOA from the greedy schedule; test on IBM hardware with error mitigation.")
bullet("Add customer counts, feeder priority classes and multi-day fairness (total hours shed).")

doc.add_heading("10. Reproducibility and credits", 1)
P("python -m venv .venv  →  pip install -r requirements.txt  →  python run_experiments.py "
  f"(≈{R['runtime_seconds'] / 60:.0f} min). All seeds are fixed. Results are written to results/.")
P("All code was written by the team for this hackathon. Algorithmic ideas are credited: QAOA "
  "(Farhi, Goldstone & Gutmann, arXiv:1411.4028, 2014); CVaR objective (Barkoutsos et al., "
  "Quantum 4, 256, 2020); INTERP initialisation (Zhou et al., Phys. Rev. X 10, 021067, 2020); "
  "QUBO penalty formulations (Lucas, Front. Phys. 2, 5, 2014). Software: Qiskit, SciPy, NumPy, "
  "Matplotlib.")

doc.save("Report.docx")
print("saved Report.docx")
