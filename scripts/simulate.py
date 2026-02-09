#!/usr/bin/env python3
"""
NFA Doll — 数值平衡模拟器

模拟 N 个用户，每个进行 M 次互动，分析最终数值分布。
用于验证成长曲线、互斥对抗、衰减机制的平衡性。

用法:
    python scripts/simulate.py                    # 默认 500 用户 × 200 次互动
    python scripts/simulate.py --users 1000 --rounds 500
"""

import sys
import os
import random
import argparse
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.personality import (
    create_initial_stats, process_interaction, determine_archetype,
    STAT_KEYS, STAT_LABELS, exp_required_for_level,
)
from backend.core.traits import trait_system


# 模拟不同类型的用户互动风格
USER_PROFILES = {
    "好奇型": {"curiosity": (3, 7), "wisdom": (1, 3)},
    "温柔型": {"empathy": (3, 7), "humor": (1, 2)},
    "勇敢型": {"courage": (3, 7), "creativity": (1, 3)},
    "创意型": {"creativity": (3, 7), "curiosity": (1, 2)},
    "学霸型": {"wisdom": (3, 7), "curiosity": (1, 3)},
    "搞笑型": {"humor": (3, 7), "courage": (1, 2)},
    "均衡型": {"curiosity": (1, 3), "empathy": (1, 3), "courage": (1, 3), "creativity": (1, 3), "wisdom": (1, 3), "humor": (1, 3)},
    "随机型": {},  # 每次随机
}


def random_changes(profile_name: str) -> dict:
    """根据用户画像生成随机的stat变化"""
    profile = USER_PROFILES.get(profile_name, {})
    changes = {}

    if not profile:  # 随机型
        # 随机选 1-3 个维度
        dims = random.sample(STAT_KEYS, random.randint(1, 3))
        for d in dims:
            changes[d] = random.uniform(1, 5)
    else:
        for dim, (lo, hi) in profile.items():
            if random.random() < 0.8:  # 80%概率触发
                changes[dim] = random.uniform(lo, hi)

    return changes


def simulate_one_user(profile_name: str, num_rounds: int) -> dict:
    """模拟一个用户的完整养成过程"""
    stats = create_initial_stats("blank")
    growth = {
        "level": 1, "total_exp": 0, "total_interactions": 0,
        "streak_days": 1, "last_interaction_at": None, "archetype": "白纸娃娃",
    }
    unlocked_traits = []

    for _ in range(num_rounds):
        changes = random_changes(profile_name)
        quality = random.choice([0.8, 1.0, 1.0, 1.2, 1.5])

        result = process_interaction(stats, growth, changes, quality)
        stats = result["stats"]
        growth = result["growth"]

        # 检查特质
        trait = trait_system.check_and_unlock(stats, unlocked_traits, growth)
        if trait:
            unlocked_traits.append(trait["trait_id"])

    return {
        "profile": profile_name,
        "stats": stats,
        "level": growth["level"],
        "archetype": determine_archetype(stats),
        "traits": unlocked_traits,
        "trait_count": len(unlocked_traits),
        "value_mult": trait_system.value_multiplier(unlocked_traits),
    }


