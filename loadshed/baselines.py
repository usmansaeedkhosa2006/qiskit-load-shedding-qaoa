"""Classical baselines: exact brute force, a utility-style greedy rule, simulated annealing."""
import numpy as np
from .qubo import all_costs, bits_from_index, qubo_value


def brute_force(Q, offset):
    costs = all_costs(Q, offset)
    k = int(np.argmin(costs))
    return bits_from_index(k, Q.shape[0]), float(costs[k]), costs


def greedy_rotation(inst):
    """What a control room might do by hand: each hour, shed the highest-loss
    feeders first, skipping any feeder that was shed in the previous hour,
    until the deficit is covered."""
    x = [0] * inst.n_qubits
    order = sorted(range(inst.n_feeders), key=lambda f: -inst.sheddable[f].loss_rate)
    for h in range(inst.n_hours):
        shed = 0.0
        for f in order:
            if shed >= inst.deficits_mw[h]:
                break
            if h > 0 and x[inst.var_index(f, h - 1)]:
                continue
            x[inst.var_index(f, h)] = 1
            shed += inst.sheddable[f].load_mw
    return x


def simulated_annealing(Q, offset, sweeps=2000, restarts=10, seed=3):
    rng = np.random.default_rng(seed)
    n = Q.shape[0]
    S = Q + Q.T - np.diag(np.diag(Q))  # symmetric couplings, diagonal = linear terms
    best_x, best_c = None, np.inf
    for _ in range(restarts):
        x = rng.integers(0, 2, n)
        c = qubo_value(Q, offset, x)
        for t in range(sweeps):
            T = 5.0 * (0.01 / 5.0) ** (t / sweeps)
            i = rng.integers(n)
            # energy change of flipping bit i
            d = (1 - 2 * x[i]) * (np.diag(Q)[i] + S[i] @ x - S[i, i] * x[i])
            if d < 0 or rng.random() < np.exp(-d / T):
                x[i] ^= 1
                c += d
        if c < best_c:
            best_x, best_c = x.copy(), c
    return list(map(int, best_x)), float(best_c)
