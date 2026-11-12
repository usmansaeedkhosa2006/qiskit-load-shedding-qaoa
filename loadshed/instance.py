"""Problem data for the fair load-shedding rotation problem.

A distribution company faces a supply shortfall (deficit) for a few hours and
must decide which feeders to switch off in each hour.  All numbers are
illustrative (hypothetical feeders) but shaped like a Pakistani DISCO's
loss-based load-management schedule.
"""
from dataclasses import dataclass, field


@dataclass
class Feeder:
    name: str
    kind: str
    load_mw: float      # average demand on the feeder during the window
    loss_rate: float    # technical + commercial (theft / non-payment) losses, 0..1
    protected: bool = False  # hospitals, water pumping: must never be shed


@dataclass
class Instance:
    feeders: list
    deficits_mw: list   # MW that must be shed in each hour
    block_mw: float = 10.0  # MW per "block": loads/deficits are expressed in blocks in the QUBO
    hour_labels: list = field(default_factory=list)

    # ---- derived views -------------------------------------------------
    @property
    def sheddable(self):
        """Protected feeders are removed *before* the quantum step (hard rule)."""
        return [f for f in self.feeders if not f.protected]

    @property
    def protected(self):
        return [f for f in self.feeders if f.protected]

    @property
    def n_feeders(self):
        return len(self.sheddable)

    @property
    def n_hours(self):
        return len(self.deficits_mw)

    @property
    def n_qubits(self):
        return self.n_feeders * self.n_hours

    def var_index(self, f, h):
        """Qubit index of x_{f,h} (feeder-major ordering)."""
        return f * self.n_hours + h

    def loads_blocks(self):
        return [f.load_mw / self.block_mw for f in self.sheddable]

    def deficits_blocks(self):
        return [d / self.block_mw for d in self.deficits_mw]


def default_instance():
    """4 sheddable feeders x 3 hours = 12 qubits (+1 protected hospital feeder)."""
    feeders = [
        Feeder("F1", "Residential, high-loss", 30, 0.35),
        Feeder("F2", "Mixed residential/commercial", 20, 0.25),
        Feeder("F3", "Commercial market", 20, 0.10),
        Feeder("F4", "Residential, low-loss", 10, 0.05),
        Feeder("F5", "Hospital + water pumping", 25, 0.03, protected=True),
    ]
    return Instance(feeders=feeders, deficits_mw=[30, 30, 40],
                    hour_labels=["18:00", "19:00", "20:00"])


def large_instance():
    """5 sheddable feeders x 3 hours = 15 qubits, used for the scaling check."""
    feeders = [
        Feeder("F1", "Residential, high-loss", 30, 0.35),
        Feeder("F2", "Mixed residential/commercial", 20, 0.25),
        Feeder("F3", "Commercial market", 20, 0.10),
        Feeder("F4", "Residential, low-loss", 10, 0.05),
        Feeder("F6", "Industrial estate", 20, 0.08),
        Feeder("F5", "Hospital + water pumping", 25, 0.03, protected=True),
    ]
    return Instance(feeders=feeders, deficits_mw=[40, 30, 50],
                    hour_labels=["18:00", "19:00", "20:00"])
