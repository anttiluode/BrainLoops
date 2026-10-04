from pathlib import Path

import numpy as np

from brainloops.receipts import config_fingerprint, write_receipt
from brainloops.types import CycleSummary, KRecurrenceResult
from experiments.gate0_synthetic import classify_recurrence, run_gate0


def _row(k, p_markov, p_surrogate):
    return KRecurrenceResult(
        k=k,
        asymmetry=0.4,
        markov_mean=0.2,
        markov_sd=0.05,
        p_markov=p_markov,
        excess_z=4.0,
        surrogate_mean=1.0,
        surrogate_sd=1.0,
        p_surrogate=p_surrogate,
        n_visits=100,
        cycles=(CycleSummary((0, 1, 2), 3.0, 4, 6.0),),
    )


def test_classify_recurrence_uses_two_of_three_k_rule():
    assert classify_recurrence([_row(6, .5, .5), _row(10, .5, .5), _row(20, .01, .01)]) == "NO_ROBUST_RECURRENCE"
    assert classify_recurrence([_row(6, .01, .5), _row(10, .01, .5), _row(20, .5, .5)]) == "LINEAR_LAG_RECURRENCE"
    assert classify_recurrence([_row(6, .01, .01), _row(10, .01, .01), _row(20, .5, .5)]) == "BEYOND_LINEAR_RECURRENCE"


def test_receipt_fingerprint_is_order_independent_and_json_handles_numpy(tmp_path):
    a = {"seed": 1, "ks": [6, 10, 20]}
    b = {"ks": [6, 10, 20], "seed": 1}
    assert config_fingerprint(a) == config_fingerprint(b)
    path = tmp_path / "receipt.json"
    write_receipt(path, {"array": np.array([1, 2]), "z": 1 + 2j})
    text = path.read_text()
    assert '"array": [' in text
    assert '"real": 1.0' in text
    assert '"imag": 2.0' in text


def test_gate0_four_preregistered_synthetic_classes():
    receipt = run_gate0(seed=1, n_null=39)
    assert receipt["status"] == "PASS"
    assert receipt["config"]["code_version"] == "0.1.0"
    assert receipt["config"]["n_null"] == 39
    assert receipt["config"]["surrogate_markov_n_null"] == 9
    classes = {name: item["classification"] for name, item in receipt["cases"].items()}
    assert classes == {
        "reversible_ar_noise": "NO_ROBUST_RECURRENCE",
        "linear_rotating_ar": "LINEAR_LAG_RECURRENCE",
        "smooth_forward_phase": "LINEAR_LAG_RECURRENCE",
        "event_switching_loop": "BEYOND_LINEAR_RECURRENCE",
    }


def test_gate0_script_runs_from_source_tree():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "experiments/gate0_synthetic.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
