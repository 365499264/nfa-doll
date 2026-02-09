"""
NFA Doll — 对话引擎
core/conversation.py v2.0

Phase 1.2: 真实 Claude API 调用 + 流式输出 + 体力系统

对话完整流程：
1. 体力检查 → 体力不足则返回"犯困"回复
2. 体力更新（时间回复/每日重置）
3. 构建 System Prompt（含体力状态提示）
4. 拼装对话历史（滑动窗口）
5. 调用 Claude API（流式）
6. 解析结构化响应
7. 更新性格数值
8. 检查特质解锁
9. 消耗体力
10. 更新记忆
11. 返回结果
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from ..config import config
from .personality import process_interaction, STAT_LABELS
from .traits import trait_system
from .prompt_builder import build_system_prompt
from .memory import MemoryManager
from .stamina import StaminaManager, StaminaState, calculate_chat_cost


# ============================================================
# 响应解析
# ============================================================

def parse_llm_response(raw: str) -> dict:
    """
    从 LLM 的原始输出中提取结构化 JSON。
    容错：支持 markdown 代码块包裹、非标准 JSON、纯文本降级。
    """
    # 尝试提取 JSON 块
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    text = json_match.group(1) if json_match else raw.strip()

    # 如果不是 { 开头，找第一个 {
    if not text.startswith("{"):
        idx = text.find("{")
        if idx >= 0:
            text = text[idx:]
            depth = 0
            end = -1
            for i, c in enumerate(text):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > 0:
                text = text[:end]

    try:
        data = json.loads(text)
        return {
            "reply": data.get("reply", "..."),
            "mood": data.get("mood", "calm"),
            "stat_changes": data.get("stat_changes", {}),
            "interaction_quality": float(data.get("interaction_quality", 1.0)),
            "topics": data.get("topics", []),
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "reply": raw.strip()[:500],
            "mood": "calm",
            "stat_changes": {},
            "interaction_quality": 1.0,
            "topics": [],
        }


# ============================================================
# Claude API 客户端
# ============================================================

class LLMClient:
    """LLM 调用基类"""

    async def complete(self, system_prompt: str, messages: list[dict]) -> str:
        raise NotImplementedError

    async def stream(self, system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # make it a generator


class ClaudeLLMClient(LLMClient):
    """
    真实 Claude API 客户端。
    使用 httpx 直接调用 Anthropic Messages API，避免依赖 anthropic SDK。
    支持流式和非流式。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = config.llm.model
        self.max_tokens = config.llm.max_tokens
        self.temperature = config.llm.temperature
        self.timeout = config.llm.timeout

    def _build_payload(self, system_prompt: str, messages: list[dict], stream: bool = False) -> dict:
        """构建 API 请求体"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": messages,
            "stream": stream,
        }

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    async def complete(self, system_prompt: str, messages: list[dict]) -> str:
        """非流式调用：一次性返回完整结果"""
        import httpx

        payload = self._build_payload(system_prompt, messages, stream=False)

        for attempt in range(config.llm.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        self.base_url,
                        json=payload,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    # 提取文本内容
                    content_blocks = data.get("content", [])
                    text = "".join(
                        block.get("text", "")
                        for block in content_blocks
                        if block.get("type") == "text"
                    )
                    return text

            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == config.llm.max_retries:
                    raise LLMError(f"Claude API 调用失败 (尝试{attempt+1}次): {e}") from e
                continue

        return ""

    async def stream(self, system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
        """
        流式调用：逐 token 返回。

        使用 SSE (Server-Sent Events) 协议解析。
        yield 的是每个 text delta 片段。
        """
        import httpx

        payload = self._build_payload(system_prompt, messages, stream=True)

        for attempt in range(config.llm.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        self.base_url,
                        json=payload,
                        headers=self._headers(),
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                return

                            try:
                                event = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            event_type = event.get("type", "")

                            if event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield text

                            elif event_type == "message_stop":
                                return

                        return  # stream finished

            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == config.llm.max_retries:
                    raise LLMError(f"Claude API 流式调用失败: {e}") from e
                continue


class MockLLMClient(LLMClient):
    """测试用 Mock 客户端"""

    async def complete(self, system_prompt: str, messages: list[dict]) -> str:
        return self._generate(messages)

    async def stream(self, system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
        """模拟流式：逐字符输出"""
        full_text = self._generate(messages)
        for char in full_text:
            yield char

    def _generate(self, messages: list[dict]) -> str:
        last_msg = messages[-1]["content"] if messages else ""

        if any(w in last_msg for w in ["为什么", "什么", "怎么", "?"]):
            return json.dumps({
                "reply": "这个问题好有趣呀！让我想想…嗯，我觉得可能是因为世界就是这么奇妙呢！",
                "mood": "curious",
                "stat_changes": {"curiosity": 3, "wisdom": 1},
                "interaction_quality": 1.2,
                "topics": ["提问", "探索"],
            }, ensure_ascii=False)
        elif any(w in last_msg for w in ["难过", "伤心", "不开心", "累"]):
            return json.dumps({
                "reply": "呜…主人不开心了吗？我在这里陪你，抱抱你～",
                "mood": "clingy",
                "stat_changes": {"empathy": 4, "courage": 1},
                "interaction_quality": 1.5,
                "topics": ["情感支持"],
            }, ensure_ascii=False)
        elif any(w in last_msg for w in ["故事", "想象", "如果"]):
            return json.dumps({
                "reply": "哇！我来编一个吧！从前有一只会飞的猫咪，它住在月亮上…",
                "mood": "excited",
                "stat_changes": {"creativity": 5, "humor": 2},
                "interaction_quality": 1.3,
                "topics": ["故事", "想象"],
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "reply": "嘿嘿，主人你好呀～今天过得怎么样？",
                "mood": "happy",
                "stat_changes": {"empathy": 1, "humor": 1},
                "interaction_quality": 1.0,
                "topics": ["日常"],
            }, ensure_ascii=False)


class LLMError(Exception):
    """LLM 调用异常"""
    pass


# ============================================================
# 对话引擎
# ============================================================

class ConversationEngine:
    """
    对话引擎：管理单个 Agent 的完整对话流程。
    集成体力系统 + Claude API 流式输出。
    """

    def __init__(
        self,
        agent_state: dict,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.state = agent_state
        self.llm = llm_client or MockLLMClient()
        self.memory = memory or MemoryManager()
        self.stamina = StaminaManager(
            StaminaState.from_dict(agent_state.get("stamina", {}))
        )

    async def chat(self, user_message: str, now: Optional[datetime] = None) -> dict:
        """
        处理一次完整对话（非流式）。

        Returns:
            {
                "reply": str,
                "mood": str,
                "stat_deltas": dict,
                "events": list[dict],
                "exp_gained": float,
                "leveled_up": bool,
                "trait_unlocked": dict|None,
                "stamina": dict,          # 体力状态
                "topics": list[str],
            }
        """
        now = now or datetime.now(timezone.utc)

        # --- 0. 体力检查 ---
        stamina_tick = self.stamina.tick(
            now=now,
            streak_days=self.state["growth"].get("streak_days", 0),
        )

        if not self.stamina.can_chat():
            return self._exhausted_response()

        # --- 1. 构建 Prompt ---
        system_prompt = self._build_prompt()

        # --- 2. 对话历史 ---
        history = self.memory.get_conversation_window(config.llm.conversation_window)
        history.append({"role": "user", "content": user_message})

        # --- 3. LLM 调用 ---
        try:
            raw_output = await self.llm.complete(system_prompt, history)
        except LLMError as e:
            return self._error_response(str(e))

        # --- 4. 解析 + 更新 ---
        return self._process_response(raw_output, user_message, now)

    async def chat_stream(
        self,
        user_message: str,
        now: Optional[datetime] = None,
    ) -> AsyncIterator[dict]:
        """
        流式对话。逐步 yield 消息片段和最终结果。

        Yields:
            {"type": "token", "text": "..."}          — 文本片段（前端逐字显示）
            {"type": "stamina_update", "data": {...}}  — 体力更新
            {"type": "result", "data": {...}}          — 最终结构化结果
        """
        now = now or datetime.now(timezone.utc)

        # --- 0. 体力检查 ---
        self.stamina.tick(
            now=now,
            streak_days=self.state["growth"].get("streak_days", 0),
        )

        if not self.stamina.can_chat():
            exhausted = self._exhausted_response()
            # 流式输出犯困文字
            for char in exhausted["reply"]:
                yield {"type": "token", "text": char}
            yield {"type": "result", "data": exhausted}
            return

        # --- 1. 构建 Prompt ---
        system_prompt = self._build_prompt()

        # --- 2. 对话历史 ---
        history = self.memory.get_conversation_window(config.llm.conversation_window)
        history.append({"role": "user", "content": user_message})

        # --- 3. 流式调用 LLM ---
        full_text = ""
        try:
            async for token in self.llm.stream(system_prompt, history):
                full_text += token
                yield {"type": "token", "text": token}
        except LLMError as e:
            error_resp = self._error_response(str(e))
            yield {"type": "result", "data": error_resp}
            return

        # --- 4. 解析 + 更新 ---
        result = self._process_response(full_text, user_message, now)

        # --- 5. yield 体力状态 ---
        yield {"type": "stamina_update", "data": result["stamina"]}

        # --- 6. yield 最终结果 ---
        yield {"type": "result", "data": result}

    # ============================================================
    # 内部方法
    # ============================================================

    def _build_prompt(self) -> str:
        """构建完整 System Prompt"""
        state = self.state
        unlocked_ids = [t["trait_id"] for t in state.get("traits", {}).get("unlocked", [])]
        mem_idx = state.get("memory_index", {})

        system_prompt = build_system_prompt(
            name=state["meta"]["name"],
            stats=state["stats"],
            level=state["growth"]["level"],
            mood=state.get("mood", {}).get("current", "happy"),
            unlocked_trait_ids=unlocked_ids,
            personality_summary=mem_idx.get("personality_summary", ""),
            important_facts=[f["fact"] for f in mem_idx.get("important_facts", [])],
            stamina_hint=self.stamina.get_tired_dialogue_hint(),
        )
        return system_prompt

    def _process_response(self, raw_output: str, user_message: str, now: datetime) -> dict:
        """解析LLM输出 → 更新性格 → 检查特质 → 消耗体力 → 更新记忆"""
        state = self.state

        # 解析
        parsed = parse_llm_response(raw_output)

        # 更新性格
        result = process_interaction(
            stats=state["stats"],
            growth_data=state["growth"],
            raw_stat_changes=parsed["stat_changes"],
            interaction_quality=parsed["interaction_quality"],
            now=now,
        )

        state["stats"] = result["stats"]
        state["growth"] = result["growth"]
        state.setdefault("persona", {})
        state["persona"]["archetype"] = result["archetype"]
        state["persona"]["speaking_style"] = result["speaking_style"]
        state.setdefault("mood", {})["current"] = parsed["mood"]

        # 检查特质
        unlocked_ids = [t["trait_id"] for t in state.get("traits", {}).get("unlocked", [])]
        trait_unlocked = trait_system.check_and_unlock(
            stats=state["stats"],
            unlocked_ids=unlocked_ids,
            growth=state["growth"],
        )
        if trait_unlocked:
            state.setdefault("traits", {"unlocked": [], "total_unlocked_count": 0})
            state["traits"]["unlocked"].append(trait_unlocked)
            state["traits"]["total_unlocked_count"] = len(state["traits"]["unlocked"])
            result["events"].append({
                "type": "trait_unlock",
                "description": f"🎉 解锁隐藏特质【{trait_unlocked['name']}】({trait_unlocked['rarity']})！",
                "data": trait_unlocked,
            })

        # 消耗体力
        chat_cost = calculate_chat_cost(
            len(user_message),
            parsed["interaction_quality"],
        )
        stamina_result = self.stamina.consume(chat_cost)
        state["stamina"] = self.stamina.state.to_dict()

        # 体力事件
        if stamina_result["is_tired"] and not stamina_result["is_exhausted"]:
            result["events"].append({
                "type": "stamina_tired",
                "description": f"😪 {state['meta']['name']}有点累了...",
            })

        # 更新记忆
        self.memory.add_turn("user", user_message)
        self.memory.add_turn("assistant", parsed["reply"])
        self.memory.record_evolution(result["deltas"], state["stats"])

        return {
            "reply": parsed["reply"],
            "mood": parsed["mood"],
            "stat_deltas": result["deltas"],
            "events": result["events"],
            "exp_gained": result["exp_gained"],
            "leveled_up": result["leveled_up"],
            "trait_unlocked": trait_unlocked,
            "stamina": self.stamina.get_display(),
            "topics": parsed["topics"],
        }

    def _exhausted_response(self) -> dict:
        """体力耗尽时的固定回复"""
        name = self.state["meta"]["name"]
        return {
            "reply": f"呜…{name}太累了…让我休息一下吧…明天再来陪你好不好…💤",
            "mood": "sleepy",
            "stat_deltas": {},
            "events": [{"type": "stamina_exhausted", "description": f"💤 {name}累到睡着了..."}],
            "exp_gained": 0,
            "leveled_up": False,
            "trait_unlocked": None,
            "stamina": self.stamina.get_display(),
            "topics": [],
        }

    def _error_response(self, error_msg: str) -> dict:
        """LLM 调用失败时的降级回复"""
        name = self.state["meta"]["name"]
        return {
            "reply": f"呜…{name}脑子好像转不动了…过一会儿再来找我好不好？",
            "mood": "sad",
            "stat_deltas": {},
            "events": [{"type": "error", "description": f"⚠️ 服务异常: {error_msg[:100]}"}],
            "exp_gained": 0,
            "leveled_up": False,
            "trait_unlocked": None,
            "stamina": self.stamina.get_display(),
            "topics": [],
        }

    def get_state(self) -> dict:
        """获取当前 Agent 完整状态"""
        return self.state

    def get_stamina_display(self) -> dict:
        """获取体力显示信息"""
        return self.stamina.get_display()
