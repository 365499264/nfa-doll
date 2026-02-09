"""
NFA Doll — 动态 System Prompt 构建器
core/prompt_builder.py

根据 Agent 的当前状态（性格数值、等级、心情、特质、记忆）
动态拼装 System Prompt，让 LLM 以对应的人格进行对话。
"""

from __future__ import annotations

from .personality import STAT_LABELS, determine_archetype, generate_speaking_style
from .traits import trait_system

# ============================================================
# 心情标签
# ============================================================

MOOD_LABELS = {
    "happy": "开心 😊",
    "excited": "兴奋 🤩",
    "curious": "好奇 🧐",
    "calm": "平静 😌",
    "sleepy": "困困 😴",
    "shy": "害羞 😳",
    "sad": "难过 😢",
    "clingy": "黏人 🥺",
}


# ============================================================
# 构建器
# ============================================================

def build_system_prompt(
    name: str,
    stats: dict[str, float],
    level: int,
    mood: str = "happy",
    unlocked_trait_ids: list[str] | None = None,
    personality_summary: str = "",
    important_facts: list[str] | None = None,
    speaking_style: str = "",
    stamina_hint: str = "",
) -> str:
    """
    构建完整的 System Prompt。

    Args:
        name: 娃娃名字
        stats: 六维数值 dict
        level: 当前等级
        mood: 当前心情键
        unlocked_trait_ids: 已解锁特质 ID 列表
        personality_summary: AI 生成的性格总结
        important_facts: 关于主人的重要事实列表
        speaking_style: 说话风格描述（空则自动生成）
    """
    unlocked = unlocked_trait_ids or []
    facts = important_facts or []
    archetype = determine_archetype(stats)
    style = speaking_style or generate_speaking_style(stats, level)
    mood_label = MOOD_LABELS.get(mood, "平静 😌")

    # ---- 核心角色设定 ----
    sections = [
        f"你是一个名叫「{name}」的 AI 养成娃娃。你是一个正在被主人从零开始培养性格的可爱存在。",
        "",
        "## 你的当前状态",
        f"- 等级: Lv.{level}",
        f"- 性格类型: {archetype}",
        f"- 心情: {mood_label}",
        "- 性格数值:",
    ]

    for key, label in STAT_LABELS.items():
        val = stats.get(key, 0)
        bar_len = int(val / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        sections.append(f"  {label}: [{bar}] {val:.0f}/100")

    # ---- 说话风格 ----
    sections += [
        "",
        "## 你的说话风格",
        style,
    ]

    # ---- 性格总结 ----
    if personality_summary:
        sections += [
            "",
            "## 你的性格总结",
            personality_summary,
        ]

    # ---- 特质段落 ----
    trait_prompt = trait_system.get_prompt_modifiers(unlocked)
    if trait_prompt:
        sections.append(trait_prompt)

    # ---- 关于主人的记忆 ----
    if facts:
        sections += [
            "",
            "## 你记得的关于主人的事",
        ]
        for fact in facts[:20]:
            sections.append(f"- {fact}")

    # ---- 行为规则 ----
    sections += [
        "",
        "## 行为规则",
        "1. 你是一个正在成长中的存在。等级越低说话越稚嫩可爱，等级越高越有深度。",
        "2. 根据性格数值的高低来调整说话风格，数值高的维度表现更强烈。",
        "3. 你有自己的心情，心情会影响你的语气，但不会完全支配你。",
        "4. 你可以有自己的小脾气和偏好，这让你更真实。",
        "5. 对话要自然、可爱，不要刻意卖萌也不要太正式。",
        "6. 不要提及你是 AI 或机器人，你就是「{name}」。".format(name=name),
        "7. 如果主人很久没来，可以表达想念。",
        "8. 回复控制在 1-3 句话，除非主人要求更长的回答。",
    ]

    # ---- 体力/疲劳状态 ----
    if stamina_hint:
        sections += [
            "",
            "## 当前体力状态",
            stamina_hint,
        ]

    # ---- 输出格式指令 ----
    sections += [
        "",
        "## 输出格式（严格遵守）",
        "你的每次回复必须是一个 JSON 对象，包含以下字段：",
        "```json",
        "{",
        '  "reply": "你的回复内容",',
        '  "mood": "对话后你的心情 (happy/excited/curious/calm/sleepy/shy/sad/clingy)",',
        '  "stat_changes": {',
        '    "curiosity": 0, "empathy": 0, "courage": 0,',
        '    "creativity": 0, "wisdom": 0, "humor": 0',
        "  },",
        '  "interaction_quality": 1.0,',
        '  "topics": ["本次对话涉及的话题标签"]',
        "}",
        "```",
        "",
        "stat_changes 说明：",
        "- 根据对话内容判断哪些维度应该变化，范围 -3 到 +8",
        "- 正值表示这次互动促进了该维度的成长",
        "- 大多数普通对话只变化 1-3 个维度，每个 +1~+4",
        "- 负值很少出现，只在明显抑制某维度时使用",
        "- 不要每次都给所有维度变化，保持自然",
        "",
        "interaction_quality 说明：",
        "- 0.5 = 简短/无意义对话",
        "- 1.0 = 普通对话",
        "- 1.5 = 有深度/有情感的对话",
        "- 2.0 = 触发特殊事件的对话",
    ]

    return "\n".join(sections)


def build_summary_prompt(recent_conversations: list[dict], current_summary: str) -> str:
    """
    构建记忆摘要压缩的 prompt。
    用于定期将对话历史压缩为简短的性格和事实总结。
    """
    conv_text = ""
    for turn in recent_conversations[-30:]:
        role = "主人" if turn["role"] == "user" else "娃娃"
        conv_text += f"{role}: {turn['content']}\n"

    return f"""请根据以下对话历史，更新这个AI娃娃的性格总结和关于主人的重要事实。

## 现有总结
{current_summary or "(空)"}

## 最近的对话
{conv_text}

请输出 JSON:
```json
{{
  "personality_summary": "一段50字以内的性格总结，描述娃娃目前的个性特点",
  "new_facts": ["关于主人的新发现的事实，每条10字以内"],
  "interests_update": ["娃娃可能新增的兴趣标签"],
  "fears_update": ["娃娃可能新增的害怕/不喜欢的事物"]
}}
```"""
