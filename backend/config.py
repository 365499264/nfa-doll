"""
NFA Doll — 全局配置
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PersonalityConfig:
    """性格系统配置"""
    stat_min: float = 0
    stat_max: float = 100
    stat_keys: tuple = ("curiosity", "empathy", "courage", "creativity", "wisdom", "humor")
    antagonisms: tuple = (
        ("courage", "empathy", 0.25),
        ("empathy", "courage", 0.25),
        ("creativity", "wisdom", 0.20),
        ("wisdom", "creativity", 0.20),
    )


@dataclass(frozen=True)
class DecayConfig:
    """衰减配置"""
    enabled: bool = True
    grace_period_hours: int = 72
    decay_rate_per_day: float = 0.5
    decay_floor: float = 5.0
    max_decay_per_dimension: float = 15.0


@dataclass(frozen=True)
class GrowthConfig:
    """成长配置"""
    max_level: int = 100
    exp_base: float = 8.0
    exp_exponent: float = 2.2
    base_exp_per_interaction: float = 5.0
    max_streak_bonus: float = 1.5
    streak_continuity_hours: int = 48


@dataclass(frozen=True)
class LLMConfig:
    """LLM 调用配置 (Claude only)"""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 800
    temperature: float = 0.85
    conversation_window: int = 20
    stream: bool = True
    timeout: float = 30.0
    max_retries: int = 2


@dataclass
class StaminaConfig:
    """
    体力系统配置

    设计: 100体力 / 3消耗每次 ≈ 33轮/天
    用户看到的是娃娃越来越困，不是"次数用完"
    """
    base_max: float = 100.0
    cost_per_chat: float = 3.0
    recovery_per_hour: float = 2.0
    tired_threshold: float = 0.3
    items_per_day_limit: int = 5
    items: dict = None

    def __post_init__(self):
        if self.items is None:
            self.items = {
                "snack": {
                    "name": "小零食 🍪",
                    "description": "恢复少量体力",
                    "restore": 20,
                    "message": "嗷呜~好好吃！感觉有力气了！",
                },
                "cake": {
                    "name": "草莓蛋糕 🍰",
                    "description": "恢复大量体力",
                    "restore": 50,
                    "message": "哇！草莓蛋糕！最喜欢了！元气恢复～",
                },
                "energy": {
                    "name": "元气药水 ✨",
                    "description": "完全恢复体力",
                    "full_restore": True,
                    "restore": 0,
                    "message": "咕噜咕噜…哇！满血复活！我又可以了！",
                },
                "upgrade": {
                    "name": "成长果实 🍎",
                    "description": "永久增加10点体力上限",
                    "bonus": 10,
                    "message": "感觉身体变强了！可以陪主人更久了！",
                },
            }


@dataclass
class AppConfig:
    """应用配置入口"""
    personality: PersonalityConfig = None
    decay: DecayConfig = None
    growth: GrowthConfig = None
    llm: LLMConfig = None
    stamina: StaminaConfig = None

    def __post_init__(self):
        if self.personality is None:
            self.personality = PersonalityConfig()
        if self.decay is None:
            self.decay = DecayConfig()
        if self.growth is None:
            self.growth = GrowthConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.stamina is None:
            self.stamina = StaminaConfig()


# 全局默认配置实例
config = AppConfig()
