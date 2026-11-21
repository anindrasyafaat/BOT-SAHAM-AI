from signals.learning import adapt


def test_adapt():
    assert "belajar" in adapt(70, True, 5, 80, 3, -1).reason
    a = adapt(70, True, 25, 40, 1, -2)          # expectancy negatif
    assert a.min_confidence == 72 and a.enabled
    a = adapt(70, True, 50, 30, 1, -2)          # rugi terus, sampel cukup
    assert not a.enabled
    a = adapt(70, True, 25, 60, 3, -1)          # untung, win rate sehat
    assert a.min_confidence == 69 and a.expectancy > 0
    assert adapt(60, True, 25, 60, 3, -1).min_confidence == 60   # tidak turun di bawah lantai
    assert adapt(95, True, 25, 40, 1, -2).min_confidence == 95   # tidak naik di atas plafon


def test_evaluate_signal():
    from signals.learning import evaluate_signal as ev
    assert ev(True, 100, 95, 110, 100, False) == (None, 0.0)
    assert ev(True, 100, 95, 110, 94, False)[0] == "STOPPED_OUT"
    st, pnl = ev(True, 100, 95, 110, 111, False)
    assert st == "TARGET_HIT" and round(pnl, 6) == 11
    # SELL: target di bawah entry tidak boleh langsung kena saat harga = entry (bug lama)
    assert ev(False, 100, 105, 90, 100, False)[0] is None
    st, pnl = ev(False, 100, 105, 90, 89, False)
    assert st == "TARGET_HIT" and round(pnl, 6) == 11
    st, pnl = ev(False, 100, 105, 90, 106, False)
    assert st == "STOPPED_OUT" and pnl < 0
    assert ev(True, 0, 0, None, 5, False) == ("CANCELLED", 0.0)  # harga rusak tidak crash
    st, pnl = ev(True, 100, 95, 110, 102, True)
    assert st == "EXPIRED" and round(pnl, 6) == 2


def test_valid_levels():
    from signals.learning import valid_levels as v
    assert v(True, 100, 95, 110) and v(False, 100, 105, 90) and v(True, 100, 95, None)
    assert not v(True, 5300, 5197.5, 4770.66)  # bug VWAP_OrderBlock: target BUY di bawah entry
    assert not v(False, 100, 95, 90) and not v(True, 0, 0, 1)


if __name__ == "__main__":
    test_valid_levels()
    test_adapt()
    test_evaluate_signal()
    print("ok")
