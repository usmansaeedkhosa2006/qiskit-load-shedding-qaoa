"""Sanity checks: Ising mapping matches the QUBO, and the QUBO optimum is a valid schedule."""
import numpy as np
from loadshed.instance import default_instance
from loadshed.qubo import build_qubo, all_costs, qubo_to_ising, evaluate_schedule, bits_from_index
from loadshed.baselines import brute_force


def test_ising_matches_qubo():
    inst = default_instance()
    Q, off = build_qubo(inst)
    op, *_ = qubo_to_ising(Q, off)
    diag = np.real(np.diag(op.to_matrix(sparse=True).toarray()))
    assert np.allclose(diag, all_costs(Q, off))


def test_optimum_is_feasible():
    inst = default_instance()
    Q, off = build_qubo(inst)
    x, c, _ = brute_force(Q, off)
    assert evaluate_schedule(inst, x)["feasible"]


def test_fast_simulator_matches_qiskit():
    from loadshed.qaoa import QAOASolver, qaoa_circuit, fast_qaoa_probs
    inst = default_instance()
    Q, off = build_qubo(inst)
    _, h, J, _ = qubo_to_ising(Q, off)
    costs = all_costs(Q, off)
    s = QAOASolver(inst.n_qubits, h, J, costs)
    qc, g, b = qaoa_circuit(inst.n_qubits, h, J, 3, s.scale)
    theta = np.array([0.4, 0.9, 1.3, 0.2, 0.6, 1.1])
    ref = s.qiskit_probs(qc, list(g) + list(b), theta)
    assert np.allclose(fast_qaoa_probs(costs / s.scale, inst.n_qubits, theta), ref, atol=1e-10)


if __name__ == "__main__":
    test_ising_matches_qubo(); test_optimum_is_feasible(); test_fast_simulator_matches_qiskit()
    print("all tests passed")