def run_simulation(num_users: int = 500, num_rounds: int = 200) -> None:
    print(f"\n{'='*60}")
    print(f"  🧪 NFA Doll 数值平衡模拟")
    print(f"  用户数: {num_users}  |  每人互动: {num_rounds} 轮")
    print(f"{'='*60}")

    profiles = list(USER_PROFILES.keys())
    results = []

    for i in range(num_users):
        profile = profiles[i % len(profiles)]
        result = simulate_one_user(profile, num_rounds)
        results.append(result)

    # ---- 统计分析 ----

    # 1. 各维度分布
    print(f"\n📊 各维度最终数值分布 (n={num_users}):")
    for key in STAT_KEYS:
        values = [r["stats"][key] for r in results]
        avg = sum(values) / len(values)
        mn, mx = min(values), max(values)
        # 简单直方图
        buckets = [0] * 10  # 0-10, 10-20, ..., 90-100
        for v in values:
            idx = min(9, int(v / 10))
            buckets[idx] += 1
        bar = " ".join(f"{b:3d}" for b in buckets)
        print(f"  {STAT_LABELS[key]:12s}  avg={avg:5.1f}  min={mn:5.1f}  max={mx:5.1f}  [{bar}]")

    # 2. 等级分布
    print(f"\n📈 等级分布:")
    levels = [r["level"] for r in results]
    level_counter = Counter()
    for lv in levels:
        bucket = f"Lv.{(lv // 5) * 5 + 1}-{(lv // 5) * 5 + 5}"
        level_counter[bucket] += 1
    for bucket in sorted(level_counter.keys()):
        count = level_counter[bucket]
        bar = "█" * (count * 40 // num_users)
        print(f"  {bucket:12s} {bar} {count}")

    # 3. 性格类型分布
    print(f"\n🎭 性格类型分布:")
    arch_counter = Counter(r["archetype"] for r in results)
    for arch, count in arch_counter.most_common():
        pct = count * 100 / num_users
        bar = "█" * int(pct / 2)
        print(f"  {arch:10s} {bar} {count} ({pct:.1f}%)")

    # 4. 特质解锁统计
    print(f"\n✨ 特质解锁统计:")
    trait_counts = [r["trait_count"] for r in results]
    avg_traits = sum(trait_counts) / len(trait_counts)
    print(f"  平均解锁特质数: {avg_traits:.1f}")

    all_traits = []
    for r in results:
        all_traits.extend(r["traits"])
    trait_counter = Counter(all_traits)

    rarity_groups = {"N": [], "R": [], "SR": [], "SSR": []}
    for tid, count in trait_counter.most_common():
        info = trait_system.registry.get(tid, {})
        rarity = info.get("rarity", "?")
        pct = count * 100 / num_users
        rarity_groups.setdefault(rarity, []).append((info.get("name", tid), pct))

    for rarity in ["N", "R", "SR", "SSR"]:
        items = rarity_groups.get(rarity, [])
        if items:
            print(f"  [{rarity}]")
            for name, pct in sorted(items, key=lambda x: -x[1]):
                bar = "█" * int(pct / 2)
                print(f"    {name:10s} {bar} {pct:.1f}%")

    # 5. 交易价值分布
    print(f"\n💰 交易价值乘数分布:")
    mults = [r["value_mult"] for r in results]
    avg_mult = sum(mults) / len(mults)
    print(f"  平均: ×{avg_mult:.2f}  最低: ×{min(mults):.2f}  最高: ×{max(mults):.2f}")

    # 6. 互斥对抗效果验证
    print(f"\n⚔️ 互斥对抗效果:")
    courage_vals = [r["stats"]["courage"] for r in results]
    empathy_vals = [r["stats"]["empathy"] for r in results]
    creativity_vals = [r["stats"]["creativity"] for r in results]
    wisdom_vals = [r["stats"]["wisdom"] for r in results]

    # 计算相关系数（简化版）
    def correlation(x, y):
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
        sx = (sum((xi - mx) ** 2 for xi in x) / n) ** 0.5
        sy = (sum((yi - my) ** 2 for yi in y) / n) ** 0.5
        return cov / (sx * sy) if sx * sy > 0 else 0

    print(f"  勇气 ↔ 共情力: r = {correlation(courage_vals, empathy_vals):.3f} (期望负相关)")
    print(f"  创造力 ↔ 智慧: r = {correlation(creativity_vals, wisdom_vals):.3f} (期望负相关)")
    print(f"  好奇心 ↔ 幽默: r = {correlation([r['stats']['curiosity'] for r in results], [r['stats']['humor'] for r in results]):.3f} (期望无相关)")

    print(f"\n{'='*60}")
    print(f"  ✅ 模拟完成")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="NFA Doll 数值平衡模拟器")
    parser.add_argument("--users", type=int, default=500, help="模拟用户数量")
    parser.add_argument("--rounds", type=int, default=200, help="每用户互动轮数")
    args = parser.parse_args()
    run_simulation(args.users, args.rounds)


if __name__ == "__main__":
    main()
