# NFA Doll 开发大纲

## BAP-578 养成娃娃 · 从原型到上线的完整路径

---

## 项目概述

**产品定义：** 一个基于 BAP-578（Non-Fungible Agent）协议的 AI 养成娃娃。用户通过语音/文字对话从零培养娃娃的性格，养成结果可上链交易。最终形态包含实体硬件娃娃 + 云端 AI Agent + 链上 NFA 资产三层架构。

**核心价值主张：** AI 从"租用的服务"变成"拥有的资产"——你养出的性格独一无二，可验证、可交易、可增值。

**技术栈总览：**

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| AI 引擎 | Claude API / GPT API | 对话生成 + 性格演化判定 |
| 后端服务 | Python (FastAPI) | Agent 状态管理、记忆系统、API 网关 |
| 前端应用 | React / Next.js | 养成界面、性格可视化、交易市场 |
| 区块链层 | BNB Smart Chain + BAP-578 | NFA 铸造、学习验证、交易 |
| 链下存储 | IPFS + PostgreSQL | 对话记忆、行为数据、Vault 数据 |
| 硬件层 | ESP32 + 麦克风 + 扬声器 + 舵机 | 实体娃娃（Phase 4） |

---

## Phase 1：AI 养成核心系统（第 1-6 周）

> 目标：跑通"对话 → 性格变化 → 可感知成长"的核心循环

### 1.1 人格状态模型设计（第 1 周）

**任务清单：**

- 定义性格维度体系（6-8 个核心维度 + 隐藏特质系统）
- 设计 JSON Schema 数据结构，包含 persona、experience、stats、memory 等字段
- 确定数值范围（0-100）、成长曲线（前期快后期慢）、衰减机制
- 设计隐藏特质的触发条件和稀有度分级（N / R / SR / SSR）

**交付物：**

```
agent_state.json — 完整的人格状态 Schema
growth_curves.py — 成长曲线算法
trait_system.md — 隐藏特质设计文档
```

**关键设计决策：**

- 维度之间是否存在互斥关系（如勇气↑可能导致谨慎↓）
- 是否引入"遗忘机制"（长时间不互动某维度会缓慢下降）
- 隐藏特质是否可逆（一旦解锁是否永久保持）

### 1.2 对话引擎开发（第 2-3 周）

**任务清单：**

- 搭建 LLM 调用层（支持 Claude / GPT 多模型切换）
- 编写动态 System Prompt 模板（根据当前性格状态实时生成）
- 实现结构化输出解析（对话回复 + 心情 + 性格变动数值）
- 开发对话上下文管理（滑动窗口 + 摘要压缩）

**核心架构：**

```
用户输入
  ↓
对话引擎 (conversation_engine.py)
  ├── 构建 System Prompt ← 读取当前 agent_state
  ├── 组装 Message History ← 最近 N 轮 + 长期摘要
  ├── 调用 LLM API
  ├── 解析结构化响应 (reply, mood, stat_changes)
  └── 更新 agent_state → 写入数据库
  ↓
返回回复 + UI 更新指令
```

**交付物：**

```
conversation_engine.py — 对话引擎核心
prompt_builder.py — 动态 Prompt 构建器
response_parser.py — 结构化输出解析器
context_manager.py — 上下文/记忆管理
```

### 1.3 记忆系统（第 3-4 周）

**任务清单：**

- 实现三层记忆架构：短期记忆 / 情景记忆 / 长期性格记忆
- 开发记忆摘要算法（定期用 LLM 将对话压缩为摘要）
- 构建重要事件标记系统（用户生日、重大对话等自动检测并持久化）
- 实现记忆检索（向量相似度 或 关键词索引）

**三层记忆架构：**

```
短期记忆 (Short-term)
├── 最近 20 轮完整对话
├── 当前会话上下文
└── 存储：内存 / Redis

情景记忆 (Episodic)
├── 重要事件摘要（"主人教我认识了星座"）
├── 情感高峰时刻
├── 每日互动摘要
└── 存储：PostgreSQL

长期性格记忆 (Personality)
├── 性格维度数值
├── 行为模式统计
├── 偏好图谱
└── 存储：PostgreSQL + 链上 Merkle Root
```

**交付物：**

