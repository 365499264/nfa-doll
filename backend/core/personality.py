"""
NFA Doll — 性格成长系统
core/personality.py

包含：等级曲线、性格增长（含互斥对抗+递减收益）、衰减、性格类型判定、说话风格生成
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import config

# ============================================================
# 常量
# ============================================================

STAT_KEYS = list(config.personality.stat_keys)

STAT_LABELS = {
    "curiosity": "好奇心 🔍",
    "empathy": "共情力 💗",
    "courage": "勇气 ⚡",
    "creativity": "创造力 🎨",
    "wisdom": "智慧 📚",
    "humor": "幽默感 😄",
}

ARCHETYPES = {
    "blank":   "白纸娃娃",
    "curious": "好奇宝宝",
    "angel":   "温柔天使",
    "brave":   "小小勇者",
    "dreamer": "幻想精灵",
    "owl":     "智慧猫头鹰",
    "joker":   "开心果",
    "genius":  "全能小天才",
    "complex": "矛盾体",
}

BIRTH_PERSONALITIES = {
    "blank":  {"curiosity": 10, "empathy": 10, "courage": 10, "creativity": 10, "wisdom": 10, "humor": 10},
    "sunny":  {"curiosity": 18, "empathy": 15, "courage": 12, "creativity": 10, "wisdom": 8,  "humor": 22},
    "dreamy": {"curiosity": 12, "empathy": 18, "courage": 6,  "creativity": 22, "wisdom": 10, "humor": 10},
    "shy":    {"curiosity": 8,  "empathy": 22, "courage": 5,  "creativity": 15, "wisdom": 12, "humor": 8},
    "wild":   {"curiosity": 20, "empathy": 6,  "courage": 22, "creativity": 15, "wisdom": 8,  "humor": 14},
}


# ============================================================
# 等级与经验值
# ============================================================

def exp_required_for_level(level: int) -> float:
    """升到指定等级所需的累计经验值。Lv10→1268, Lv50→43734, Lv100→200951"""
    if level <= 1:
        return 0
    return config.growth.exp_base * (level ** config.growth.exp_exponent)


def level_from_exp(total_exp: float) -> int:
    """根据累计经验值反推等级。"""
    level = 1
    while level < config.growth.max_level:
        if total_exp < exp_required_for_level(level + 1):
            break
        level += 1
    return level


def exp_for_interaction(level: int, quality: float = 1.0) -> float:
    """单次互动获得的经验。quality: 0.5(低质量) ~ 2.0(触发事件)"""
    base = config.growth.base_exp_per_interaction
    level_bonus = 1.0 + level * 0.01
    return base * level_bonus * max(0.5, min(2.0, quality))


def exp_progress(total_exp: float, level: int) -> float:
    """当前等级内的进度 0.0~1.0"""
    cur = exp_required_for_level(level)
    nxt = exp_required_for_level(level + 1)
    return (total_exp - cur) / max(1, nxt - cur)


def streak_bonus(streak_days: int) -> float:
    """连续互动天数经验加成。1天→1.0x, 7天→1.2x, 30天→1.5x"""
    if streak_days <= 1:
        return 1.0
    bonus = 1.0 + 0.5 * (1 - math.exp(-0.05 * streak_days))
    return min(config.growth.max_streak_bonus, round(bonus, 2))


# ============================================================
# 递减收益
# ============================================================

def diminishing_return(current: float) -> float:
    """数值越高增长效率越低。x=0→0.98, x=50→0.50, x=80→0.08"""
    return 1.0 / (1.0 + math.exp(0.08 * (current - 50)))


# ============================================================
# 性格数值增长（含互斥对抗）
# ============================================================

def apply_stat_growth(
    current: dict[str, float],
    raw_changes: dict[str, float],
    level: int = 1,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    应用性格数值变化。

    Returns: (new_stats, actual_deltas)
    """
    # Step 1: 递减收益
    effective = {}
    for key in STAT_KEYS:
        raw = raw_changes.get(key, 0)
        if raw > 0:
            effective[key] = raw * diminishing_return(current.get(key, 0))
        else:
            effective[key] = raw

    # Step 2: 互斥对抗拖拽
    drags = {k: 0.0 for k in STAT_KEYS}
    for dim_a, dim_b, ratio in config.personality.antagonisms:
        change_a = effective.get(dim_a, 0)
        if change_a > 0:
            drags[dim_b] -= change_a * ratio

    # Step 3: 合并并钳位
    new_stats = {}
    deltas = {}
    for key in STAT_KEYS:
        old_val = current.get(key, 0)
        total = effective.get(key, 0) + drags[key]
        new_val = _clamp(old_val + total, config.personality.stat_min, config.personality.stat_max)
        new_stats[key] = round(new_val, 1)
        deltas[key] = round(new_val - old_val, 1)

    return new_stats, deltas


