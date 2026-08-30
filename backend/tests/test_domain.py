from app.domain import clamp, heat_index_c, risk_level
from app.models import RiskLevel


def test_clamp_and_risk_bands():
    assert clamp(-1) == 0
    assert clamp(120) == 100
    assert risk_level(10) == RiskLevel.LOW
    assert risk_level(49.9) == RiskLevel.MODERATE
    assert risk_level(74.9) == RiskLevel.HIGH
    assert risk_level(75) == RiskLevel.SEVERE


def test_heat_index_is_finite():
    value = heat_index_c(35, 60)
    assert 35 < value < 60