```
memory_manager.py — 记忆管理总控
short_term_memory.py — 短期记忆（滑动窗口）
episodic_memory.py — 情景记忆（摘要 + 检索）
personality_memory.py — 长期性格记忆
memory_summarizer.py — LLM 驱动的记忆压缩
```

### 1.4 养成机制与游戏性设计（第 4-5 周）

**任务清单：**

- 设计成长等级体系（Lv.1-100，每级需要的经验值递增）
- 实现隐藏特质触发系统（组合条件 + 随机因子）
- 设计"养成事件"系统（特定条件触发剧情对话）
- 开发性格平衡性测试工具（模拟 1000 个用户的养成路径分布）

**养成事件示例：**

```
事件：初次觉醒
触发条件：任意一个维度首次突破 50
效果：解锁"成长宣言"特殊对话，Agent 主动表达自我认知

事件：性格冲突
触发条件：两个互斥维度同时 > 60
效果：触发内心独白对话，Agent 表现出复杂性格

事件：隐藏觉醒
触发条件：特定维度组合达标 + 随机概率
效果：解锁 SSR 级隐藏特质，全局通知
```

**交付物：**

```
growth_system.py — 等级与经验值系统
trait_trigger.py — 隐藏特质触发引擎
event_system.py — 养成事件管理
balance_tester.py — 平衡性模拟测试工具
game_design.md — 完整的养成机制设计文档
```

### 1.5 后端 API 服务（第 5-6 周）

**任务清单：**

- 搭建 FastAPI 项目骨架
- 实现用户认证（JWT）
- 开发 Agent CRUD API（创建、读取、更新状态）
- 实现对话 API（Websocket 实时通信）
- 开发状态查询 API（性格面板、成长历史）

**API 端点设计：**

```
POST   /api/agent/create          — 创建新 Agent
GET    /api/agent/{id}/state      — 获取当前状态
POST   /api/agent/{id}/chat       — 发送消息（返回 SSE 流）
GET    /api/agent/{id}/stats      — 性格维度数据
GET    /api/agent/{id}/history    — 养成历史记录
GET    /api/agent/{id}/traits     — 已解锁特质列表
POST   /api/agent/{id}/sync       — 同步状态到链上（Phase 2）
```

**交付物：**

```
main.py — FastAPI 入口
routers/ — API 路由模块
models/ — 数据库模型（SQLAlchemy / Tortoise ORM）
services/ — 业务逻辑层
schemas/ — Pydantic 请求/响应模型
```

### Phase 1 里程碑验证

- [ ] 能通过 API 创建一个新 Agent 并进行 >50 轮对话
- [ ] 对话内容能可感知地影响性格数值
- [ ] Agent 的说话风格随性格变化而变化
- [ ] 能触发至少一个隐藏特质
- [ ] 记忆系统能在 50 轮后仍记住早期关键信息

---

## Phase 2：前端应用 + 链上集成（第 7-14 周）

> 目标：完整的 Web 应用 + BAP-578 NFA 铸造和验证

### 2.1 前端应用开发（第 7-10 周）

**页面结构：**

```
App
├── 首页 / 引导页
│   └── 创建你的娃娃（选择初始外观、起名）
├── 养成主页
│   ├── 娃娃形象展示（表情随心情变化）
│   ├── 对话区域（实时聊天）
│   ├── 性格变动动画（+3 好奇心 ↑ 浮动提示）
│   └── 快捷互动按钮（摸头、喂食、讲故事）
├── 性格面板
│   ├── 雷达图（六维可视化）
│   ├── 各维度进度条 + 历史曲线
│   ├── 隐藏特质收集面板（已解锁 / 未知）
│   └── 成长日记（自动记录里程碑事件）
├── 链上状态
│   ├── BAP-578 元数据展示
│   ├── Merkle Tree 学习记录
│   ├── 同步操作界面
│   └── 交易历史
├── 交易市场
│   ├── Agent 浏览 / 搜索 / 筛选
│   ├── Agent 详情页（试聊功能）
│   ├── 上架 / 购买 / 出价
│   └── 我的交易记录
└── 设置
    ├── 钱包连接（MetaMask / Trust Wallet）
    ├── 通知偏好
    └── 隐私设置
```

**技术选型：**

```
框架：Next.js 14 (App Router)
状态管理：Zustand
样式：Tailwind CSS + Framer Motion（动画）
图表：Recharts（性格可视化）
Web3：wagmi + viem（钱包连接 + 合约交互）
实时通信：WebSocket / SSE
```