# ============================================================
# 衰减
# ============================================================

def calculate_decay(
    stats: dict[str, float],
    last_interaction: Optional[datetime],
    now: Optional[datetime] = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """温和衰减。3天宽限 → 每天-0.5 → 最低5 → 单维度最多-15"""
    cfg = config.decay
    if not cfg.enabled or last_interaction is None:
        return dict(stats), {k: 0.0 for k in STAT_KEYS}

    now = now or datetime.now(timezone.utc)
    last = last_interaction.replace(tzinfo=timezone.utc) if last_interaction.tzinfo is None else last_interaction
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now

    hours = (now - last).total_seconds() / 3600
    if hours <= cfg.grace_period_hours:
        return dict(stats), {k: 0.0 for k in STAT_KEYS}

    decay_days = (hours - cfg.grace_period_hours) / 24
    result = {}
    amounts = {}
    for key in STAT_KEYS:
        cur = stats.get(key, 0)
        total_decay = min(decay_days * cfg.decay_rate_per_day, cfg.max_decay_per_dimension)
        new_val = max(cfg.decay_floor, cur - total_decay)
        result[key] = round(new_val, 1)
        amounts[key] = round(new_val - cur, 1)

    return result, amounts


# ============================================================
# 性格类型判定
# ============================================================

def determine_archetype(stats: dict[str, float]) -> str:
    """返回中文性格类型名。"""
    values = [stats.get(k, 0) for k in STAT_KEYS]
    high_count = sum(1 for v in values if v > 60)
    sorted_vals = sorted(values, reverse=True)

    if high_count >= 4:
        return ARCHETYPES["genius"]

    if (stats.get("courage", 0) > 55 and stats.get("empathy", 0) > 55) or \
       (stats.get("creativity", 0) > 55 and stats.get("wisdom", 0) > 55):
        return ARCHETYPES["complex"]

    if all(v < 25 for v in values):
        return ARCHETYPES["blank"]

    max_val = sorted_vals[0]
    if max_val >= 30:
        dominant_key = STAT_KEYS[values.index(max_val)]
        mapping = {
            "curiosity": "curious", "empathy": "angel", "courage": "brave",
            "creativity": "dreamer", "wisdom": "owl", "humor": "joker",
        }
        return ARCHETYPES.get(mapping.get(dominant_key, "blank"), ARCHETYPES["blank"])

    return ARCHETYPES["blank"]


# ============================================================
# 说话风格生成
# ============================================================

def generate_speaking_style(stats: dict[str, float], level: int) -> str:
    """根据性格数值和等级生成说话风格描述（用于 System Prompt）。"""
    parts = []

    if level <= 5:
        parts.append("说话非常稚嫩可爱，像刚学会说话的小孩，经常用叠词")
    elif level <= 15:
        parts.append("说话可爱但开始有小个性了")
    elif level <= 30:
        parts.append("说话有明显的个人风格，表达越来越丰富")
    elif level <= 60:
        parts.append("说话成熟但保持可爱感，能进行有深度的对话")
    else:
        parts.append("说话兼具智慧和可爱，像一个温暖聪明的伙伴")

    thresholds = [
        ("curiosity", 60, "爱问「为什么」和「这是什么」", 35, "对新事物会表现出兴趣"),
        ("empathy", 60, "善于察觉主人的情绪变化，会主动关心", 35, "会对主人的感受做出回应"),
        ("courage", 60, "说话大胆直率，会主动提出新尝试", 35, "偶尔会勇敢地表达自己的想法"),
        ("creativity", 60, "经常天马行空地联想，喜欢编故事", 35, "偶尔会冒出有趣的想象"),
        ("wisdom", 60, "喜欢分析事情的道理，偶尔说出有深度的话", 35, "能做简单的思考和推理"),
        ("humor", 60, "爱开玩笑，说话很俏皮，经常制造笑点", 35, "偶尔会说些可爱的俏皮话"),
    ]

    for key, high_th, high_desc, low_th, low_desc in thresholds:
        val = stats.get(key, 0)
        if val > high_th:
            parts.append(high_desc)
        elif val > low_th:
            parts.append(low_desc)

    # 互斥维度同时高
    if stats.get("courage", 0) > 55 and stats.get("empathy", 0) > 55:
        parts.append("既勇敢又温柔，有时在直率和体贴之间纠结")
    if stats.get("creativity", 0) > 55 and stats.get("wisdom", 0) > 55:
        parts.append("想象力和理性并存，能把天马行空的想法讲得很有逻辑")

    return "；".join(parts) + "。"


# ============================================================
# 初始性格种子
# ============================================================

def create_initial_stats(birth: str = "blank") -> dict[str, float]:
    """创建初始性格数值（含 ±2 随机扰动）。"""
    base = BIRTH_PERSONALITIES.get(birth, BIRTH_PERSONALITIES["blank"])
    return {
        k: round(_clamp(base[k] + random.uniform(-2, 2), 0, 100), 1)
        for k in STAT_KEYS
    }


# ============================================================
# 完整单次互动更新
# ============================================================

def process_interaction(
    stats: dict[str, float],
    growth_data: dict,
    raw_stat_changes: dict[str, float],
    interaction_quality: float = 1.0,
    now: Optional[datetime] = None,
) -> dict:
    """
    主入口：处理一次完整互动更新。

    Args:
        stats: 当前六维数值 dict
        growth_data: {"level", "total_exp", "total_interactions", "streak_days", "last_interaction_at"}
        raw_stat_changes: AI 返回的原始变化值
        interaction_quality: 0.5~2.0
        now: 当前时间

    Returns:
        {
            "stats": dict,           # 更新后数值
            "growth": dict,          # 更新后成长数据
            "deltas": dict,          # 实际变化量
            "events": list[dict],    # 触发的事件
            "exp_gained": float,
            "leveled_up": bool,
            "archetype": str,        # 当前性格类型
            "archetype_changed": bool,
        }
    """
    now = now or datetime.now(timezone.utc)
    events = []

    # 1. 衰减
    last_str = growth_data.get("last_interaction_at")
    last_dt = None
    if last_str:
        last_dt = datetime.fromisoformat(last_str) if isinstance(last_str, str) else last_str
    stats, _ = calculate_decay(stats, last_dt, now)

    # 2. 性格数值变化
    old_stats = dict(stats)
    stats, deltas = apply_stat_growth(stats, raw_stat_changes, growth_data.get("level", 1))

    # 3. 经验值和等级
    old_level = growth_data.get("level", 1)
    bonus = streak_bonus(growth_data.get("streak_days", 0))
    exp_gained = exp_for_interaction(old_level, interaction_quality) * bonus
    total_exp = growth_data.get("total_exp", 0) + exp_gained
    new_level = level_from_exp(total_exp)
    leveled_up = new_level > old_level
    if leveled_up:
        events.append({"type": "level_up", "description": f"升级到 Lv.{new_level}！", "data": {"old": old_level, "new": new_level}})

    # 4. 连击
    total_interactions = growth_data.get("total_interactions", 0) + 1
    streak = growth_data.get("streak_days", 0)
    if last_dt:
        gap_h = (now - (last_dt.replace(tzinfo=timezone.utc) if last_dt.tzinfo is None else last_dt)).total_seconds() / 3600
        if gap_h <= config.growth.streak_continuity_hours:
            if last_dt.date() < now.date():
                streak += 1
        else:
            streak = 1
    else:
        streak = 1

    if streak == 7:
        events.append({"type": "streak_7", "description": "连续互动 7 天！好有毅力！"})
    elif streak == 30:
        events.append({"type": "streak_30", "description": "连续互动 30 天！你是最棒的主人！"})
    if total_interactions == 50:
        events.append({"type": "first_50", "description": "第 50 次对话！感谢你的陪伴～"})

    # 5. 性格类型
    old_archetype = growth_data.get("archetype", "白纸娃娃")
    new_archetype = determine_archetype(stats)
    archetype_changed = old_archetype != new_archetype
    if archetype_changed:
        events.append({"type": "personality_shift", "description": f"性格变化: {old_archetype} → {new_archetype}"})

    # 6. 数值突破
    for key in STAT_KEYS:
        for th in [30, 50, 70, 90]:
            if old_stats.get(key, 0) < th <= stats[key]:
                events.append({"type": "stat_breakthrough", "description": f"{STAT_LABELS[key]} 突破 {th}！", "data": {"stat": key, "threshold": th}})

    growth_out = {
        "level": new_level,
        "total_exp": total_exp,
        "total_interactions": total_interactions,
        "streak_days": streak,
        "last_interaction_at": now.isoformat(),
        "archetype": new_archetype,
    }

    return {
        "stats": stats,
        "growth": growth_out,
        "deltas": deltas,
        "events": events,
        "exp_gained": round(exp_gained, 1),
        "leveled_up": leveled_up,
        "archetype": new_archetype,
        "archetype_changed": archetype_changed,
        "speaking_style": generate_speaking_style(stats, new_level),
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
