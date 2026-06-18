from unittest.mock import MagicMock, patch
from src import db_preflight

def _engine_returning(count):
    eng = MagicMock()
    conn = eng.connect.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = count
    return eng

def test_skips_build_when_table_populated():
    eng = _engine_returning(2068)
    with patch("src.db_preflight.build_nppv_features.build") as mock_build:
        triggered = db_preflight.ensure_nppv_features(eng)
    assert triggered is False
    mock_build.assert_not_called()

def test_builds_when_table_empty():
    eng = _engine_returning(0)
    with patch("src.db_preflight.build_nppv_features.build") as mock_build:
        triggered = db_preflight.ensure_nppv_features(eng)
    assert triggered is True
    mock_build.assert_called_once_with(eng)

def test_builds_when_table_missing():
    eng = MagicMock()
    conn = eng.connect.return_value.__enter__.return_value
    conn.execute.side_effect = Exception("UndefinedTable")
    with patch("src.db_preflight.build_nppv_features.build") as mock_build:
        triggered = db_preflight.ensure_nppv_features(eng)
    assert triggered is True
    mock_build.assert_called_once_with(eng)
