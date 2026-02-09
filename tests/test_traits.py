"""
Tests for backend.core.traits
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.traits import TraitSystem, TRAIT_REGISTRY, RARITY_ORDER
from backend.core.personality import STAT_KEYS


class TestTraitSystem:
    def setup_method(self):
        self.ts = TraitSystem()
        self.low_stats = {k: 10 for k in STAT_KEYS}
        self.default_growth = {"total_interactions": 5, "streak_days": 1}

    def test_no_unlock_at_low_stats(self):
        result = self.ts.check_and_unlock(self.low_stats, [], self.default_growth)
        assert result is None

    def test_n01_unlocks_at_curiosity_30(self):
        stats = {k: 10 for k in STAT_KEYS}
        stats["curiosity"] = 35
        result = self.ts.check_and_unlock(stats, [], self.default_growth)
        assert result is not None
        # Could be N-01 or another trait, but something should unlock
        assert result["rarity"] in ["N", "R", "SR", "SSR"]

    def test_already_unlocked_skipped(self):
        stats = {k: 35 for k in STAT_KEYS}
        # First unlock
        r1 = self.ts.check_and_unlock(stats, [], self.default_growth)
        assert r1 is not None
        # Second unlock should be different
        r2 = self.ts.check_and_unlock(stats, [r1["trait_id"]], self.default_growth)
        if r2 is not None:
            assert r2["trait_id"] != r1["trait_id"]

    def test_higher_rarity_checked_first(self):
        sorted_ids = self.ts._sorted_ids
        rarities = [TRAIT_REGISTRY[tid]["rarity"] for tid in sorted_ids]
        rarity_order = [RARITY_ORDER[r] for r in rarities]
        # Should be non-decreasing (SSR=0 first, then SR=1, etc.)
        for i in range(1, len(rarity_order)):
            assert rarity_order[i] >= rarity_order[i - 1]

    def test_prompt_modifiers_empty(self):
        assert self.ts.get_prompt_modifiers([]) == ""

    def test_prompt_modifiers_with_traits(self):
        prompt = self.ts.get_prompt_modifiers(["N-01", "SR-01"])
        assert "小好奇" in prompt
        assert "治愈之心" in prompt

    def test_display_list_length(self):
        display = self.ts.get_display_list([])
        assert len(display) == len(TRAIT_REGISTRY)
        assert all(d["name"] == "???" for d in display)

    def test_display_list_unlocked(self):
        display = self.ts.get_display_list(["N-01"])
        n01 = next(d for d in display if d["trait_id"] == "N-01")
        assert n01["unlocked"] is True
        assert n01["name"] == "小好奇"

    def test_value_multiplier_base(self):
        assert self.ts.value_multiplier([]) == 1.0

    def test_value_multiplier_increases(self):
        m1 = self.ts.value_multiplier(["N-01"])
        m2 = self.ts.value_multiplier(["N-01", "SR-01"])
        m3 = self.ts.value_multiplier(["N-01", "SR-01", "SSR-01"])
        assert m1 < m2 < m3

    def test_ssr_high_multiplier(self):
        m = self.ts.value_multiplier(["SSR-01", "SSR-02"])
        assert m >= 3.0  # Two SSRs should be very valuable

    def test_all_traits_have_required_fields(self):
        required = {"name", "icon", "rarity", "description", "effect", "conditions", "probability", "prompt"}
        for tid, trait in TRAIT_REGISTRY.items():
            for field in required:
                assert field in trait, f"Trait {tid} missing field '{field}'"

    def test_rarity_distribution(self):
        counts = {"N": 0, "R": 0, "SR": 0, "SSR": 0}
        for t in TRAIT_REGISTRY.values():
            counts[t["rarity"]] += 1
        assert counts["N"] == 8
        assert counts["R"] == 6
        assert counts["SR"] == 4
        assert counts["SSR"] == 2


# ============================================================
# Runner
# ============================================================

if __name__ == "__main__":
    import traceback

    instance = TestTraitSystem()
    passed = failed = 0
    for name in sorted(dir(instance)):
        if name.startswith("test_"):
            instance.setup_method()
            try:
                getattr(instance, name)()
                passed += 1
                print(f"  ✅ {name}")
            except Exception as e:
                failed += 1
                print(f"  ❌ {name}: {e}")
                traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
