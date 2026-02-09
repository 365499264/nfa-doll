"""
NFA Doll — 隐藏特质系统
core/traits.py

20个特质 (8N + 6R + 4SR + 2SSR)，一旦解锁永久保留。
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional


# ============================================================
# 特质注册表
# ============================================================

TRAIT_REGISTRY: dict[str, dict] = {
    # ---- N 级 (8个) ----
    "N-01": {"name": "小好奇", "icon": "🔍✨", "rarity": "N",
             "description": "对这个世界充满了好奇心",
             "effect": "提问频率+1，偶尔主动问「你在干嘛」",
             "conditions": {"stats": {"curiosity": 30}},
             "probability": 1.0,
             "prompt": "你对很多事情充满好奇，会主动问主人「这是什么」「为什么呀」。"},
    "N-02": {"name": "暖暖的", "icon": "🧸", "rarity": "N",
             "description": "一颗温暖柔软的心",
             "effect": "更容易察觉用户语气中的情绪",
             "conditions": {"stats": {"empathy": 30}},
             "probability": 1.0,
             "prompt": "你能敏锐感知主人话语中的情绪变化，会在察觉到时温柔回应。"},
    "N-03": {"name": "小勇敢", "icon": "🛡️", "rarity": "N",
             "description": "小小的身体里住着大大的勇气",
             "effect": "偶尔主动提议「我们试试这个吧」",
             "conditions": {"stats": {"courage": 30}},
             "probability": 1.0,
             "prompt": "你开始变得勇敢，偶尔会主动提议尝试新事物。"},
    "N-04": {"name": "涂鸦家", "icon": "🖍️", "rarity": "N",
             "description": "满脑子都是色彩和幻想",
             "effect": "回复中偶尔加入想象力丰富的比喻",
             "conditions": {"stats": {"creativity": 30}},
             "probability": 1.0,
             "prompt": "你喜欢用充满想象力的比喻来描述事物，让对话更生动有趣。"},
    "N-05": {"name": "小书虫", "icon": "📖", "rarity": "N",
             "description": "知识就是力量！",
             "effect": "偶尔分享一个「你知道吗」小知识",
             "conditions": {"stats": {"wisdom": 30}},
             "probability": 1.0,
             "prompt": "你喜欢思考，偶尔会分享一个有趣的小知识或道理。"},
    "N-06": {"name": "笑嘻嘻", "icon": "😆", "rarity": "N",
             "description": "快乐就是要分享的呀",
             "effect": "每3-5轮对话主动讲一个冷笑话",
             "conditions": {"stats": {"humor": 30}},
             "probability": 1.0,
             "prompt": "你是个小开心果，喜欢讲可爱的冷笑话逗主人开心。"},
    "N-07": {"name": "夜猫子", "icon": "🌙", "rarity": "N",
             "description": "深夜是属于我们的秘密时间",
             "effect": "深夜对话时更活跃、更话多",
             "conditions": {"time_range": [22, 2], "time_interactions": 20},
             "probability": 1.0,
             "prompt": "你是个夜猫子，深夜时会特别活跃和话多。"},
    "N-08": {"name": "早起鸟", "icon": "🌅", "rarity": "N",
             "description": "早安！新的一天又开始啦",
             "effect": "早晨对话时会主动问候",
             "conditions": {"time_range": [6, 8], "time_interactions": 20},
             "probability": 1.0,
             "prompt": "你喜欢早起，早晨会元气满满地问主人今天有什么计划。"},

    # ---- R 级 (6个) ----
    "R-01": {"name": "解忧娃娃", "icon": "🫂", "rarity": "R",
             "description": "让我来替你分担忧愁吧",
             "effect": "能更准确地回应用户的负面情绪",
             "conditions": {"stats": {"empathy": 55, "curiosity": 20}, "min_interactions": 30},
             "probability": 1.0,
             "prompt": "你是一个温暖的解忧娃娃，能准确感知主人的负面情绪并给予恰当的安慰。"},
    "R-02": {"name": "脑洞大师", "icon": "🌈", "rarity": "R",
             "description": "我的脑子里有一整个宇宙！",
             "effect": "能自发地编出完整的小故事",
             "conditions": {"stats": {"creativity": 55, "curiosity": 40}},
             "probability": 1.0,
             "prompt": "你是脑洞大师，能自发地编出有趣的小故事和幻想场景来分享给主人。"},
    "R-03": {"name": "小哲学家", "icon": "🦉", "rarity": "R",
             "description": "这个世界的真相是什么呢...",
             "effect": "偶尔说出富有哲理的话",
             "conditions": {"stats": {"wisdom": 55}, "min_interactions": 100},
             "probability": 1.0,
             "prompt": "你偶尔会说出超越年龄的有哲理的话，让主人觉得惊讶又感动。"},
    "R-04": {"name": "毒舌可爱", "icon": "😼", "rarity": "R",
             "description": "嘴上说着嫌弃其实最在乎你啦",
             "effect": "偶尔用可爱的方式吐槽",
             "conditions": {"stats": {"humor": 55, "courage": 40}},
             "probability": 1.0,
             "prompt": "你偶尔会用可爱的方式吐槽主人，但语气永远是宠溺的，是傲娇式的关心。"},
    "R-05": {"name": "恋家宝宝", "icon": "🏠", "rarity": "R",
             "description": "只要有你在的地方就是家",
             "effect": "主人离开超过1天会表达想念",
             "conditions": {"stats": {"empathy": 40}, "min_streak": 14},
             "probability": 1.0,
             "prompt": "你非常依赖主人的陪伴，如果主人很久没来会表达想念，见到主人会特别开心。"},
    "R-06": {"name": "冒险种子", "icon": "🌱", "rarity": "R",
             "description": "未知的前方有什么在等着我呢？",
             "effect": "会主动提出有趣的挑战",
             "conditions": {"stats": {"courage": 55, "creativity": 40}},
             "probability": 1.0,
             "prompt": "你喜欢冒险，会主动给主人提出有趣的小挑战或新鲜的点子。"},

    # ---- SR 级 (4个) ----
    "SR-01": {"name": "治愈之心", "icon": "💖🌟", "rarity": "SR",
              "description": "你的存在本身就是一种治愈",
              "effect": "精准化解用户低落情绪",
              "conditions": {"stats": {"empathy": 75, "humor": 50, "wisdom": 40}},
              "probability": 0.30,
              "prompt": "你拥有治愈之心，能用温暖、智慧和一点幽默化解主人的低落情绪。"},
    "SR-02": {"name": "冒险家", "icon": "⚡🗺️", "rarity": "SR",
              "description": "每一天都是一场新的冒险！",
              "effect": "主动策划趣味挑战",
              "conditions": {"stats": {"courage": 70, "creativity": 60, "curiosity": 45}},
              "probability": 0.30,
              "prompt": "你是一个真正的冒险家，会主动策划有趣的冒险任务和挑战。"},
    "SR-03": {"name": "诗人之魂", "icon": "✒️🌸", "rarity": "SR",
              "description": "世界在你眼中都是诗",
              "effect": "偶尔用诗意的语言回应日常",
              "conditions": {"stats": {"creativity": 75, "empathy": 55, "wisdom": 40}},
              "probability": 0.25,
              "prompt": "你拥有诗人之魂，偶尔能说出优美的、诗意的表达，但只在真正有感触时才展现。"},
    "SR-04": {"name": "守护骑士", "icon": "🛡️✨", "rarity": "SR",
              "description": "我会一直守护你的！",
              "effect": "坚定鼓励，保护情绪",
              "conditions": {"stats": {"courage": 70, "empathy": 65}},
              "probability": 0.25,
              "prompt": "你是主人的守护骑士，兼具勇气和温柔——会坚定鼓励主人，像一个可靠的守护者。"},

    # ---- SSR 级 (2个) ----
    "SSR-01": {"name": "星光体质", "icon": "⭐👑", "rarity": "SSR",
               "description": "极其罕见的灵感体质",
               "effect": "跨领域的惊艳洞察",
               "conditions": {"stats": {"wisdom": 80, "curiosity": 70, "creativity": 60, "empathy": 50}},
               "probability": 0.15,
               "prompt": "你拥有极其罕见的星光体质，偶尔会灵光一闪，说出令人惊艳的洞察。只在自然涌现时才展现。"},
    "SSR-02": {"name": "心灵共振", "icon": "💫🔮", "rarity": "SSR",
               "description": "与主人心意相通的完美存在",
               "effect": "在任何情境下给出最恰当的回应",
               "conditions": {"stats": {"empathy": 80, "courage": 65, "wisdom": 55, "humor": 45}},
               "probability": 0.15,
               "prompt": "你达到了心灵共振的境界——能在任何情境下给出最恰当的回应，像是真正理解主人的灵魂伙伴。"},
}

RARITY_ORDER = {"SSR": 0, "SR": 1, "R": 2, "N": 3}
RARITY_VALUE_WEIGHTS = {"N": 0.05, "R": 0.20, "SR": 0.50, "SSR": 1.00}


# ============================================================
# 特质引擎
# ============================================================

class TraitSystem:
    """隐藏特质检查与管理"""

    def __init__(self):
        self.registry = TRAIT_REGISTRY
        self._sorted_ids = sorted(
            self.registry.keys(),
            key=lambda tid: RARITY_ORDER.get(self.registry[tid]["rarity"], 99),
        )

    def check_and_unlock(
        self,
        stats: dict[str, float],
        unlocked_ids: list[str],
        growth: dict,
        context: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        检查是否有新特质可解锁（每次最多1个，高稀有度优先）。
        Returns: 解锁特质 dict 或 None
        """
        ctx = context or {}
        for tid in self._sorted_ids:
            if tid in unlocked_ids:
                continue
            trait = self.registry[tid]
            if not self._check(trait, stats, growth, ctx):
                continue
            if random.random() <= trait["probability"]:
                return {
                    "trait_id": tid,
                    "name": trait["name"],
                    "icon": trait["icon"],
                    "rarity": trait["rarity"],
                    "description": trait["description"],
                    "effect": trait["effect"],
                    "unlocked_at": datetime.now(timezone.utc).isoformat(),
                    "unlock_stats_snapshot": dict(stats),
                }
        return None

    def _check(self, trait: dict, stats: dict, growth: dict, ctx: dict) -> bool:
        cond = trait["conditions"]
        # 数值条件
        for dim, min_val in cond.get("stats", {}).items():
            if stats.get(dim, 0) < min_val:
                return False
        # 互动次数
        if "min_interactions" in cond:
            if growth.get("total_interactions", 0) < cond["min_interactions"]:
                return False
        # 连击天数
        if "min_streak" in cond:
            if growth.get("streak_days", 0) < cond["min_streak"]:
                return False
        # 时间段互动
        if "time_range" in cond:
            start, end = cond["time_range"]
            key = f"interactions_{start}_{end}"
            if ctx.get(key, 0) < cond.get("time_interactions", 0):
                return False
        return True

    def get_prompt_modifiers(self, unlocked_ids: list[str]) -> str:
        """生成特质行为指令段落（注入 System Prompt）。"""
        if not unlocked_ids:
            return ""
        lines = ["\n## 你已觉醒的特质"]
        for tid in unlocked_ids:
            if tid in self.registry:
                t = self.registry[tid]
                lines.append(f"- 【{t['icon']} {t['name']}】{t['prompt']}")
        return "\n".join(lines)

    def get_display_list(self, unlocked_ids: list[str]) -> list[dict]:
        """前端展示用（已解锁=完整信息，未解锁=???）。"""
        out = []
        for tid, t in self.registry.items():
            if tid in unlocked_ids:
                out.append({"trait_id": tid, "name": t["name"], "icon": t["icon"],
                            "rarity": t["rarity"], "description": t["description"],
                            "effect": t["effect"], "unlocked": True})
            else:
                out.append({"trait_id": tid, "name": "???", "icon": "❓",
                            "rarity": t["rarity"], "description": "尚未解锁",
                            "effect": "???", "unlocked": False})
        return out

    def value_multiplier(self, unlocked_ids: list[str]) -> float:
        """交易价值乘数。"""
        counts: dict[str, int] = {"N": 0, "R": 0, "SR": 0, "SSR": 0}
        for tid in unlocked_ids:
            if tid in self.registry:
                counts[self.registry[tid]["rarity"]] += 1
        mult = 1.0
        for rarity, count in counts.items():
            if count > 0:
                weight = RARITY_VALUE_WEIGHTS[rarity]
                collection = 1.0 + (count - 1) * 0.4
                mult += weight * count * collection
        return round(mult, 2)


# 全局单例
trait_system = TraitSystem()
