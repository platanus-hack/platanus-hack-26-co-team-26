from src.model import build_tiny_tcn


def test_budget_and_shapes():
    model = build_tiny_tcn()
    assert model.count_params() < 100_000
    assert model.input_shape == (None, 450, 4)
    assert set(model.output_names) == {"physiology_logits", "quality_probability"}
