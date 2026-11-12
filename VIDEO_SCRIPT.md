# 3-minute video script (≈400 spoken words, stays under 3:00)

Record your screen with OBS, or with the Xbox Game Bar (Win+G).

**0:00–0:25 · Hook (show: a photo of a load-shedding schedule, or the title slide)**
> "Every summer in Pakistan, distribution companies like LESCO and K-Electric face a supply gap and must decide, hour by hour, which feeders go dark. Shed too little and the grid trips. Shed too much and paying customers suffer for nothing. Cut a hospital and people die. We asked: can a quantum algorithm build a fair load-shedding rotation?"

**0:25–1:00 · The problem (show: the feeder table and the four goals from the README)**
> "Our test case has 4 feeders over 3 evening hours, plus a protected hospital feeder. There are four rules. First, meet the megawatt deficit exactly. Second, prefer high-loss feeders, which is how Pakistan's loss-based load management works. Third, never cut the hospital. Fourth, for fairness, never cut the same feeder two hours in a row. Each yes/no decision, feeder f off in hour h, is one qubit. That's 12 qubits and 4,096 possible schedules, and only 2 are valid."

**1:00–1:35 · Formulation and algorithm (show: the architecture diagram)**
> "We remove the hospital feeder classically, so that rule can never be broken. The other three goals become a QUBO cost function. The deficit and fairness rules are penalties, and fairness is a natural two-qubit interaction. We map it to an Ising Hamiltonian in Qiskit and run QAOA: alternating cost and mixer layers, tuned by a classical optimiser. We use CVaR-QAOA, which optimises the best 10% of outcomes instead of the average."

**1:35–2:20 · Demo (show: the terminal running `python run_experiments.py --quick`, then the figures)**
> "Here's the code running. [show the output] The exact brute-force optimum is F2 and F4 at 6pm, F1 at 7pm, and F2 and F3 at 8pm. QAOA's best measured schedule is exactly that. [show fig_schedules] The greedy rule a control room might use cuts 40 megawatts at 7pm when only 30 were needed. [show fig_depth] As we add QAOA layers, the chance of measuring the optimum rises to about 5 percent, roughly 200 times better than random guessing. From depth 6 on, the most-measured schedule IS the optimum."

**2:20–2:50 · Honest limitations (show: the limitations section of the report)**
> "Now the honest part. A classical computer solves this in milliseconds, so there's no quantum speedup here. Even our best circuit hits the optimum in only a few percent of shots. At 15 qubits QAOA got much worse, because the penalties make the landscape rugged. On real noisy hardware, a depth-8 circuit wouldn't survive. Constraint-preserving mixers and splitting the problem by hour are our next steps."

**2:50–3:00 · Close**
> "Fair load-shedding is a real, daily optimisation problem, and it maps cleanly onto qubits. The code is on GitHub and fully reproducible. Thank you."

