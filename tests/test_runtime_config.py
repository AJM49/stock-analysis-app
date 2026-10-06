from core import runtime_config


def test_get_env_status_returns_true_for_nonempty_value(monkeypatch):
    monkeypatch.setenv("TEST_RUNTIME_CONFIG", "configured")

    assert runtime_config.get_env_status("TEST_RUNTIME_CONFIG") is True


def test_get_env_status_returns_false_for_missing_value(monkeypatch):
    monkeypatch.delenv("TEST_RUNTIME_CONFIG", raising=False)

    assert runtime_config.get_env_status("TEST_RUNTIME_CONFIG") is False


def test_get_secret_status_returns_true_for_nonempty_value(monkeypatch):
    monkeypatch.setattr(
        runtime_config.st,
        "secrets",
        {"TEST_SECRET": "configured"},
    )

    assert runtime_config.get_secret_status("TEST_SECRET") is True


def test_get_secret_status_returns_false_for_missing_value(monkeypatch):
    monkeypatch.setattr(runtime_config.st, "secrets", {})

    assert runtime_config.get_secret_status("TEST_SECRET") is False


def test_get_secret_status_returns_false_when_secret_access_fails(monkeypatch):
    class BrokenSecrets:
        def get(self, _name):
            raise RuntimeError("secret access failed")

    monkeypatch.setattr(runtime_config.st, "secrets", BrokenSecrets())

    assert runtime_config.get_secret_status("TEST_SECRET") is False
