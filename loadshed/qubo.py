"""QUBO formulation of the fair load-shedding rotation problem.

Variables   x[f,h] in {0,1}: 1 = feeder f is switched off during hour h.

Minimise    C(x) = sum_{f,h} c_f * x[f,h]                                 (harm to paying customers)
                 + A * sum_h ( sum_f L_f x[f,h] - D_h )^2                 (meet the deficit, don't over-shed)
                 + B * sum_f sum_h x[f,h] * x[f,h+1]                      (fairness: no back-to-back cuts)

with c_f = L_f * (1 - loss_f): shedding a high-loss feeder harms fewer paying
customers per MW, which reproduces loss-based load management.  Protected
feeders are not variables at all (removed classically before the quantum step).
"""
import itertools
import numpy as np
from qiskit.quantum_info import SparsePauliOp


DEFAULT_A = 3.0  # deficit penalty weight (per block^2)
DEFAULT_B = 3.0  # fairness penalty weight (per back-to-back cut)


def build_qubo(inst, A=DEFAULT_A, B=DEFAULT_B):
    """Return (Q, offset) with C(x) = x^T Q x + offset, Q upper-triangular."""
    n = inst.n_qubits
    L = inst.loads_blocks()
    D = inst.deficits_blocks()
    Q = np.zeros((n, n))
    offset = 0.0
    idx = inst.var_index

    # 1) harm term
    for f, feeder in enumerate(inst.sheddable):
        c = L[f] * (1.0 - feeder.loss_rate)
        for h in range(inst.n_hours):
            Q[idx(f, h), idx(f, h)] += c

    # 2) deficit penalty  A * (sum_f L_f x_fh - D_h)^2, using x^2 = x
    for h in range(inst.n_hours):
        offset += A * D[h] ** 2
        for f in range(inst.n_feeders):
            i = idx(f, h)
            Q[i, i] += A * (L[f] ** 2 - 2 * D[h] * L[f])
            for g in range(f + 1, inst.n_feeders):
                Q[i, idx(g, h)] += 2 * A * L[f] * L[g]

    # 3) fairness penalty  B * x_fh * x_f,h+1
    for f in range(inst.n_feeders):
        for h in range(inst.n_hours - 1):
            Q[idx(f, h), idx(f, h + 1)] += B

    return Q, offset


def qubo_value(Q, offset, x):
    x = np.asarray(x, dtype=float)
    return float(x @ Q @ x + offset)


def all_costs(Q, offset):
    """Cost of every basis state |k>, with bit i of k = x_i (Qiskit little-endian)."""
    n = Q.shape[0]
    k = np.arange(2 ** n)
    X = ((k[:, None] >> np.arange(n)) & 1).astype(float)
    return np.einsum("ki,ij,kj->k", X, Q, X) + offset


def qubo_to_ising(Q, offset):
    """Map x_i = (1 - Z_i)/2.  Returns a SparsePauliOp H with <k|H|k> = C(k)."""
    n = Q.shape[0]
    h = np.zeros(n)
    J = {}
    const = offset
    for i in range(n):
        q = Q[i, i]
        const += q / 2
        h[i] += -q / 2
    for i, j in itertools.combinations(range(n), 2):
        q = Q[i, j] + Q[j, i]
        if q == 0:
            continue
        # q x_i x_j = q/4 (1 - Z_i - Z_j + Z_i Z_j)
        const += q / 4
        h[i] += -q / 4
        h[j] += -q / 4
        J[(i, j)] = J.get((i, j), 0.0) + q / 4

    terms = [("", [], const)]
    terms += [("Z", [i], h[i]) for i in range(n) if h[i] != 0]
    terms += [("ZZ", [i, j], v) for (i, j), v in J.items() if v != 0]
    op = SparsePauliOp.from_sparse_list(terms, num_qubits=n).simplify()
    return op, h, J, const


def decode(inst, x):
    """Bit vector -> {hour: [feeder names]}."""
    sched = {}
    for h in range(inst.n_hours):
        sched[h] = [inst.sheddable[f].name for f in range(inst.n_feeders)
                    if x[inst.var_index(f, h)]]
    return sched


def bits_from_index(k, n):
    return [(k >> i) & 1 for i in range(n)]


def evaluate_schedule(inst, x):
    """Plain-language metrics, independent of the penalty weights."""
    L = [f.load_mw for f in inst.sheddable]
    shed, gap = [], []
    for h in range(inst.n_hours):
        s = sum(L[f] for f in range(inst.n_feeders) if x[inst.var_index(f, h)])
        shed.append(s)
        gap.append(s - inst.deficits_mw[h])
    back_to_back = sum(
        x[inst.var_index(f, h)] * x[inst.var_index(f, h + 1)]
        for f in range(inst.n_feeders) for h in range(inst.n_hours - 1))
    harm = sum(inst.sheddable[f].load_mw * (1 - inst.sheddable[f].loss_rate)
               * x[inst.var_index(f, h)]
               for f in range(inst.n_feeders) for h in range(inst.n_hours))
    return {
        "shed_mw": shed,
        "unmet_mw": sum(max(0, -g) for g in gap),       # under-shedding -> grid risk
        "over_shed_mw": sum(max(0, g) for g in gap),    # unnecessary outages
        "back_to_back_cuts": int(back_to_back),
        "paying_mw_cut": round(harm, 3),
        "feasible": all(g == 0 for g in gap) and back_to_back == 0,
    }
