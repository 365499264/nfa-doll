#!/usr/bin/env python3
"""
NFA Doll — 交互式演示脚本

用法:
    python scripts/demo.py              # 交互模式
    python scripts/demo.py --simulate   # 自动模拟 20 轮对话
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.personality import create_initial_stats, STAT_KEYS, STAT_LABELS
from backend.core.conversation import ConversationEngine, MockLLMClient
from backend.core.memory import MemoryManager


def create_fresh_state(name: str = "小星", birth: str = "blank") -> dict:
    """创建全新 Agent 状态"""
    return {
        "agent_id": "demo_001",
        "meta": {"name": name},
        "stats": create_initial_stats(birth),
        "growth": {
            "level": 1, "total_exp": 0, "total_interactions": 0,
            "streak_days": 0, "last_interaction_at": None, "archetype": "白纸娃娃",
        },
        "mood": {"current": "happy"},
        "traits": {"unlocked": [], "total_unlocked_count": 0},
        "persona": {"archetype": "白纸娃娃", "speaking_style": ""},
        "memory_index": {"personality_summary": "", "important_facts": []},
    }


def print_status(state: dict) -> None:
    name = state["meta"]["name"]
    g = state["growth"]
    print(f"\n{'='*50}")
    print(f"  🧸 {name}  |  Lv.{g['level']}  |  {state['persona'].get('archetype', '?')}")
    print(f"{'='*50}")

    for key in STAT_KEYS:
        val = state["stats"].get(key, 0)
        bar_len = int(val / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        label = STAT_LABELS[key]
        print(f"  {label:12s} [{bar}] {val:5.1f}")

    mood = state.get("mood", {}).get("current", "?")
    print(f"\n  💭 心情: {mood}  |  互动: {g['total_interactions']}次  |  连击: {g['streak_days']}天")

    traits = state.get("traits", {}).get("unlocked", [])
    if traits:
        names = [f"{t['icon']} {t['name']}({t['rarity']})" for t in traits]
        print(f"  ✨ 特质: {', '.join(names)}")
    print(f"{'='*50}\n")


async def interactive_mode():
    name = input("  给你的娃娃起个名字 (默认: 小星): ").strip() or "小星"
    state = create_fresh_state(name)
    engine = ConversationEngine(state, llm_client=MockLLMClient(), memory=MemoryManager())

    print(f"\n  🎉 {name} 诞生了！（使用 Mock LLM，输入 /status 查看状态，/quit 退出）\n")
    print_status(state)

    while True:
        try:
            user_input = input(f"  你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input == "/quit":
            print(f"\n  👋 {name}: 再见，下次再来陪我玩哦~\n")
            break
        if user_input == "/status":
            print_status(state)
            continue

        result = await engine.chat(user_input)
        print(f"\n  🧸 {name}: {result['reply']}")

        # 显示变化
        deltas = result.get("stat_deltas", {})
        changes = [f"{STAT_LABELS[k].split()[0]}{'+' if v > 0 else ''}{v}" for k, v in deltas.items() if v != 0]
        if changes:
            print(f"  📊 {', '.join(changes)}  |  EXP +{result['exp_gained']}")
        for ev in result.get("events", []):
            print(f"  🎉 {ev['description']}")
        print()


async def simulate_mode():
    state = create_fresh_state("小星")
    engine = ConversationEngine(state, llm_client=MockLLMClient(), memory=MemoryManager())

    messages = [
        "你好呀小星！",
        "你觉得星星为什么会发光呢？",
        "今天好难过...",
        "给我讲个故事吧！",
        "你真聪明！",
        "如果世界是倒过来的会怎样？",
        "我喜欢和你聊天",
        "为什么天是蓝色的？",
        "我今天遇到了一件开心的事",
        "你害怕什么吗？",
        "来玩个游戏吧！",
        "你知道宇宙有多大吗？",
        "我觉得你越来越有趣了",
        "如果你可以去任何地方你想去哪？",
        "今天天气真好",
        "你有什么秘密吗？",
        "教我一个新知识吧",
        "我想听你讲笑话",
        "你觉得什么是勇气？",
        "谢谢你一直陪着我",
    ]

    print(f"\n  🤖 自动模拟模式 — {len(messages)} 轮对话\n")
    print_status(state)

    for i, msg in enumerate(messages, 1):
        result = await engine.chat(msg)
        deltas = {k: v for k, v in result.get("stat_deltas", {}).items() if v != 0}
        delta_str = ", ".join(f"{k[:3]}{'+' if v > 0 else ''}{v}" for k, v in deltas.items())
        events = "  ".join(f"🎉{e['description']}" for e in result.get("events", []))
        print(f"  [{i:2d}] 👤 {msg[:25]:25s} → 🧸 {result['reply'][:35]:35s} | {delta_str}  {events}")

    print_status(state)


def main():
    if "--simulate" in sys.argv:
        asyncio.run(simulate_mode())
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
