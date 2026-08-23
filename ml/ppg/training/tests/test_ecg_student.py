from src.ecg_student_model import build_ecg_student


def test_ecg_student_budget_and_shapes():
    model = build_ecg_student()
    assert model.count_params() < 250_000
    assert model.input_shape == (None, 1800, 5)
    assert set(model.output_names) == {
        "estimated_ecg_mean", "estimated_ecg_logvar", "reconstruction_quality"
    }
