"""
AI Brain: strategi belajar dari hasil sinyalnya sendiri.

Setiap siklus performa, tiap strategi dinilai dari sinyal yang sudah ditutup:
- expectancy negatif  -> ambang confidence dinaikkan (lebih selektif)
- expectancy positif & win rate sehat -> ambang diturunkan (lebih banyak peluang)
- terus merugi setelah cukup sampel -> strategi dimatikan (aktifkan lagi manual lewat toggle)
Keputusan disimpan ke StrategyConfig, jadi pembelajaran bertahan setelah restart.
"""

from dataclasses import dataclass

MIN_SAMPLE = 20        # jangan menilai strategi sebelum ada cukup sinyal tertutup
DISABLE_SAMPLE = 40    # bukti yang dibutuhkan sebelum mematikan strategi
CONF_FLOOR, CONF_CEIL = 60.0, 95.0


@dataclass
class Adaptation:
    min_confidence: float
    enabled: bool
    expectancy: float
    reason: str


def adapt(min_confidence: float, enabled: bool, closed: int, win_rate: float,
          avg_profit: float, avg_loss: float) -> Adaptation:
    """win_rate dalam persen; avg_loss bernilai negatif (persen)."""
    wr = win_rate / 100.0
    expectancy = wr * avg_profit + (1 - wr) * avg_loss
    if closed < MIN_SAMPLE:
        return Adaptation(min_confidence, enabled, expectancy, f"belajar: baru {closed}/{MIN_SAMPLE} sinyal tertutup")
    if expectancy < 0 and win_rate < 35 and closed >= DISABLE_SAMPLE:
        return Adaptation(CONF_CEIL, False, expectancy, f"dimatikan: expectancy {expectancy:.2f}%, win rate {win_rate:.0f}%")
    if expectancy < 0:
        new = min(CONF_CEIL, min_confidence + 2.0)
        return Adaptation(new, enabled, expectancy, f"lebih selektif: ambang {min_confidence:.0f}→{new:.0f}")
    if win_rate >= 55:
        new = max(CONF_FLOOR, min_confidence - 1.0)
        return Adaptation(new, enabled, expectancy, f"lebih agresif: ambang {min_confidence:.0f}→{new:.0f}")
    return Adaptation(min_confidence, enabled, expectancy, "stabil: pertahankan parameter")
