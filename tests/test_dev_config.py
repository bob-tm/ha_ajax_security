"""Test the local development cache switch."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.ajax_jeedom.dev_config import cache_api_requests_enabled


def test_missing_file_disables_cache(tmp_path: Path) -> None:
    assert not cache_api_requests_enabled(str(tmp_path / "missing.json"))


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        pytest.param('{"cache_api_requests":true}', True, id="enabled"),
        pytest.param('{"cache_api_requests":false}', False, id="disabled"),
        pytest.param('{"cache_api_requests":"true"}', False, id="string"),
        pytest.param("{}", False, id="missing-setting"),
        pytest.param("[]", False, id="wrong-shape"),
        pytest.param("invalid", False, id="invalid-json"),
    ],
)
def test_only_boolean_true_enables_cache(
    tmp_path: Path, content: str, expected: bool
) -> None:
    path = tmp_path / "dev.json"
    path.write_text(content)
    assert cache_api_requests_enabled(str(path)) is expected
