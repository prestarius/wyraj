from pathlib import Path

import pytest

from wyraj.persistence.config import load_config


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WYRAJ_HOME", str(tmp_path))
    return tmp_path


def test_missing_config_is_empty(home: Path) -> None:
    assert load_config() == {}


def test_config_reads_known_keys(home: Path) -> None:
    (home / "config.yml").write_text("ascii: true\nportrait: box\nunknown: 5\n")
    config = load_config()
    assert config == {"ascii": True, "portrait": "box"}


def test_garbage_config_is_ignored(home: Path) -> None:
    (home / "config.yml").write_text("- just\n- a list\n")
    assert load_config() == {}
