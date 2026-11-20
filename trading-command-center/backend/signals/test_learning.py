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


if __name__ == "__main__":
    test_adapt()
    print("ok")
