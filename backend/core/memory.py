"""
NFA Doll — 三层记忆系统
core/memory.py

短期记忆: 最近 N 轮对话（内存）
情景记忆: 重要事件摘要（待接 DB）
长期记忆: 性格数值+行为模式（Agent State 自身）

Phase 1.3 将实现完整的持久化和向量检索。
当前版本提供内存实现，接口已为数据库做好准备。
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# 短期记忆（对话窗口）
# ============================================================

@dataclass
class ConversationTurn:
    """单轮对话"""
    role: str           # "user" | "assistant"
    content: str
    timestamp: float = 0.0
    emotion_tag: str = "neutral"
    topics: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class ShortTermMemory:
    """短期记忆：滑动窗口保留最近 N 轮对话"""

    def __init__(self, max_turns: int = 40):
        self.max_turns = max_turns
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)
        self._session_start: Optional[float] = None

    def add(self, role: str, content: str, **kwargs) -> None:
        self._turns.append(ConversationTurn(role=role, content=content, **kwargs))

    def get_recent(self, n: int = 20) -> list[dict]:
        """获取最近 n 轮对话（LLM 上下文格式）"""
        recent = list(self._turns)[-n:]
        return [t.to_dict() for t in recent]

    def get_all(self) -> list[ConversationTurn]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()

    @property
    def count(self) -> int:
        return len(self._turns)

    def start_session(self) -> None:
        self._session_start = time.time()

    def end_session(self) -> list[ConversationTurn]:
        """结束会话，返回本次会话的所有对话"""
        turns = list(self._turns)
        self._session_start = None
        return turns


# ============================================================
# 情景记忆（重要事件）
# ============================================================

@dataclass
class EpisodicEvent:
    """情景记忆条目"""
    event_type: str       # "emotional_peak" | "milestone" | "topic_deep_dive" | "user_fact"
    summary: str          # 事件摘要
    timestamp: float
    importance: float     # 0-1 重要性评分
    related_stats: dict = field(default_factory=dict)  # 关联的性格变化
    metadata: dict = field(default_factory=dict)


class EpisodicMemory:
    """
    情景记忆：记录重要事件和情感高峰。
    Phase 1.3 将接入 PostgreSQL + 向量索引。
    """

    def __init__(self, max_events: int = 500):
        self.max_events = max_events
        self._events: list[EpisodicEvent] = []

    def add_event(
        self,
        event_type: str,
        summary: str,
        importance: float = 0.5,
        related_stats: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        event = EpisodicEvent(
            event_type=event_type,
            summary=summary,
            timestamp=time.time(),
            importance=importance,
            related_stats=related_stats or {},
            metadata=metadata or {},
        )
        self._events.append(event)
        # 如果超过上限，移除最不重要的
        if len(self._events) > self.max_events:
            self._events.sort(key=lambda e: e.importance)
            self._events = self._events[1:]

    def get_important(self, n: int = 10) -> list[EpisodicEvent]:
        """获取最重要的 n 个事件"""
        sorted_events = sorted(self._events, key=lambda e: e.importance, reverse=True)
        return sorted_events[:n]

    def get_recent(self, n: int = 10) -> list[EpisodicEvent]:
        """获取最近的 n 个事件"""
        return self._events[-n:]

    @property
    def count(self) -> int:
        return len(self._events)

    def search(self, keywords: list[str], limit: int = 5) -> list[EpisodicEvent]:
        """关键词搜索（Phase 1.3 将升级为向量检索）"""
        results = []
        for event in self._events:
            score = sum(1 for kw in keywords if kw in event.summary)
            if score > 0:
                results.append((score, event))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]


# ============================================================
# 演化日志（用于 Merkle Tree）
# ============================================================

@dataclass
class EvolutionEntry:
    """性格演化记录，用于构建 Merkle Tree"""
    interaction_id: int
    timestamp: float
    stat_deltas: dict
    stat_snapshot: dict
    trigger: str         # "conversation" | "event" | "decay"
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            data = json.dumps({
                "id": self.interaction_id,
                "ts": self.timestamp,
                "deltas": self.stat_deltas,
                "snap": self.stat_snapshot,
            }, sort_keys=True)
            self.hash = hashlib.sha256(data.encode()).hexdigest()


class EvolutionLog:
    """
    性格演化日志。
    记录每次性格变化，用于构建 Merkle Tree 上链验证。
    """

    def __init__(self):
        self._entries: list[EvolutionEntry] = []
        self._merkle_root: str = ""

    def record(self, stat_deltas: dict, stat_snapshot: dict, trigger: str = "conversation") -> str:
        entry = EvolutionEntry(
            interaction_id=len(self._entries) + 1,
            timestamp=time.time(),
            stat_deltas=stat_deltas,
            stat_snapshot=stat_snapshot,
            trigger=trigger,
        )
        self._entries.append(entry)
        self._update_merkle_root()
        return entry.hash

    def _update_merkle_root(self) -> None:
        """简化版 Merkle Root 计算（Phase 2 将实现完整 Merkle Tree）"""
        if not self._entries:
            self._merkle_root = ""
            return
        hashes = [e.hash for e in self._entries]
        while len(hashes) > 1:
            new_level = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i + 1]
                else:
                    combined = hashes[i] + hashes[i]
                new_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_level
        self._merkle_root = hashes[0]

    @property
    def merkle_root(self) -> str:
        return self._merkle_root

    @property
    def total_entries(self) -> int:
        return len(self._entries)


# ============================================================
# 记忆管理器（统一入口）
# ============================================================

class MemoryManager:
    """三层记忆的统一管理器"""

    def __init__(self, max_short_term: int = 40, max_episodic: int = 500):
        self.short_term = ShortTermMemory(max_turns=max_short_term)
        self.episodic = EpisodicMemory(max_events=max_episodic)
        self.evolution_log = EvolutionLog()

    def add_turn(self, role: str, content: str, **kwargs) -> None:
        """添加一轮对话到短期记忆"""
        self.short_term.add(role, content, **kwargs)

    def get_conversation_window(self, n: int = 20) -> list[dict]:
        """获取对话窗口（LLM 上下文用）"""
        return self.short_term.get_recent(n)

    def record_evolution(self, stat_deltas: dict, stat_snapshot: dict) -> str:
        """记录性格演化"""
        return self.evolution_log.record(stat_deltas, stat_snapshot)

    def add_important_event(self, event_type: str, summary: str, importance: float = 0.5) -> None:
        """添加情景记忆"""
        self.episodic.add_event(event_type, summary, importance)

    def export_for_trade(self) -> dict:
        """
        导出交易用数据（隐私清洗后）。
        保留：性格演化记录、情景记忆摘要
        移除：完整对话内容
        """
        return {
            "episodic_events": [
                {"type": e.event_type, "summary": e.summary, "importance": e.importance}
                for e in self.episodic.get_important(20)
            ],
            "evolution_count": self.evolution_log.total_entries,
            "merkle_root": self.evolution_log.merkle_root,
        }

    def get_stats(self) -> dict:
        return {
            "short_term_count": self.short_term.count,
            "episodic_count": self.episodic.count,
            "evolution_entries": self.evolution_log.total_entries,
            "merkle_root": self.evolution_log.merkle_root,
        }
