# 🧸 NFA Doll — AI 养成娃娃

> 基于 BAP-578 Non-Fungible Agent 协议的可养成 AI 伴侣  
> 每一次对话，都在塑造它独一无二的灵魂

## 项目概述

NFA Doll 是一个将 AI 对话与链上数字资产结合的养成系统。用户通过日常对话培养 AI 娃娃的性格，解锁隐藏特质，并可在链上铸造为 NFA（Non-Fungible Agent）进行展示和交易。

## 项目结构

```
nfa-doll/
├── backend/                # Python 后端
│   ├── core/               # 核心系统
│   │   ├── personality.py  # 六维性格 + 成长曲线 + 互斥对抗 + 衰减
│   │   ├── traits.py       # 20个隐藏特质 (8N/6R/4SR/2SSR)
│   │   ├── conversation.py # 对话引擎 (LLM调用 + 互动分析)
│   │   ├── memory.py       # 三层记忆 (短期/情景/长期)
│   │   └── prompt_builder.py # 动态 System Prompt 构建
│   ├── models/             # Pydantic 数据模型
│   │   └── agent.py        # AgentState 完整模型定义
│   ├── schemas/            # JSON Schema
│   │   └── agent_state.json
│   ├── api/                # FastAPI 服务 (Phase 1.5)
│   │   └── main.py
│   └── config.py           # 全局配置
├── contracts/              # Solidity 智能合约
│   └── NFADoll.sol         # BAP-578 NFA 合约
├── frontend/               # 前端
│   └── prototype/
│       └── agent-doll.jsx  # React 交互原型 (Claude Artifact)
├── scripts/                # 工具脚本
│   ├── demo.py             # 交互式演示
│   └── simulate.py         # 数值平衡测试 (模拟1000用户)
├── tests/                  # 测试
│   ├── test_personality.py
│   └── test_traits.py
├── docs/                   # 文档
│   ├── roadmap.md          # 完整开发路线图
│   └── trait_system.md     # 特质系统设计文档
├── pyproject.toml
└── .gitignore
```

## 核心系统

### 六维性格模型

| 维度 | 图标 | 互斥关系 |
|------|------|---------|
| 好奇心 | 🔍 | 独立 |
| 共情力 | 💗 | ↔ 勇气 (drag 0.25) |
| 勇气 | ⚡ | ↔ 共情力 (drag 0.25) |
| 创造力 | 🎨 | ↔ 智慧 (drag 0.20) |
| 智慧 | 📚 | ↔ 创造力 (drag 0.20) |
| 幽默感 | 😄 | 独立 |

### 成长机制

- **递减收益**: 数值越高增长越慢（sigmoid 曲线）
- **温和衰减**: 3天不互动后每天 -0.5，最低不低于5
- **连击加成**: 连续互动最高 1.5x 经验加成
- **等级系统**: Lv.1-100，前期快后期慢

### 隐藏特质

20个特质 (8N + 6R + 4SR + 2SSR)，一旦解锁永久保留。SSR 需要互斥维度同时达到高值 + 15%概率。

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest tests/ -v

# 交互式演示
python scripts/demo.py

# 数值平衡测试
python scripts/simulate.py

# 启动 API 服务 (Phase 1.5)
uvicorn backend.api.main:app --reload
```

## 技术栈

- **后端**: Python 3.11+ / FastAPI / Pydantic v2
- **AI**: Claude API (主) / GPT-4 (备选)
- **前端**: Next.js 14 / React / Tailwind CSS
- **合约**: Solidity ^0.8.20 / Hardhat / BNB Chain
- **存储**: PostgreSQL + Redis + IPFS

## 开发阶段

- [x] Phase 0: 可行性研究 + 原型验证
- [x] Phase 1.1: 人格状态模型设计
- [ ] Phase 1.2: 对话引擎开发
- [ ] Phase 1.3: 记忆系统
- [ ] Phase 1.4: 养成机制与游戏性
- [ ] Phase 1.5: 后端 API 服务
- [ ] Phase 2: 前端 + 链上集成
- [ ] Phase 3: 优化 + 社区
- [ ] Phase 4: 硬件整合
- [ ] Phase 5: 上线运营

## License

MIT
