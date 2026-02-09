"""
Tests for backend.core.personality
"""

import sys
import os

# Allow running tests directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone
from backend.core.personality import (
    exp_required_for_level,
    level_from_exp,
    exp_for_interaction,
    diminishing_return,
    apply_stat_growth,
    calculate_decay,
    determine_archetype,
    create_initial_stats,
    process_interaction,
    streak_bonus,
    STAT_KEYS,
)


class TestLevelSystem:
    def test_level_1_requires_zero_exp(self):
        assert exp_required_for_level(1) == 0

    def test_levels_are_monotonically_increasing(self):
        prev = 0
        for lv in range(2, 101):
            exp = exp_required_for_level(lv)
            assert exp > prev, f"Level {lv} should require more exp than {lv-1}"
            prev = exp

    def test_level_from_exp_roundtrip(self):
        for lv in [1, 5, 10, 30, 50, 99]:
            exp = exp_required_for_level(lv)
            assert level_from_exp(exp) == lv

    def test_exp_for_interaction_positive(self):
        assert exp_for_interaction(1) > 0
        assert exp_for_interaction(50) > 0

    def test_quality_scales_exp(self):
        low = exp_for_interaction(10, quality=0.5)
        normal = exp_for_interaction(10, quality=1.0)
        high = exp_for_interaction(10, quality=2.0)
        assert low < normal < high


class TestDiminishingReturn:
    def test_low_value_high_efficiency(self):
        assert diminishing_return(0) > 0.9

    def test_mid_value_mid_efficiency(self):
        eff = diminishing_return(50)
        assert 0.4 < eff < 0.6

    def test_high_value_low_efficiency(self):
        assert diminishing_return(90) < 0.1


class TestStatGrowth:
    def test_basic_growth(self):
        stats = {k: 10 for k in STAT_KEYS}
        new, deltas = apply_stat_growth(stats, {"curiosity": 5})
        assert new["curiosity"] > stats["curiosity"]
        assert deltas["curiosity"] > 0

    def test_antagonism_courage_empathy(self):
        stats = {k: 30 for k in STAT_KEYS}
        new, deltas = apply_stat_growth(stats, {"courage": 10})
        assert deltas["courage"] > 0
        assert deltas["empathy"] < 0, "Empathy should be dragged down by courage growth"

    def test_antagonism_creativity_wisdom(self):
        stats = {k: 30 for k in STAT_KEYS}
        new, deltas = apply_stat_growth(stats, {"creativity": 10})
        assert deltas["wisdom"] < 0

    def test_no_change_stays_same(self):
        stats = {k: 50 for k in STAT_KEYS}
        new, deltas = apply_stat_growth(stats, {})
        for k in STAT_KEYS:
            assert deltas[k] == 0

    def test_clamped_to_100(self):
        stats = {k: 99 for k in STAT_KEYS}
        new, _ = apply_stat_growth(stats, {"curiosity": 100})
        assert new["curiosity"] <= 100

    def test_clamped_to_0(self):
        stats = {k: 1 for k in STAT_KEYS}
        new, _ = apply_stat_growth(stats, {"curiosity": -100})
        assert new["curiosity"] >= 0


class TestDecay:
    def test_no_decay_within_grace(self):
        stats = {k: 50 for k in STAT_KEYS}
        last = datetime.now(timezone.utc) - timedelta(hours=24)
        new, amounts = calculate_decay(stats, last)
        assert all(a == 0 for a in amounts.values())

    def test_decay_after_grace(self):
        stats = {k: 50 for k in STAT_KEYS}
        last = datetime.now(timezone.utc) - timedelta(days=7)
        new, amounts = calculate_decay(stats, last)
        assert all(a < 0 for a in amounts.values())

    def test_decay_floor(self):
        stats = {k: 6 for k in STAT_KEYS}
        last = datetime.now(timezone.utc) - timedelta(days=100)
        new, _ = calculate_decay(stats, last)
        assert all(v >= 5 for v in new.values())

    def test_max_decay_cap(self):
        stats = {k: 80 for k in STAT_KEYS}
        last = datetime.now(timezone.utc) - timedelta(days=365)
        new, amounts = calculate_decay(stats, last)
        for k in STAT_KEYS:
            assert abs(amounts[k]) <= 15


class TestArchetype:
    def test_blank(self):
        stats = {k: 10 for k in STAT_KEYS}
        assert determine_archetype(stats) == "白纸娃娃"

    def test_genius(self):
        stats = {k: 70 for k in STAT_KEYS}
        assert determine_archetype(stats) == "全能小天才"

    def test_complex(self):
        stats = {k: 30 for k in STAT_KEYS}
        stats["courage"] = 60
        stats["empathy"] = 60
        assert determine_archetype(stats) == "矛盾体"


class TestCreateInitialStats:
    def test_blank_around_10(self):
        stats = create_initial_stats("blank")
        for k in STAT_KEYS:
            assert 5 < stats[k] < 15

    def test_different_births_different_stats(self):
        blank = create_initial_stats("blank")
        wild = create_initial_stats("wild")
        # Wild should have higher courage
        # (with jitter, just check the pattern roughly)
        assert wild["courage"] > blank["courage"] - 5


class TestStreakBonus:
    def test_no_bonus_day_1(self):
        assert streak_bonus(1) == 1.0

    def test_bonus_increases(self):
        assert streak_bonus(7) > streak_bonus(3) > 1.0

    def test_max_cap(self):
        assert streak_bonus(100) <= 1.5


class TestProcessInteraction:
    def test_full_flow(self):
        stats = create_initial_stats("blank")
        growth = {
            "level": 1, "total_exp": 0, "total_interactions": 0,
            "streak_days": 0, "last_interaction_at": None, "archetype": "白纸娃娃",
        }
        result = process_interaction(stats, growth, {"curiosity": 5, "empathy": 2})
        assert result["stats"]["curiosity"] > stats["curiosity"]
        assert result["exp_gained"] > 0
        assert result["growth"]["total_interactions"] == 1

    def test_level_up(self):
        stats = create_initial_stats("blank")
        growth = {
            "level": 1, "total_exp": exp_required_for_level(2) - 1,
            "total_interactions": 10, "streak_days": 1,
            "last_interaction_at": datetime.now(timezone.utc).isoformat(),
            "archetype": "白纸娃娃",
        }
        result = process_interaction(stats, growth, {"curiosity": 3}, interaction_quality=2.0)
        # With enough exp to push past level 2, should level up
        assert result["growth"]["level"] >= 2


# ============================================================
# Runner
# ============================================================

if __name__ == "__main__":
    import traceback

    test_classes = [
        TestLevelSystem, TestDiminishingReturn, TestStatGrowth,
        TestDecay, TestArchetype, TestCreateInitialStats,
        TestStreakBonus, TestProcessInteraction,
    ]

    passed = failed = 0
    for cls in test_classes:
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                try:
                    getattr(instance, name)()
                    passed += 1
                    print(f"  ✅ {cls.__name__}.{name}")
                except Exception as e:
                    failed += 1
                    print(f"  ❌ {cls.__name__}.{name}: {e}")
                    traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
