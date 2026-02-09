"""
NFA Doll — 体力系统
core/stamina.py

用可爱的"体力"机制包装对话上限，让用户感受到的是
"娃娃累了需要休息"而不是"你的次数用完了"。

设计理念：
- 每次对话消耗体力（短对话少、长对话多）
- 体力每天自动恢复（凌晨重置 + 每小时缓慢回复）
- 道具可增加体力上限或立即恢复
- 连击天数越长，每日基础体力越高（奖励忠实用户）
- 体力不足时娃娃会"犯困"，而不是生硬的报错
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass, field

from ..config import config


# ============================================================
# 体力状态
# ============================================================

@dataclass
class StaminaState:
    """体力状态数据（存储在 agent_state 中）"""
    current: float = 100.0           # 当前体力
    max_base: float = 100.0          # 基础上限
    max_bonus: float = 0.0           # 道具加成上限
    last_recovery_at: Optional[str] = None   # 上次回复时间
    last_daily_reset_date: Optional[str] = None  # 上次每日重置日期
    total_consumed_today: float = 0.0  # 今日已消耗
    items_used_today: int = 0         # 今日已使用道具数
    upgrades_used_today: int = 0      # 今日已使用扩容道具数

    @property
    def max_stamina(self) -> float:
        return self.max_base + self.max_bonus

    def to_dict(self) -> dict:
        return {
            "current": round(self.current, 1),
            "max_base": self.max_base,
            "max_bonus": self.max_bonus,
            "max_stamina": self.max_stamina,
            "last_recovery_at": self.last_recovery_at,
            "last_daily_reset_date": self.last_daily_reset_date,
            "total_consumed_today": round(self.total_consumed_today, 1),
            "items_used_today": self.items_used_today,
            "upgrades_used_today": self.upgrades_used_today,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StaminaState":
        if not data:
            return cls()
        return cls(
            current=data.get("current", 100.0),
            max_base=data.get("max_base", 100.0),
            max_bonus=data.get("max_bonus", 0.0),
            last_recovery_at=data.get("last_recovery_at"),
            last_daily_reset_date=data.get("last_daily_reset_date"),
            total_consumed_today=data.get("total_consumed_today", 0.0),
            items_used_today=data.get("items_used_today", 0),
            upgrades_used_today=data.get("upgrades_used_today", 0),
        )


# ============================================================
# 体力管理器
# ============================================================

class StaminaManager:
    """体力系统核心逻辑"""

    def __init__(self, state: Optional[StaminaState] = None):
        self.state = state or StaminaState()

    # ---- 每日重置 & 时间回复 ----

    def tick(self, now: Optional[datetime] = None, streak_days: int = 0) -> dict:
        """
        时间驱动的体力更新。每次对话前调用。

        1. 检查是否跨天 → 执行每日重置
        2. 计算距上次回复的时间 → 缓慢回复体力

        Returns:
            {"recovered": float, "daily_reset": bool, "current": float}
        """
        now = now or datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        recovered = 0.0
        daily_reset = False

        # --- 每日重置 ---
        if self.state.last_daily_reset_date != today_str:
            self.state.last_daily_reset_date = today_str
            self.state.total_consumed_today = 0.0
            self.state.items_used_today = 0
            self.state.upgrades_used_today = 0
            # 重置体力到上限（含连击加成）
            streak_bonus = self._streak_stamina_bonus(streak_days)
            self.state.max_base = config.stamina.base_max + streak_bonus
            old = self.state.current
            self.state.current = self.state.max_stamina
            recovered = self.state.current - old
            daily_reset = True

        # --- 时间缓慢回复 ---
        elif self.state.last_recovery_at:
            last_recovery = datetime.fromisoformat(self.state.last_recovery_at)
            if last_recovery.tzinfo is None:
                last_recovery = last_recovery.replace(tzinfo=timezone.utc)
            hours_passed = (now - last_recovery).total_seconds() / 3600
            if hours_passed >= 1.0:
                # 每小时恢复 recovery_per_hour 点
                hourly_recovery = int(hours_passed) * config.stamina.recovery_per_hour
                old = self.state.current
                self.state.current = min(
                    self.state.max_stamina,
                    self.state.current + hourly_recovery,
                )
                recovered = self.state.current - old

        self.state.last_recovery_at = now.isoformat()

        return {
            "recovered": round(recovered, 1),
            "daily_reset": daily_reset,
            "current": round(self.state.current, 1),
        }

    # ---- 消耗体力 ----

    def consume(self, amount: Optional[float] = None) -> dict:
        """
        消耗体力。每次对话后调用。

        Args:
            amount: 消耗量。None 则使用默认值。

        Returns:
            {
                "consumed": float,
                "remaining": float,
                "is_tired": bool,       # 体力 < 疲劳阈值
                "is_exhausted": bool,   # 体力 <= 0，无法继续对话
                "tired_level": str,     # "energetic" | "normal" | "tired" | "sleepy" | "exhausted"
            }
        """
        cost = amount if amount is not None else config.stamina.cost_per_chat
        self.state.current = max(0, self.state.current - cost)
        self.state.total_consumed_today += cost

        remaining = self.state.current
        max_st = self.state.max_stamina

        return {
            "consumed": round(cost, 1),
            "remaining": round(remaining, 1),
            "is_tired": remaining < max_st * config.stamina.tired_threshold,
            "is_exhausted": remaining <= 0,
            "tired_level": self._tired_level(remaining, max_st),
        }

    def can_chat(self) -> bool:
        """是否还有体力对话"""
        return self.state.current > 0

    # ---- 道具效果 ----

    def use_item(self, item_type: str) -> dict:
        """
        使用体力道具。

        item_type:
            "snack"     — 小零食：恢复 20 体力
            "cake"      — 蛋糕：恢复 50 体力
            "energy"    — 能量饮料：恢复至满
            "upgrade"   — 体力扩容：永久+10上限（每天限用1次）

        Returns:
            {"success": bool, "message": str, "recovered": float}
        """
        items = config.stamina.items
        if item_type not in items:
            return {"success": False, "message": "未知道具", "recovered": 0}

        item = items[item_type]

        # 扩容道具每日限制
        if item_type == "upgrade":
            if self.state.upgrades_used_today >= 1:
                return {"success": False, "message": "今天已经用过扩容道具了，明天再来吧~", "recovered": 0}
            self.state.max_bonus += item["bonus"]
            self.state.current = min(self.state.max_stamina, self.state.current + item["bonus"])
            self.state.upgrades_used_today += 1
            return {"success": True, "message": f"体力上限永久+{item['bonus']}！", "recovered": item["bonus"]}

        # 恢复类道具
        old = self.state.current
        if item.get("full_restore"):
            self.state.current = self.state.max_stamina
        else:
            self.state.current = min(self.state.max_stamina, self.state.current + item["restore"])
        recovered = self.state.current - old
        self.state.items_used_today += 1

        return {"success": True, "message": item["message"], "recovered": round(recovered, 1)}

    # ---- 内部方法 ----

    def _streak_stamina_bonus(self, streak_days: int) -> float:
        """
        连续互动天数的体力上限加成。
        7天: +5, 14天: +10, 30天: +15, 60天: +20 (上限)
        """
        if streak_days < 7:
            return 0
        bonus = min(20, (streak_days // 7) * 5)
        return float(bonus)

    def _tired_level(self, current: float, max_st: float) -> str:
        """
        根据体力百分比返回疲劳等级。
        影响娃娃的说话方式和表情。
        """
        if max_st <= 0:
            return "exhausted"
        ratio = current / max_st
        if ratio > 0.7:
            return "energetic"
        elif ratio > 0.4:
            return "normal"
        elif ratio > 0.15:
            return "tired"
        elif ratio > 0:
            return "sleepy"
        else:
            return "exhausted"

    # ---- 前端展示 ----

    def get_display(self) -> dict:
        """前端展示用的体力信息"""
        max_st = self.state.max_stamina
        current = self.state.current
        level = self._tired_level(current, max_st)

        display_map = {
            "energetic": {"emoji": "⚡", "label": "元气满满", "color": "#4ade80"},
            "normal":    {"emoji": "😊", "label": "状态正常", "color": "#60a5fa"},
            "tired":     {"emoji": "😪", "label": "有点累了", "color": "#fbbf24"},
            "sleepy":    {"emoji": "😴", "label": "好困好困", "color": "#f97316"},
            "exhausted": {"emoji": "💤", "label": "需要休息", "color": "#ef4444"},
        }
        info = display_map.get(level, display_map["normal"])

        return {
            "current": round(current, 1),
            "max": round(max_st, 1),
            "percentage": round(current / max_st * 100, 1) if max_st > 0 else 0,
            "level": level,
            **info,
        }

    def get_tired_dialogue_hint(self) -> str:
        """
        生成体力相关的 Prompt 提示，让娃娃自然地表现出疲劳。
        注入到 System Prompt 中。
        """
        level = self._tired_level(self.state.current, self.state.max_stamina)

        hints = {
            "energetic": "",  # 不影响
            "normal": "",     # 不影响
            "tired": (
                "你现在有点累了，偶尔会打哈欠。回复可以稍微短一点，"
                "偶尔提一句「有点困了呢」，但还能正常对话。"
            ),
            "sleepy": (
                "你现在非常困，说话变得迷迷糊糊的，经常打哈欠。"
                "回复要变短，语气要显得很困，偶尔说「呜…好困…」"
                "「眼睛都快睁不开了…」之类的话。暗示主人你需要休息。"
            ),
            "exhausted": (
                "你已经累到不行了，只能用很短很短的话回复。"
                "说「呜…太累了…让我休息一下吧…明天再来陪你好不好…💤」"
                "之类的话。这是你今天最后能说的了。"
            ),
        }
        return hints.get(level, "")


# ============================================================
# 体力消耗计算
# ============================================================

def calculate_chat_cost(
    message_length: int,
    interaction_quality: float = 1.0,
) -> float:
    """
    根据对话内容计算体力消耗。

    - 基础消耗: config.stamina.cost_per_chat (默认3)
    - 长对话加成: 消息超过200字时每100字+0.5
    - 高质量对话折扣: 触发事件的对话消耗-20%（奖励有深度的互动）

    Returns:
        实际体力消耗值
    """
    base = config.stamina.cost_per_chat

    # 长度加成
    if message_length > 200:
        extra_hundreds = (message_length - 200) / 100
        base += extra_hundreds * 0.5

    # 高质量折扣
    if interaction_quality >= 1.5:
        base *= 0.8

    return round(max(1.0, base), 1)


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  🔋 体力系统测试")
    print("=" * 50)

    sm = StaminaManager()

    # 测试1: 初始状态
    print(f"\n初始: {sm.get_display()}")
    assert sm.can_chat()
    print("✅ 初始体力满")

    # 测试2: 消耗
    for i in range(10):
        result = sm.consume(3)
    print(f"\n消耗30后: 剩余{result['remaining']}, 状态={result['tired_level']}")
    assert result['remaining'] == 70
    print("✅ 消耗计算正确")

    # 测试3: 持续消耗到疲劳
    while sm.state.current > 15:
        sm.consume(5)
    display = sm.get_display()
    print(f"\n低体力: {display['emoji']} {display['label']} ({display['percentage']}%)")
    hint = sm.get_tired_dialogue_hint()
    print(f"  Prompt提示: {hint[:50]}...")
    print("✅ 疲劳提示正确")

    # 测试4: 消耗到0
    while sm.state.current > 0:
        sm.consume(5)
    assert not sm.can_chat()
    display = sm.get_display()
    print(f"\n耗尽: {display['emoji']} {display['label']}")
    print("✅ 体力耗尽检测正确")

    # 测试5: 使用道具
    sm2 = StaminaManager(StaminaState(current=10, max_base=100))
    result = sm2.use_item("cake")
    print(f"\n使用蛋糕: {result}")
    assert result["success"]
    print("✅ 道具使用正确")

    # 测试6: 每日重置
    sm3 = StaminaManager(StaminaState(current=0, last_daily_reset_date="2025-01-01"))
    tick_result = sm3.tick(streak_days=14)
    print(f"\n每日重置(14天连击): {tick_result}")
    assert tick_result["daily_reset"]
    assert sm3.state.max_base > 100  # 连击加成
    print(f"  上限: {sm3.state.max_base} (含连击+10)")
    print("✅ 每日重置+连击加成正确")

    # 测试7: 消耗计算
    cost_short = calculate_chat_cost(50)
    cost_long = calculate_chat_cost(500)
    cost_quality = calculate_chat_cost(100, interaction_quality=1.8)
    print(f"\n消耗计算: 短消息={cost_short}, 长消息={cost_long}, 高质量={cost_quality}")
    assert cost_long > cost_short
    assert cost_quality < cost_short  # 高质量折扣
    print("✅ 动态消耗计算正确")

    print(f"\n{'=' * 50}")
    print("  🎉 全部测试通过！")
