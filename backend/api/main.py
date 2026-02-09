"""
NFA Doll — FastAPI 服务入口
backend/api/main.py

Phase 1.5 完整实现。当前为骨架 + 核心路由定义。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="NFA Doll API",
    version="0.1.0",
    description="AI养成娃娃后端服务",
)


# ============================================================
# 请求/响应模型
# ============================================================

class CreateAgentRequest(BaseModel):
    name: str
    owner_id: str = ""
    birth_personality: str = "blank"


class ChatRequest(BaseModel):
    agent_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    mood: str
    stat_deltas: dict
    events: list[dict]
    exp_gained: float
    leveled_up: bool
    trait_unlocked: dict | None = None


# ============================================================
# 路由
# ============================================================

@app.get("/")
async def root():
    return {"service": "nfa-doll", "version": "0.1.0", "status": "ok"}


@app.post("/agents", summary="创建新 Agent")
async def create_agent(req: CreateAgentRequest):
    """创建一个新的 AI 娃娃。Phase 1.5 接入数据库。"""
    # TODO: 接入 AgentState.create_new() + 持久化
    return {"message": "TODO: Phase 1.5", "name": req.name}


@app.get("/agents/{agent_id}", summary="获取 Agent 状态")
async def get_agent(agent_id: str):
    """获取 Agent 的完整状态。"""
    # TODO: 从数据库加载
    raise HTTPException(404, "TODO: Phase 1.5")


@app.post("/agents/{agent_id}/chat", summary="对话", response_model=ChatResponse)
async def chat(agent_id: str, req: ChatRequest):
    """与 Agent 对话。"""
    # TODO: 加载 Agent → ConversationEngine.chat() → 保存
    raise HTTPException(501, "TODO: Phase 1.5")


@app.get("/agents/{agent_id}/traits", summary="获取特质面板")
async def get_traits(agent_id: str):
    """获取 Agent 的特质信息（已解锁+未解锁）。"""
    raise HTTPException(501, "TODO: Phase 1.5")


@app.get("/agents/{agent_id}/history", summary="成长历史")
async def get_history(agent_id: str):
    """获取 Agent 的性格变化历史和里程碑。"""
    raise HTTPException(501, "TODO: Phase 1.5")


@app.post("/agents/{agent_id}/export", summary="导出交易数据")
async def export_for_trade(agent_id: str):
    """导出隐私清洗后的交易数据。"""
    raise HTTPException(501, "TODO: Phase 1.5")
