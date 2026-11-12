# 3-minute video script: Team Winners (Usman Saeed & Ali Saeed)

354 spoken words, about 2:45 at a calm pace. A formatted version with page thumbnails is in `VIDEO_SCRIPT.pdf`.
**SHOW** gives the `Report.pdf` page to have on screen while you speak each segment.

Before you record:
- Open `Report.pdf` full-screen.
- Run `python run_experiments.py --quick` so its output is ready to show.
- Record at 1080p with OBS or the Xbox Game Bar (Win+G), and keep it under 3:00.

| Time | SHOW | SAY |
|---|---|---|
| 0:00–0:15 | **p.1** Cover | "Hi, we're Team Winners: Usman Saeed and Ali Saeed. Our project is fair load-shedding with quantum optimisation." |
| 0:15–0:40 | **p.4** The Challenge (point at the "Our test grid" sidebar) | "Every summer, Pakistani distribution companies like LESCO and K-Electric face a supply gap and must decide, hour by hour, which feeders go dark. Shed too little and the grid trips. Shed too much and paying customers suffer for nothing. And a hospital must never lose power." |
| 0:40–1:05 | **p.7** The Four Rules, then **p.2** (the amber statement page) at "twelve qubits" | "We turned this into four rules: meet the megawatt deficit exactly, prefer high-loss feeders the way Pakistan's loss-based load management does, never cut critical loads, and never cut the same feeder two hours in a row. Our test case has four feeders over three evening hours. Each yes-or-no decision is one qubit: twelve qubits, 4,096 possible schedules, and only two follow every rule." |
| 1:05–1:35 | **p.6** From Grid to Qubits, then **p.9** Architecture (trace the loop) | "The hospital feeder is removed classically, so that rule can never break. The other rules become a QUBO cost function: the deficit and fairness rules are penalties, and fairness is a natural two-qubit interaction. We map it to an Ising Hamiltonian in Qiskit and run QAOA: alternating cost and mixer layers, tuned by a classical optimiser. We use CVaR-QAOA, which focuses on the best ten percent of outcomes." |
| 1:35–2:15 | **Terminal** output, then **p.11** schedules, **p.12** depth chart, **p.13** tall amber bar | "Here's our code running. The exact optimum sheds F2 and F4 at six, F1 at seven, and F2 and F3 at eight, and QAOA's best measured schedule is exactly that. The greedy rule a control room might use cuts forty megawatts at seven when only thirty were needed. As we add QAOA layers, the chance of measuring the optimum climbs to about five percent, roughly two hundred times better than guessing, and from depth six the most-measured schedule is the optimum." |
| 2:15–2:45 | **p.14** The Limits (tiles 1, 8, 5) | "Now the honest part. A classical computer solves this in milliseconds, so there's no quantum speedup here. At fifteen qubits QAOA almost never found the optimum, because the penalties make the landscape rugged. And on real noisy hardware, a depth-eight circuit with over seven hundred two-qubit gates wouldn't survive." |
| 2:45–3:00 | **p.15** Next steps, end on **p.16** Thank You | "Next we'd try constraint-preserving mixers and split the problem by hour. Fair load-shedding is a real, daily problem that maps cleanly onto qubits. Our code is on GitHub. Thank you!" |

After recording:
1. Upload to Google Drive and set Share to "Anyone with the link".
2. Paste the link into the report (cover and back page) and into the submission form.
3. Open it in a private window to check that it plays.