**交付物：**

```
src/
├── app/                — Next.js 页面路由
├── components/
│   ├── doll/           — 娃娃形象相关组件
│   ├── chat/           — 对话界面组件
│   ├── stats/          — 性格可视化组件
│   ├── market/         — 交易市场组件
│   └── chain/          — 链上状态组件
├── hooks/              — 自定义 Hooks
├── stores/             — Zustand 状态管理
├── services/           — API 调用层
└── contracts/          — 合约 ABI + 交互函数
```

### 2.2 BAP-578 智能合约开发（第 9-11 周）

**任务清单：**

- 学习 BAP-578 标准合约接口
- 开发 NFA 工厂合约（创建 Agent Token）
- 实现 JSON Light Memory 模式（MVP 阶段）
- 实现 Merkle Tree Learning 模式（进阶养成验证）
- 开发学习状态更新合约逻辑
- 编写合约测试（Hardhat / Foundry）
- 部署到 BNB Chain 测试网

**合约架构：**

```
contracts/
├── NFAFactory.sol          — Agent 铸造工厂
├── NFAToken.sol            — BAP-578 兼容的 NFA 代币
├── LearningModule.sol      — Merkle Tree 学习验证模块
├── Marketplace.sol         — 交易市场合约
└── interfaces/
    └── IBAP578.sol         — BAP-578 标准接口
```

**关键合约函数：**

```solidity
// 铸造新 Agent
function createAgent(
    string name,
    string persona,        // JSON 编码的性格特征
    string experience,     // Agent 角色描述
    string vaultURI        // 链下数据存储地址
) → tokenId

// 启用学习功能
function enableLearning(
    uint256 tokenId,
    address learningModule,
    bytes32 initialRoot
)

// 更新学习状态（定期批量上链）
function updateLearningTree(
    uint256 tokenId,
    bytes32 newTreeRoot,
    bytes32[] merkleProof,
    bytes updateData
)

// 查询学习信息
function getLearningInfo(uint256 tokenId)
    → (enabled, moduleAddress, metrics)
```

**交付物：**

```
contracts/ — Solidity 合约源码
test/ — 合约测试
scripts/ — 部署脚本
hardhat.config.js — Hardhat 配置
```

### 2.3 链下存储与同步（第 11-12 周）

**任务清单：**

- 搭建 IPFS 节点或接入 Pinata/Web3.Storage
- 实现 Vault 数据打包（性格快照 + 记忆摘要 → IPFS）
- 开发 Merkle Tree 构建服务（将养成历史构建为树结构）
- 实现定时同步任务（积累 N 次交互后批量上链）
- 开发隐私清洗流程（交易前剥离私人对话，只保留性格数据）

**同步策略：**

```
每次对话 → 更新本地 agent_state (PostgreSQL)
每 50 次交互 或 每日 → 构建 Merkle Tree + 上传 IPFS + 更新链上 Root
上架交易前 → 执行隐私清洗 → 生成"可交易快照"
```

**交付物：**

```
sync_service.py — 链上同步任务
merkle_builder.py — Merkle Tree 构建
ipfs_uploader.py — IPFS 数据上传
privacy_cleaner.py — 隐私清洗（记忆蒸馏）
vault_manager.py — Vault 数据管理
```

### 2.4 交易市场 MVP（第 12-14 周）

**任务清单：**

- 开发市场合约（挂单、购买、取消、出价）
- 实现"试聊"功能（买家可与 Agent 对话 3-5 轮体验性格）
- 开发 Agent 估值展示（等级、交互次数、稀有特质、学习速度）
- 实现交易时的 NFA 所有权转移 + 链下数据迁移
- 开发稀有度排行榜

**交易流程：**

```
卖家上架
  ├── 执行隐私清洗
  ├── 生成可交易快照（性格 + 公开记忆 + Merkle Proof）
  ├── 设置价格
  └── 创建市场挂单 (Marketplace.sol)

买家浏览
  ├── 查看性格面板 + 稀有特质
  ├── 验证 Merkle Proof（确认养成真实性）
  ├── 试聊 3-5 轮
  └── 确认购买

交易完成
  ├── NFA Token 转移所有权
  ├── 链下 Vault 数据迁移给买家
  ├── 市场手续费扣除
  └── Agent 与新主人开始新对话（保留性格，适应新主人）
```

