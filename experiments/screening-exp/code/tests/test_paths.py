from screening.paths import (
    code_root,
    config_root,
    data_root,
    ensure_results_subdir,
    experiment_root,
    results_root,
)


def test_roots_match_experiment_layout() -> None:
    assert experiment_root.name == "screening-exp"
    assert code_root == experiment_root / "code"
    assert data_root == experiment_root / "data"
    assert results_root == experiment_root / "results"
    assert config_root == code_root / "config"


def test_config_templates_exist() -> None:
    assert (config_root / "llm_providers.example.yaml").is_file()
    assert (config_root / "experiment_defaults.yaml").is_file()


def test_ensure_results_subdir_creates_directory() -> None:
    path = ensure_results_subdir("phase1-test-artifacts")
    assert path.is_dir()
    assert path == results_root / "phase1-test-artifacts"
