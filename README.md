# Fair Load-Shedding Rotation with QAOA

**Qiskit Fall Fest 2026 Hackathon · Domain: Energy & Smart Infrastructure**

When a power distribution company (like LESCO or K-Electric) faces a supply shortfall, it has to decide which feeders to switch off each hour. We turn that decision into a 12-qubit QUBO and solve it with a CVaR-QAOA written in Qiskit, then check the answer against an exact solver and a greedy rule of the kind used in practice.

| Goal | How it is modelled |
|---|---|
| Shed exactly the MW deficit each hour | quadratic penalty `A·(shed − deficit)²` |
| Prefer high-loss feeders (loss-based load management) | linear cost `load × (1 − loss rate)` |
| Never cut hospital / water-pumping feeders | removed before the quantum step (0 qubits) |
| Fairness: no feeder is cut two hours in a row | pairwise penalty `B·x[f,h]·x[f,h+1]` |

Test instance: 4 sheddable feeders × 3 evening hours = **12 qubits** (4096 schedules, only 2 of which are valid). A 15-qubit instance is used as a scaling check.

## Setup (≈2 minutes)

Requires Python 3.10+ (tested on 3.14, Windows 11).

```bash
git clone https://github.com/usmansaeedkhosa2006/qiskit-load-shedding-qaoa.git
cd qiskit-load-shedding-qaoa
python -m venv .venv
# Windows:   .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m tests.test_formulation   # checks the Ising mapping and penalty weights
python run_experiments.py --quick  # smoke test, ~30 s
python run_experiments.py          # full study, a few minutes
python make_architecture.py        # redraws the architecture diagram
```

Outputs go to `results/`:
- `results.json` holds all the numbers.
- `fig_schedules.png` compares the greedy, QAOA and exact rotation tables.
- `fig_depth.png` plots success probability against QAOA depth.
- `fig_histogram.png` shows the most-measured schedules.
- `fig_architecture.png` is the architecture diagram.

To rebuild the report run `pip install python-docx`, then `python make_report.py`.

## How it works

1. **`loadshed/instance.py`** holds the feeder data (illustrative numbers) and the hourly deficits.
2. **`loadshed/qubo.py`** builds the QUBO, maps it to an Ising `SparsePauliOp` via `x = (1 − Z)/2`, and computes schedule metrics.
3. **`loadshed/qaoa.py`** does the quantum part:
   - builds the QAOA circuit from `H`, `RZZ`/`RZ` cost layers and `RX` mixers;
   - trains it with a CVaR objective and a COBYLA loop, with INTERP warm starts from p to p+1;
   - samples the trained circuit with Qiskit's `StatevectorSampler`.
4. **`loadshed/baselines.py`** has the classical baselines: exact brute force, the greedy loss-based rule, and simulated annealing.
5. **`run_experiments.py`** runs everything end to end and writes the figures and JSON.

During training, the QAOA state is computed with a NumPy routine that is mathematically identical to the circuit, because rebuilding the circuit on every optimiser step was too slow. A check in the script confirms it matches `qiskit.quantum_info.Statevector`. All reported probabilities and samples come from the Qiskit circuit itself.

## Results (full run)

See `results/results.json` and the report. In short:
- QAOA's best measured sample is the exact optimal rotation.
- The probability of measuring the optimum grows with depth, to roughly two orders of magnitude above random guessing.
- The greedy rule over-sheds 10 MW at 19:00.
- At 15 qubits, QAOA becomes much less reliable (see Limitations in the report).

## Credits

All code was written for this hackathon. Ideas used:
- QAOA: Farhi et al., 2014
- CVaR-QAOA: Barkoutsos et al., *Quantum* 2020
- INTERP initialisation: Zhou et al., *PRX* 2020
- QUBO penalty formulations: Lucas, *Front. Phys.* 2014