### Phase 2 里程碑验证

- [ ] 完整的 Web 应用可正常使用（创建 → 养成 → 查看状态）
- [ ] 能在 BNB 测试网铸造 NFA Token
- [ ] 养成数据能正确同步到链上（Merkle Root 可验证）
- [ ] 交易市场能完成至少一笔 NFA 买卖
- [ ] 试聊功能正常运作

---

## Phase 3：优化 + 社区功能（第 15-22 周）

> 目标：产品打磨 + 社交功能 + 公开测试

### 3.1 养成深度优化（第 15-17 周）

- 增加更多隐藏特质（扩展到 20+ 种）
- 实现"养成路线"系统（不同互动风格导向不同性格流派）
- 开发"Agent 日记"功能（Agent 自动撰写每日感悟）
- 增加情绪波动系统（心情不只是状态，而是有惯性和触发条件）
- 实现"成长回忆录"（可导出的养成历程 PDF）

### 3.2 社交与社区功能（第 17-19 周）

- Agent 之间的"见面"功能（两个 Agent 对话，产生化学反应）
- 养成排行榜（最高等级、最稀有特质、最活跃互动）
- 养成攻略社区（用户分享如何触发特定特质）
- Agent 性格展示页（可分享的卡片 / 链接）

### 3.3 经济系统完善（第 19-21 周）

- 实现交易平台手续费机制（平台抽成 2.5%）
- 开发"养成加速道具"系统（可选付费，加快特定维度成长）
- 实现"性格种子"售卖（特殊初始性格模板）
- 设计创作者分成机制（如果你的 Agent 被多次转售，原始创建者获得版税）

### 3.4 安全与防作弊（第 21-22 周）

- 实现交互频率限制（防止脚本刷养成）
- 开发异常行为检测（检测非自然对话模式）
- Merkle Proof 验证工具（买家可独立验证养成真实性）
- 合约安全审计（找第三方审计 Marketplace + NFA 合约）

### Phase 3 里程碑验证

- [ ] 至少 50 个测试用户完成完整养成流程
- [ ] 市场上有 >100 个 Agent 在交易
- [ ] 社交功能（Agent 见面）正常运作
- [ ] 无安全漏洞被发现

---

## Phase 4：硬件整合（第 23-32 周）

> 目标：将 AI Agent "注入"实体娃娃

### 4.1 硬件方案选型（第 23-24 周）

**推荐方案 A（低成本原型）：**

```
主控：ESP32-S3（支持 WiFi + 蓝牙 + 音频编解码）
音频输入：I2S MEMS 麦克风 (INMP441)
音频输出：I2S DAC + 小型扬声器 (MAX98357A)
动作：2-3 个微型舵机（头部转动 + 手臂摆动）
电源：3.7V 锂电池 + 充电模块
外壳：3D 打印原型 → 硅胶开模量产
预估 BOM 成本：¥80-120
```

**推荐方案 B（体验优先）：**

```
主控：Raspberry Pi Zero 2W
音频：USB 声卡 + 麦克风阵列 + 扬声器
动作：5 个舵机（更丰富的表情/动作）
显示：小型 OLED 屏（显示表情）
电源：5V 2A 锂电池组
预估 BOM 成本：¥200-300
```

### 4.2 固件开发（第 25-28 周）

**任务清单：**

- 开发 WiFi 配网模块（首次使用引导连接）
- 实现语音录制 → 云端 STT → 文字（使用 Whisper API）
- 实现云端 TTS → 语音播放（使用 Edge TTS / 自定义音色）
- 开发舵机动作库（点头、摇头、挥手、害羞等）
- 实现动作与对话情绪联动（开心时自动摆手，困了慢慢低头）
- 开发 OTA 固件更新机制

**语音对话流程：**

```
用户说话
  ↓ 麦克风采集
ESP32 检测语音活动 (VAD)
  ↓ 录音结束
上传音频到云端
  ↓
云端 STT (Whisper) → 文字
  ↓
调用 Agent 对话 API → 获取回复 + 心情 + 动作指令
  ↓
云端 TTS → 合成语音
  ↓ 下载音频
ESP32 播放语音 + 同步执行动作
```

### 4.3 娃娃设计与制造（第 27-32 周）

