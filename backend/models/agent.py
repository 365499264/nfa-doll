"""
NFA Doll — Pydantic 数据模型
对应 schemas/agent_state.json 的 Python 类型定义
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 枚举类型
# ============================================================

class BirthPersonality(str, Enum):
    BLANK = "blank"
    SUNNY = "sunny"
    DREAMY = "dreamy"
    SHY = "shy"
    WILD = "wild"


class Archetype(str, Enum):
    BLANK = "白纸娃娃"
    CURIOUS = "好奇宝宝"
    ANGEL = "温柔天使"
    BRAVE = "小小勇者"
    DREAMER = "幻想精灵"
    OWL = "智慧猫头鹰"
    JOKER = "开心果"
    GENIUS = "全能小天才"
    COMPLEX = "矛盾体"


class MoodType(str, Enum):
    HAPPY = "happy"
    EXCITED = "excited"
    CURIOUS = "curious"
    CALM = "calm"
    SLEEPY = "sleepy"
    SHY = "shy"
    SAD = "sad"
    CLINGY = "clingy"


class Rarity(str, Enum):
    N = "N"
    R = "R"
    SR = "SR"
    SSR = "SSR"


class MilestoneType(str, Enum):
    LEVEL_UP = "level_up"
    TRAIT_UNLOCK = "trait_unlock"
    FIRST_50 = "first_50"
    STREAK_7 = "streak_7"
    STREAK_30 = "streak_30"
    STAT_BREAKTHROUGH = "stat_breakthrough"
    PERSONALITY_SHIFT = "personality_shift"


# ============================================================
# 子模型
# ============================================================

class Meta(BaseModel):
    name: str = Field(max_length=20, description="娃娃名字")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: str = ""
    avatar_seed: int = 0
    birth_personality: BirthPersonality = BirthPersonality.BLANK
    version: int = 1


class Persona(BaseModel):
    archetype: Archetype = Archetype.BLANK
    speaking_style: str = ""
    catchphrase: str = Field(default="", max_length=30)
    interests: list[str] = Field(default_factory=list, max_length=20)
    fears: list[str] = Field(default_factory=list, max_length=10)


class Stats(BaseModel):
    curiosity: float = Field(default=10, ge=0, le=100)
    empathy: float = Field(default=10, ge=0, le=100)
    courage: float = Field(default=10, ge=0, le=100)
    creativity: float = Field(default=10, ge=0, le=100)
    wisdom: float = Field(default=10, ge=0, le=100)
    humor: float = Field(default=10, ge=0, le=100)

    def to_dict(self) -> dict[str, float]:
        return self.model_dump()

    def total(self) -> float:
        return sum(self.model_dump().values())

    def average(self) -> float:
        d = self.model_dump()
        return sum(d.values()) / len(d)

    def dominant(self) -> tuple[str, float]:
        d = self.model_dump()
        key = max(d, key=d.get)
        return key, d[key]


class Antagonism(BaseModel):
    dim_a: str
    dim_b: str
    drag_ratio: float = Field(ge=0, le=0.5)


class StatSnapshot(BaseModel):
    date: str  # YYYY-MM-DD
    stats: Stats


class Milestone(BaseModel):
    type: MilestoneType
    description: str
    timestamp: datetime
    data: dict = Field(default_factory=dict)


class Growth(BaseModel):
    level: int = Field(default=1, ge=1, le=100)
    total_exp: float = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    streak_days: int = Field(default=0, ge=0)
    last_interaction_at: Optional[datetime] = None
    stat_history: list[StatSnapshot] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)


class Decay(BaseModel):
    enabled: bool = True
    grace_period_hours: int = 72
    decay_rate_per_day: float = 0.5
    decay_floor: float = 5.0
    max_decay_per_dimension: float = 15.0


class Mood(BaseModel):
    current: MoodType = MoodType.HAPPY
    valence: float = Field(default=0.5, ge=-1, le=1)
    arousal: float = Field(default=0.5, ge=0, le=1)
    inertia: float = Field(default=0.7, ge=0, le=1)
    last_changed_at: Optional[datetime] = None


class UnlockedTrait(BaseModel):
    trait_id: str
    name: str
    rarity: Rarity
    description: str = ""
    effect: str = ""
    unlocked_at: datetime
    unlock_stats_snapshot: dict[str, float] = Field(default_factory=dict)


class Traits(BaseModel):
    unlocked: list[UnlockedTrait] = Field(default_factory=list)
    total_unlocked_count: int = 0

    def unlocked_ids(self) -> list[str]:
        return [t.trait_id for t in self.unlocked]


class ImportantFact(BaseModel):
    fact: str
    confidence: float = Field(ge=0, le=1)
    source_date: Optional[str] = None


class MemoryIndex(BaseModel):
    short_term_count: int = 0
    episodic_count: int = 0
    personality_summary: str = ""
    important_facts: list[ImportantFact] = Field(default_factory=list, max_length=50)
    last_summary_at: Optional[datetime] = None


class ChainState(BaseModel):
    token_id: Optional[int] = None
    chain: str = "bsc"
    contract_address: Optional[str] = None
    learning_enabled: bool = False
    learning_version: int = 0
    merkle_root: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    interactions_since_sync: int = 0
    vault_uri: Optional[str] = None


# ============================================================
# 顶级 Agent 状态模型
# ============================================================

class AgentState(BaseModel):
    """完整的 Agent 状态，对应链下存储的全量数据"""
    agent_id: str
    meta: Meta
    persona: Persona = Field(default_factory=Persona)
    stats: Stats = Field(default_factory=Stats)
    stat_antagonisms: list[Antagonism] = Field(default_factory=lambda: [
        Antagonism(dim_a="courage", dim_b="empathy", drag_ratio=0.25),
        Antagonism(dim_a="empathy", dim_b="courage", drag_ratio=0.25),
        Antagonism(dim_a="creativity", dim_b="wisdom", drag_ratio=0.20),
        Antagonism(dim_a="wisdom", dim_b="creativity", drag_ratio=0.20),
    ])
    growth: Growth = Field(default_factory=Growth)
    decay: Decay = Field(default_factory=Decay)
    mood: Mood = Field(default_factory=Mood)
    traits: Traits = Field(default_factory=Traits)
    memory_index: MemoryIndex = Field(default_factory=MemoryIndex)
    chain_state: ChainState = Field(default_factory=ChainState)

    @classmethod
    def create_new(cls, name: str, owner_id: str = "", birth: str = "blank") -> "AgentState":
        """工厂方法：创建一个全新的 Agent"""
        import uuid
        import random
        from ..core.personality import create_initial_stats

        agent_id = f"nfa_{uuid.uuid4().hex[:8]}"
        initial_stats = create_initial_stats(birth)

        return cls(
            agent_id=agent_id,
            meta=Meta(
                name=name,
                owner_id=owner_id,
                avatar_seed=random.randint(0, 999999),
                birth_personality=BirthPersonality(birth),
            ),
            stats=Stats(**initial_stats),
        )
