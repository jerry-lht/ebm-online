"""Zero-cell correction and continuity adjustments."""

from __future__ import annotations


def apply_zero_cell_correction(
    exp_events: int,
    exp_n: int,
    ctrl_events: int,
    ctrl_n: int,
    correction: float = 0.5,
) -> tuple[float, float, float, float]:
    if (
        exp_events == 0
        or ctrl_events == 0
        or (exp_n - exp_events) == 0
        or (ctrl_n - ctrl_events) == 0
    ):
        return (
            exp_events + correction,
            exp_n + 2 * correction,
            ctrl_events + correction,
            ctrl_n + 2 * correction,
        )
    return float(exp_events), float(exp_n), float(ctrl_events), float(ctrl_n)