- 概念设计（用 Midjourney / AI 工具生成外观方案）
- 3D 建模（Blender / Fusion 360）
- 内部结构设计（电路板、舵机、电池的布局）
- 3D 打印原型测试
- 硅胶外壳开模（找深圳工厂）
- 小批量试产（50-100 台）

### Phase 4 里程碑验证

- [ ] 实体娃娃能完成完整的语音对话
- [ ] 从说话到回复的延迟 < 3 秒
- [ ] 动作与情绪正确联动
- [ ] 续航 > 2 小时持续对话
- [ ] 更换娃娃不影响 Agent 性格数据

---

## Phase 5：上线运营（第 33 周+）

### 5.1 上线准备

- 主网合约部署 + 最终安全审计
- CDN + 服务器部署（推荐 Vercel + AWS / Cloudflare Workers）
- 客服系统搭建
- 法律合规审查（隐私政策、用户协议、NFT 交易合规）

### 5.2 运营策略

- 内测邀请制（首批 500 个 NFA 铸造名额）
- 社交媒体运营（展示有趣的养成案例）
- KOL 合作（送娃娃 + Agent 给科技博主体验）
- 社区建设（Discord / Telegram 养成攻略社群）

### 5.3 商业模式

```
收入来源                    预估占比
──────────────────────────────────
硬件销售（娃娃本体）          35%
NFA 铸造费（0.01 BNB/个）    10%
交易市场手续费（2.5%）        25%
养成道具 / 加速器             15%
性格种子 / 特殊模板           10%
企业定制 / API 授权            5%
```

---

## 独立开发者 AI 辅助工作流

### 日常开发流程

```
1. 需求拆解 → 用 Claude 把模糊想法转化为具体任务清单
2. 架构设计 → 用 Claude 画数据流图、设计 API 接口、审查 Schema
3. 编码实现 → 用 Claude Code / Cursor 辅助编码
4. 测试调试 → 用 Claude 生成测试用例 + 模拟养成对话测试
5. 文档编写 → 用 Claude 生成 API 文档、README、部署指南
```

### 推荐工具链

```
编码：Claude Code / Cursor（主力）
设计：Midjourney / Flux（概念图）+ v0.dev（UI 组件）
项目管理：Linear / Notion（任务跟踪）
版本控制：GitHub
CI/CD：GitHub Actions
部署：Vercel（前端）+ Railway / Fly.io（后端）
监控：Sentry（错误追踪）+ Posthog（用户行为）
```

### 成本预估（独立开发者 6 个月）

```
类目                    月均费用
──────────────────────────────
LLM API 调用            ¥500-2000（开发阶段）
服务器 / 云服务          ¥200-500
域名 + CDN              ¥50
BNB 测试网 Gas           免费
工具订阅                 ¥200-500（Cursor / Claude Pro）
3D 打印原型              ¥500（一次性）
──────────────────────────────
合计：约 ¥1000-3000/月
```

---

## 风险清单与应对策略

| 风险 | 影响 | 应对 |
|------|------|------|
| LLM API 成本失控 | 高 | 实现记忆摘要压缩 Token 用量；设置每用户每日对话上限；后期考虑微调小模型 |
| 养成缺乏深度，用户玩几天就腻 | 高 | 持续增加隐藏特质和养成事件；引入社交玩法；定期推出限时养成活动 |
| 性格数据被篡改/伪造 | 中 | Merkle Tree 验证；链上记录交互次数；异常检测系统 |
| 隐私泄露（对话内容随 Agent 交易流出） | 高 | 严格的隐私清洗流程；只转移性格模型，不转移原始对话 |
| BNB Chain 生态风险 | 中 | 架构设计时预留跨链能力；BAP-578 兼容 ERC-721，可迁移 |
| 硬件量产质量问题 | 中 | 先小批量试产；软件先行，硬件可选 |

---

## 快速启动：今天就可以做的事

1. **创建 GitHub 仓库**，初始化项目结构
2. **设计 `agent_state.json` Schema**——这是整个系统的地基
3. **写第一版 System Prompt**，在 Claude 对话框里手动测试养成效果
4. **用 FastAPI 搭建最简 API**——一个创建 Agent 端点 + 一个对话端点
5. **参考本项目的前端原型**，在 Next.js 里搭建聊天界面

> 最重要的原则：先让核心循环跑起来（对话 → 性格变化 → 感知到成长），其他一切都可以后加。
