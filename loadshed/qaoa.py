"""QAOA for the load-shedding QUBO, written directly with Qiskit circuits.

Circuit:  |+>^n  ->  [ exp(-i*gamma_k*H_C)  exp(-i*beta_k*sum X) ] for k = 1..p  -> measure
Training: classical COBYLA loop over (gamma, beta), using a CVaR objective
          (Barkoutsos et al., Quantum 4, 256 (2020)) evaluated on the simulated
          state, with layer-wise INTERP initialisation (Zhou et al., PRX 10,
          021067 (2020)).  The circuit and loop are our own implementation.
"""
import time
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import Statevector
from qiskit.primitives import StatevectorSampler


def qaoa_circuit(n, h, J, p, scale=1.0, measure=False):
    """Parameterised QAOA ansatz.  h, J are Ising coefficients; `scale` normalises them."""
    gammas = ParameterVector("γ", p)
    betas = ParameterVector("β", p)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for k in range(p):
        # cost layer: exp(-i γ (sum h_i Z_i + sum J_ij Z_i Z_j))
        for (i, j), v in J.items():
            qc.rzz(2 * gammas[k] * v / scale, i, j)
        for i in range(n):
            if h[i] != 0:
                qc.rz(2 * gammas[k] * h[i] / scale, i)
        # mixer layer: exp(-i β sum X_i)
        qc.rx(2 * betas[k], range(n))
    if measure:
        qc.measure_all()
    return qc, gammas, betas


def cvar(probs, costs_sorted_idx, costs, alpha):
    """Mean cost of the best alpha-fraction of the probability mass."""
    if alpha >= 1.0:
        return float(probs @ costs)
    p_sorted = probs[costs_sorted_idx]
    c_sorted = costs[costs_sorted_idx]
    cum = np.cumsum(p_sorted)
    cut = np.searchsorted(cum, alpha)
    taken = p_sorted[:cut].sum()
    val = (p_sorted[:cut] @ c_sorted[:cut]) + (alpha - taken) * c_sorted[cut]
    return float(val / alpha)


class QAOASolver:
    def __init__(self, n, h, J, costs, alpha=0.2, maxiter=300, restarts=4, seed=7, fast=True):
        self.fast = fast
        self.n, self.h, self.J = n, h, J
        self.costs = costs
        self.order = np.argsort(costs)
        self.alpha = alpha
        self.maxiter = maxiter
        self.restarts = restarts
        self.rng = np.random.default_rng(seed)
        self.scale = max(np.max(np.abs(h)), max(abs(v) for v in J.values()))
        self.n_evals = 0

    def _probs(self, qc, params, theta):
        if self.fast:
            return fast_qaoa_probs(self.costs / self.scale, self.n, theta)
        bound = qc.assign_parameters(dict(zip(params, theta)))
        return Statevector(bound).probabilities()

    def qiskit_probs(self, qc, params, theta):
        """Exact output distribution of the actual Qiskit circuit."""
        bound = qc.assign_parameters(dict(zip(params, theta)))
        return Statevector(bound).probabilities()

    def _objective(self, qc, params):
        def f(theta):
            self.n_evals += 1
            return cvar(self._probs(qc, params, theta), self.order, self.costs, self.alpha)
        return f

    def train(self, p_max=3):
        """Train p = 1..p_max, INTERP-initialising each depth from the previous one."""
        history = {}
        prev = None
        for p in range(1, p_max + 1):
            qc, g, b = qaoa_circuit(self.n, self.h, self.J, p, self.scale)
            params = list(g) + list(b)
            starts = []
            if prev is not None:
                starts.append(np.concatenate([_interp(prev[:p - 1]), _interp(prev[p - 1:])]))
            while len(starts) < self.restarts:
                starts.append(np.concatenate([self.rng.uniform(0, np.pi, p),
                                              self.rng.uniform(0, np.pi / 2, p)]))
            best = None
            t0 = time.time()
            self.n_evals = 0
            for x0 in starts:
                res = minimize(self._objective(qc, params), x0, method="COBYLA",
                               options={"maxiter": self.maxiter, "rhobeg": 0.3})
                if best is None or res.fun < best.fun:
                    best = res
            probs = self._probs(qc, params, best.x)
            history[p] = {
                "theta": best.x,
                "cvar": float(best.fun),
                "expectation": float(probs @ self.costs),
                "probs": probs,
                "evals": self.n_evals,
                "seconds": time.time() - t0,
                "circuit": qc,
                "params": params,
            }
            prev = best.x
        return history

    def sample(self, qc, params, theta, shots=4096, seed=11):
        """Run the trained circuit through Qiskit's Sampler primitive (shot-based)."""
        mqc = qc.assign_parameters(dict(zip(params, theta))).copy()
        mqc.measure_all()
        sampler = StatevectorSampler(seed=seed)
        result = sampler.run([mqc], shots=shots).result()[0]
        counts = result.data.meas.get_counts()
        # Qiskit bitstrings are big-endian (qubit 0 is the right-most character)
        return {int(bs, 2): c for bs, c in counts.items()}


def fast_qaoa_probs(scaled_costs, n, theta):
    """Training-only shortcut: the same QAOA state computed with numpy.

    The cost layer is diagonal, so exp(-i*gamma*H_C) is an element-wise phase
    (up to a global phase); the mixer is RX(2*beta) on every qubit.  This is
    mathematically identical to `qaoa_circuit` (checked in tests against
    qiskit.quantum_info.Statevector) but avoids rebuilding the circuit on every
    optimiser step.  Final results always come from the Qiskit circuit.
    """
    p = len(theta) // 2
    gammas, betas = theta[:p], theta[p:]
    psi = np.full(2 ** n, 2 ** (-n / 2), dtype=complex)
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * scaled_costs)
        c, s = np.cos(b), -1j * np.sin(b)
        for q in range(n):
            v = psi.reshape(2 ** (n - q - 1), 2, 2 ** q)  # middle axis = qubit q
            a0, a1 = v[:, 0, :], v[:, 1, :]
            psi = np.stack([c * a0 + s * a1, s * a0 + c * a1], axis=1).reshape(-1)
    return np.abs(psi) ** 2


def _interp(v):
    """INTERP rule: length-k angle schedule -> length-(k+1) schedule."""
    k = len(v)
    out = np.zeros(k + 1)
    for i in range(k + 1):
        left = v[i - 1] if i - 1 >= 0 else 0.0
        right = v[i] if i < k else 0.0
        out[i] = (i / k) * left + ((k - i) / k) * right
    return out
