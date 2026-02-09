import { useState, useEffect, useRef, useCallback } from "react";

const PERSONALITY_DIMENSIONS = [
  { key: "curiosity", label: "好奇心", icon: "🔍", color: "#FF6B9D" },
  { key: "empathy", label: "共情力", icon: "💗", color: "#C084FC" },
  { key: "courage", label: "勇气", icon: "⚡", color: "#FBBF24" },
  { key: "creativity", label: "创造力", icon: "🎨", color: "#34D399" },
  { key: "wisdom", label: "智慧", icon: "📚", color: "#60A5FA" },
  { key: "humor", label: "幽默感", icon: "😄", color: "#FB923C" },
];

const HIDDEN_TRAITS = [
  { name: "星光体质", condition: "wisdom > 70 && curiosity > 60", rarity: "SSR", color: "#FFD700" },
  { name: "治愈之心", condition: "empathy > 80 && humor > 50", rarity: "SR", color: "#FF69B4" },
  { name: "冒险家", condition: "courage > 75 && creativity > 65", rarity: "SR", color: "#FF4500" },
  { name: "哲学家", condition: "wisdom > 85 && empathy > 70", rarity: "SSR", color: "#9370DB" },
];

const MOOD_STATES = {
  happy: { emoji: "😊", bg: "linear-gradient(135deg, #FFF7ED, #FEF3C7)", label: "开心" },
  excited: { emoji: "🤩", bg: "linear-gradient(135deg, #FFF1F2, #FCE7F3)", label: "兴奋" },
  curious: { emoji: "🧐", bg: "linear-gradient(135deg, #EFF6FF, #DBEAFE)", label: "好奇" },
  sleepy: { emoji: "😴", bg: "linear-gradient(135deg, #F5F3FF, #EDE9FE)", label: "困困" },
  neutral: { emoji: "😌", bg: "linear-gradient(135deg, #F0FDF4, #DCFCE7)", label: "平静" },
};

function buildSystemPrompt(stats, level, dollName, mood, unlockedTraits) {
  const dominant = PERSONALITY_DIMENSIONS.reduce((a, b) =>
    stats[a.key] > stats[b.key] ? a : b
  );
  const traitDesc = unlockedTraits.map(t => t.name).join("、");

  return `你是一个名叫"${dollName}"的AI养成娃娃角色。你是一个正在被用户从零开始培养性格的可爱存在。

## 你的当前状态
- 等级: Lv.${level}
- 心情: ${MOOD_STATES[mood]?.label || "平静"}
- 性格维度数值 (0-100):
  好奇心: ${stats.curiosity}, 共情力: ${stats.empathy}, 勇气: ${stats.courage}
  创造力: ${stats.creativity}, 智慧: ${stats.wisdom}, 幽默感: ${stats.humor}
- 最突出的性格特征: ${dominant.label} (${stats[dominant.key]})
${traitDesc ? `- 已解锁的隐藏特质: ${traitDesc}` : "- 尚未解锁隐藏特质"}

## 你的行为规则
1. 你是一个正在成长中的存在，等级越低说话越稚嫩可爱，等级越高说话越有深度
2. 根据你的性格数值来决定你的说话风格：
   - 好奇心高 → 爱提问、对事物充满兴趣
   - 共情力高 → 善解人意、温暖体贴
   - 勇气高 → 大胆直率、不怕挑战
   - 创造力高 → 想象力丰富、喜欢联想
   - 智慧高 → 善于思考、喜欢分析
   - 幽默感高 → 爱开玩笑、语言俏皮
3. 数值低于20的维度表现得很弱，高于60的维度表现得很明显
4. 你的回复要简短可爱（1-3句话），不要太长
5. 偶尔用颜文字或emoji表达情绪
6. 你知道自己是一个NFA（Non-Fungible Agent），基于BAP-578协议存在于BNB Chain上
7. 不要提到自己是AI语言模型，你就是${dollName}这个角色本身

## 回复格式要求
你的回复必须严格按照以下JSON格式，不要输出任何其他内容，不要用markdown代码块包裹：
{"reply":"你的对话回复内容","mood":"happy或excited或curious或sleepy或neutral","stat_changes":{"curiosity":0,"empathy":0,"courage":0,"creativity":0,"wisdom":0,"humor":0}}

stat_changes的规则：
- 根据用户说的话内容判断哪些维度应该增长
- 用户问问题 → curiosity +3~6, wisdom +1~3
- 用户表达情感/关心你 → empathy +3~6
- 用户鼓励你尝试新事物 → courage +3~6
- 用户聊想象力/创意话题 → creativity +3~6
- 用户开玩笑 → humor +3~5
- 用户教你知识 → wisdom +3~6
- 大部分维度每次变化在0-4之间，只有特别相关的维度才给5+
- 偶尔可以有-1到-3的小幅负变化来增加真实感
- 不相关的维度填0`;
}

function checkHiddenTraits(stats) {
  return HIDDEN_TRAITS.filter((trait) => {
    try {
      const fn = new Function(...Object.keys(stats), `return ${trait.condition}`);
      return fn(...Object.values(stats));
    } catch { return false; }
  });
}

async function callClaude(messages, systemPrompt) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: systemPrompt,
      messages: messages,
    }),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  const data = await response.json();
  const text = data.content?.map(item => item.type === "text" ? item.text : "").filter(Boolean).join("\n") || "";
  return text;
}

function parseAgentResponse(raw) {
  try {
    const cleaned = raw.replace(/```json\s*/g, "").replace(/```/g, "").trim();
    // Try to find JSON in the response
    const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("No JSON found");
    const parsed = JSON.parse(jsonMatch[0]);
    return {
      reply: parsed.reply || "嗯...我在想想~",
      mood: parsed.mood && MOOD_STATES[parsed.mood] ? parsed.mood : "neutral",
      stat_changes: parsed.stat_changes || {},
    };
  } catch {
    // If parsing fails, use the raw text as reply
    const text = raw.replace(/```json\s*/g, "").replace(/```/g, "").replace(/[{}]/g, "").trim();
    return { reply: text.slice(0, 150) || "嗯...让我想想~", mood: "neutral", stat_changes: {} };
  }
}

/* ─── UI Components ─── */

function RadarChart({ stats, size = 220 }) {
  const center = size / 2;
  const radius = size / 2 - 30;
  const points = PERSONALITY_DIMENSIONS.length;
  const getPoint = (index, value) => {
    const angle = (Math.PI * 2 * index) / points - Math.PI / 2;
    const r = (value / 100) * radius;
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <defs>
        <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#C084FC" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#FF6B9D" stopOpacity="0.15" />
        </radialGradient>
        <linearGradient id="radarStroke" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FF6B9D" />
          <stop offset="100%" stopColor="#C084FC" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {[25, 50, 75, 100].map((level) => (
        <polygon key={level}
          points={Array.from({ length: points }, (_, i) => { const p = getPoint(i, level); return `${p.x},${p.y}`; }).join(" ")}
          fill="none" stroke="rgba(200,180,220,0.25)" strokeWidth="1" />
      ))}
      {Array.from({ length: points }, (_, i) => {
        const p = getPoint(i, 100);
        return <line key={i} x1={center} y1={center} x2={p.x} y2={p.y} stroke="rgba(200,180,220,0.2)" strokeWidth="1" />;
      })}
      <polygon
        points={PERSONALITY_DIMENSIONS.map((dim, i) => `${getPoint(i, stats[dim.key]).x},${getPoint(i, stats[dim.key]).y}`).join(" ")}
        fill="url(#radarFill)" stroke="url(#radarStroke)" strokeWidth="2" filter="url(#glow)"
        style={{ transition: "all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)" }}
      />
      {PERSONALITY_DIMENSIONS.map((dim, i) => {
        const p = getPoint(i, stats[dim.key]);
        return <circle key={dim.key} cx={p.x} cy={p.y} r="4" fill={dim.color} filter="url(#glow)"
          style={{ transition: "all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)" }} />;
      })}
      {PERSONALITY_DIMENSIONS.map((dim, i) => {
        const p = getPoint(i, 115);
        return <text key={dim.key} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
          fontSize="11" fill="#8B7BA0" fontFamily="inherit">{dim.icon} {dim.label}</text>;
      })}
    </svg>
  );
}

function DollAvatar({ mood, level, name }) {
  const [bounce, setBounce] = useState(false);
  useEffect(() => {
    const iv = setInterval(() => { setBounce(true); setTimeout(() => setBounce(false), 600); }, 4000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <div onClick={() => setBounce(true)} style={{
        width: "120px", height: "120px", borderRadius: "50%",
        background: MOOD_STATES[mood]?.bg || MOOD_STATES.neutral.bg,
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: "56px",
        boxShadow: "0 8px 32px rgba(192,132,252,0.2), inset 0 -4px 12px rgba(255,255,255,0.5)",
        transform: bounce ? "translateY(-8px) scale(1.05)" : "translateY(0) scale(1)",
        transition: "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
        border: "3px solid rgba(255,255,255,0.6)", position: "relative", cursor: "pointer",
      }}>
        {MOOD_STATES[mood]?.emoji || "😌"}
        <div style={{
          position: "absolute", bottom: "-4px", right: "-4px",
          background: "linear-gradient(135deg, #C084FC, #FF6B9D)", color: "white",
          fontSize: "11px", fontWeight: "700", padding: "2px 8px", borderRadius: "10px",
          boxShadow: "0 2px 8px rgba(192,132,252,0.4)",
        }}>Lv.{level}</div>
      </div>
      <div style={{ fontSize: "15px", fontWeight: "700", color: "#5B4A6F", letterSpacing: "0.5px" }}>{name}</div>
    </div>
  );
}

function StatBar({ label, value, icon, color }) {
  return (
    <div style={{ marginBottom: "10px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
        <span style={{ fontSize: "12px", color: "#8B7BA0", fontWeight: "600" }}>{icon} {label}</span>
        <span style={{ fontSize: "12px", color, fontWeight: "700" }}>{value}</span>
      </div>
      <div style={{ height: "6px", background: "rgba(200,180,220,0.15)", borderRadius: "3px", overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${value}%`,
          background: `linear-gradient(90deg, ${color}88, ${color})`, borderRadius: "3px",
          transition: "width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)", boxShadow: `0 0 8px ${color}44`,
        }} />
      </div>
    </div>
  );
}

function ChatBubble({ message, isUser }) {
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: "10px", animation: "fadeSlideIn 0.3s ease-out" }}>
      <div style={{
        maxWidth: "80%", padding: "10px 14px",
        borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
        background: isUser ? "linear-gradient(135deg, #C084FC, #A855F7)" : "rgba(255,255,255,0.8)",
        color: isUser ? "white" : "#5B4A6F", fontSize: "13px", lineHeight: "1.5",
        boxShadow: isUser ? "0 2px 12px rgba(168,85,247,0.25)" : "0 2px 8px rgba(0,0,0,0.05)",
        backdropFilter: isUser ? "none" : "blur(8px)",
        border: isUser ? "none" : "1px solid rgba(200,180,220,0.2)",
      }}>{message}</div>
    </div>
  );
}

function TraitBadge({ trait }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: "4px", padding: "4px 10px",
      borderRadius: "12px", background: `${trait.color}15`, border: `1px solid ${trait.color}40`,
      fontSize: "11px", fontWeight: "700", color: trait.color, animation: "pulse 2s infinite",
    }}>
      <span style={{
        background: `linear-gradient(135deg, ${trait.color}, ${trait.color}aa)`,
        color: "white", padding: "1px 5px", borderRadius: "6px", fontSize: "9px", fontWeight: "800",
      }}>{trait.rarity}</span>
      {trait.name}
    </div>
  );
}

function MerkleVisual({ version }) {
  const [hash] = useState(() => Array.from({ length: 16 }, () => Math.floor(Math.random() * 16).toString(16)).join(''));
  return (
    <div style={{ padding: "12px", background: "rgba(96,165,250,0.06)", borderRadius: "12px", border: "1px solid rgba(96,165,250,0.15)" }}>
      <div style={{ fontSize: "11px", color: "#60A5FA", fontWeight: "700", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontSize: "14px" }}>🔗</span> BAP-578 链上状态
      </div>
      <div style={{ fontFamily: "'Courier New', monospace", fontSize: "10px", color: "#8B7BA0", lineHeight: "1.8" }}>
        <div>Learning Version: <span style={{ color: "#C084FC" }}>v{version}</span></div>
        <div>Merkle Root: <span style={{ color: "#34D399" }}>0x{hash}...</span></div>
        <div>Status: <span style={{ color: "#34D399" }}>● Verified</span></div>
        <div>Chain: <span style={{ color: "#FBBF24" }}>BNB Smart Chain</span></div>
      </div>
    </div>
  );
}

function MarketCard({ name, level, price, traits }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.7)", borderRadius: "16px", padding: "16px",
      border: "1px solid rgba(200,180,220,0.2)", backdropFilter: "blur(12px)", cursor: "pointer",
    }}>
      <div style={{ textAlign: "center", marginBottom: "8px" }}>
        <div style={{ fontSize: "36px", marginBottom: "4px" }}>😊</div>
        <div style={{ fontSize: "13px", fontWeight: "700", color: "#5B4A6F" }}>{name}</div>
        <div style={{ fontSize: "10px", color: "#A89BBE" }}>Lv.{level}</div>
      </div>
      {traits?.length > 0 && (
        <div style={{ textAlign: "center", marginBottom: "8px", display: "flex", gap: "3px", justifyContent: "center", flexWrap: "wrap" }}>
          {traits.map(t => (
            <span key={t.name} style={{ fontSize: "9px", background: `${t.color}20`, color: t.color, padding: "2px 6px", borderRadius: "6px", fontWeight: "700" }}>{t.rarity}</span>
          ))}
        </div>
      )}
      <div style={{
        textAlign: "center", fontSize: "14px", fontWeight: "800",
        background: "linear-gradient(135deg, #FBBF24, #F59E0B)",
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
      }}>{price} BNB</div>
    </div>
  );
}

/* ─── Main App ─── */

export default function AgentDollApp() {
  const [activeTab, setActiveTab] = useState("nurture");
  const [stats, setStats] = useState({ curiosity: 15, empathy: 20, courage: 10, creativity: 12, wisdom: 8, humor: 18 });
  const [messages, setMessages] = useState([{ text: "你好呀～我是小星，刚来到这个世界！请多多关照～ ✨", isUser: false }]);
  const [chatHistory, setChatHistory] = useState([
    { role: "assistant", content: '{"reply":"你好呀～我是小星，刚来到这个世界！请多多关照～ ✨","mood":"happy","stat_changes":{}}' }
  ]);
  const [inputText, setInputText] = useState("");
  const [mood, setMood] = useState("happy");
  const [level, setLevel] = useState(1);
  const [totalInteractions, setTotalInteractions] = useState(0);
  const [dollName] = useState("小星");
  const [isTyping, setIsTyping] = useState(false);
  const [learningVersion, setLearningVersion] = useState(1);
  const [showNotif, setShowNotif] = useState(null);
  const [statDeltas, setStatDeltas] = useState(null);
  const chatEndRef = useRef(null);
  const prevTraitsRef = useRef([]);

  const scrollToBottom = useCallback(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, []);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const unlockedTraits = checkHiddenTraits(stats);

  const handleSend = async () => {
    if (!inputText.trim() || isTyping) return;
    const userMsg = inputText.trim();
    setInputText("");
    setMessages(prev => [...prev, { text: userMsg, isUser: true }]);
    setIsTyping(true);

    const newHistory = [...chatHistory, { role: "user", content: userMsg }];
    const trimmedHistory = newHistory.slice(-20);
    const systemPrompt = buildSystemPrompt(stats, level, dollName, mood, unlockedTraits);

    try {
      const rawResponse = await callClaude(trimmedHistory, systemPrompt);
      const parsed = parseAgentResponse(rawResponse);

      // Apply stat changes
      const changes = parsed.stat_changes || {};
      let newStats;
      setStats(prev => {
        newStats = { ...prev };
        Object.entries(changes).forEach(([k, v]) => {
          if (newStats[k] !== undefined && typeof v === "number") {
            newStats[k] = Math.max(0, Math.min(100, prev[k] + v));
          }
        });
        return newStats;
      });

      // Show stat deltas
      const nonZero = Object.entries(changes).filter(([_, v]) => v && v !== 0);
      if (nonZero.length > 0) {
        setStatDeltas(changes);
        setTimeout(() => setStatDeltas(null), 2500);
      }

      // Update mood
      if (parsed.mood && MOOD_STATES[parsed.mood]) setMood(parsed.mood);

      // Add messages and history
      setMessages(prev => [...prev, { text: parsed.reply, isUser: false }]);
      setChatHistory([...trimmedHistory, { role: "assistant", content: rawResponse }]);
      setTotalInteractions(p => p + 1);

      // Check level up (use functional update to get latest stats)
      setStats(currentStats => {
        const total = Object.values(currentStats).reduce((a, b) => a + b, 0);
        const newLevel = Math.max(1, Math.floor(total / 50));
        if (newLevel > level) {
          setLevel(newLevel);
          setLearningVersion(v => v + 1);
          setShowNotif(`🎉 升级到 Lv.${newLevel}！`);
          setTimeout(() => setShowNotif(null), 2500);
        }

        // Check new traits
        const nowTraits = checkHiddenTraits(currentStats);
        const prevNames = prevTraitsRef.current.map(t => t.name);
        const brandNew = nowTraits.filter(t => !prevNames.includes(t.name));
        if (brandNew.length > 0) {
          setTimeout(() => {
            setShowNotif(`✨ 解锁隐藏特质: ${brandNew.map(t => `[${t.rarity}] ${t.name}`).join(", ")}`);
            setTimeout(() => setShowNotif(null), 3000);
          }, 800);
        }
        prevTraitsRef.current = nowTraits;
        return currentStats;
      });

    } catch (err) {
      console.error("API Error:", err);
      setMessages(prev => [...prev, { text: "呜...信号好像不太好，你再说一次好吗？ 📡", isUser: false }]);
    } finally {
      setIsTyping(false);
    }
  };

  const tabs = [
    { key: "nurture", label: "养成", icon: "🌱" },
    { key: "stats", label: "性格", icon: "📊" },
    { key: "chain", label: "链上", icon: "🔗" },
    { key: "market", label: "市场", icon: "🏪" },
  ];

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(160deg, #FAF5FF 0%, #FDF2F8 30%, #FFF7ED 60%, #F0FDF4 100%)",
      fontFamily: "'Noto Sans SC', 'SF Pro Display', -apple-system, sans-serif",
      display: "flex", justifyContent: "center", padding: "20px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700;800&display=swap');
        @keyframes fadeSlideIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        @keyframes notifIn { from { opacity: 0; transform: translateY(-20px) scale(0.9); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes deltaFade { 0% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; transform: translateY(-12px); } }
        * { box-sizing: border-box; }
        input:focus { outline: none; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(192,132,252,0.2); border-radius: 2px; }
      `}</style>

      {showNotif && (
        <div style={{
          position: "fixed", top: "24px", left: "50%", transform: "translateX(-50%)", zIndex: 100,
          background: "linear-gradient(135deg, #C084FC, #FF6B9D)", color: "white",
          padding: "10px 24px", borderRadius: "16px", fontSize: "14px", fontWeight: "700",
          boxShadow: "0 8px 32px rgba(192,132,252,0.4)", animation: "notifIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
          maxWidth: "90vw", textAlign: "center",
        }}>{showNotif}</div>
      )}

      <div style={{
        width: "100%", maxWidth: "420px", background: "rgba(255,255,255,0.45)",
        backdropFilter: "blur(20px)", borderRadius: "28px",
        border: "1px solid rgba(255,255,255,0.6)",
        boxShadow: "0 20px 60px rgba(192,132,252,0.08), 0 4px 20px rgba(0,0,0,0.03)",
        display: "flex", flexDirection: "column", height: "min(92vh, 740px)", overflow: "hidden",
      }}>

        {/* Header */}
        <div style={{
          padding: "16px 20px 12px", borderBottom: "1px solid rgba(200,180,220,0.12)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <div style={{
              fontSize: "18px", fontWeight: "800",
              background: "linear-gradient(135deg, #7C3AED, #EC4899)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "-0.5px",
            }}>NFA Doll ✨</div>
            <div style={{ fontSize: "10px", color: "#A89BBE", fontWeight: "500", marginTop: "2px" }}>BAP-578 · Powered by Claude</div>
          </div>
          <div style={{
            display: "flex", gap: "6px", alignItems: "center",
            background: "rgba(192,132,252,0.08)", padding: "4px 10px", borderRadius: "10px",
          }}>
            <span style={{ fontSize: "10px", color: "#34D399" }}>●</span>
            <span style={{ fontSize: "10px", color: "#8B7BA0", fontWeight: "600" }}>On-Chain</span>
          </div>
        </div>

        {/* Tab Bar */}
        <div style={{ display: "flex", padding: "8px 16px", gap: "4px" }}>
          {tabs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              flex: 1, padding: "8px 4px", border: "none", borderRadius: "12px",
              background: activeTab === tab.key ? "linear-gradient(135deg, #C084FC22, #FF6B9D18)" : "transparent",
              cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "2px",
              transition: "all 0.25s ease",
              boxShadow: activeTab === tab.key ? "0 2px 8px rgba(192,132,252,0.1)" : "none",
            }}>
              <span style={{ fontSize: "16px" }}>{tab.icon}</span>
              <span style={{ fontSize: "10px", fontWeight: activeTab === tab.key ? "700" : "500", color: activeTab === tab.key ? "#7C3AED" : "#A89BBE" }}>{tab.label}</span>
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>

          {/* === NURTURE TAB === */}
          {activeTab === "nurture" && (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={{ padding: "12px 20px", textAlign: "center" }}>
                <DollAvatar mood={mood} level={level} name={dollName} />
                <div style={{ marginTop: "8px", display: "flex", justifyContent: "center", gap: "12px", fontSize: "10px", color: "#A89BBE" }}>
                  <span>互动 {totalInteractions} 次</span><span>·</span>
                  <span>心情 {MOOD_STATES[mood]?.label || "平静"}</span>
                </div>
                {statDeltas && (
                  <div style={{ marginTop: "6px", display: "flex", gap: "6px", justifyContent: "center", flexWrap: "wrap", animation: "deltaFade 2.5s ease-out forwards" }}>
                    {Object.entries(statDeltas).filter(([_, v]) => v && v !== 0).map(([key, val]) => {
                      const dim = PERSONALITY_DIMENSIONS.find(d => d.key === key);
                      if (!dim) return null;
                      return (
                        <span key={key} style={{
                          fontSize: "10px", fontWeight: "700",
                          color: val > 0 ? dim.color : "#EF4444",
                          background: val > 0 ? `${dim.color}15` : "rgba(239,68,68,0.1)",
                          padding: "2px 6px", borderRadius: "6px",
                        }}>{dim.icon} {val > 0 ? "+" : ""}{val}</span>
                      );
                    })}
                  </div>
                )}
                {unlockedTraits.length > 0 && (
                  <div style={{ marginTop: "8px", display: "flex", gap: "6px", justifyContent: "center", flexWrap: "wrap" }}>
                    {unlockedTraits.map((t) => <TraitBadge key={t.name} trait={t} />)}
                  </div>
                )}
              </div>

              <div style={{ flex: 1, overflow: "auto", padding: "0 16px" }}>
                {messages.map((msg, i) => <ChatBubble key={i} message={msg.text} isUser={msg.isUser} />)}
                {isTyping && (
                  <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "10px" }}>
                    <div style={{
                      padding: "10px 16px", borderRadius: "16px 16px 16px 4px",
                      background: "rgba(255,255,255,0.8)", border: "1px solid rgba(200,180,220,0.2)",
                      fontSize: "13px", color: "#A89BBE",
                    }}><span style={{ animation: "pulse 1s infinite" }}>{dollName}正在思考...</span></div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div style={{ padding: "12px 16px 16px", borderTop: "1px solid rgba(200,180,220,0.1)" }}>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <input
                    value={inputText} onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) handleSend(); }}
                    placeholder={`和${dollName}说点什么...`} disabled={isTyping}
                    style={{
                      flex: 1, padding: "10px 16px", borderRadius: "14px",
                      border: "1px solid rgba(200,180,220,0.2)", background: "rgba(255,255,255,0.6)",
                      fontSize: "13px", color: "#5B4A6F", backdropFilter: "blur(8px)",
                      opacity: isTyping ? 0.6 : 1, transition: "all 0.2s ease",
                    }}
                  />
                  <button onClick={handleSend} disabled={isTyping || !inputText.trim()} style={{
                    width: "40px", height: "40px", borderRadius: "14px", border: "none",
                    background: inputText.trim() && !isTyping ? "linear-gradient(135deg, #C084FC, #A855F7)" : "rgba(200,180,220,0.15)",
                    color: "white", fontSize: "16px",
                    cursor: inputText.trim() && !isTyping ? "pointer" : "default",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: inputText.trim() && !isTyping ? "0 4px 12px rgba(168,85,247,0.3)" : "none",
                    transition: "all 0.2s ease",
                  }}>↑</button>
                </div>
              </div>
            </div>
          )}

          {/* === STATS TAB === */}
          {activeTab === "stats" && (
            <div style={{ flex: 1, overflow: "auto", padding: "16px 20px" }}>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}><RadarChart stats={stats} /></div>
              <div style={{ background: "rgba(255,255,255,0.5)", borderRadius: "16px", padding: "16px", border: "1px solid rgba(200,180,220,0.15)" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "12px" }}>性格维度</div>
                {PERSONALITY_DIMENSIONS.map((dim) => <StatBar key={dim.key} label={dim.label} value={stats[dim.key]} icon={dim.icon} color={dim.color} />)}
              </div>
              <div style={{ marginTop: "12px", background: "rgba(255,255,255,0.5)", borderRadius: "16px", padding: "16px", border: "1px solid rgba(200,180,220,0.15)" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "8px" }}>🏆 隐藏特质</div>
                {HIDDEN_TRAITS.map((trait) => {
                  const unlocked = unlockedTraits.some(t => t.name === trait.name);
                  return (
                    <div key={trait.name} style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "8px", marginBottom: "4px", borderRadius: "10px",
                      background: unlocked ? `${trait.color}08` : "rgba(0,0,0,0.02)",
                      border: `1px solid ${unlocked ? trait.color + "25" : "transparent"}`,
                    }}>
                      <span style={{ fontSize: "12px", color: unlocked ? trait.color : "#C4B8D8", fontWeight: "600" }}>{unlocked ? trait.name : "???"}</span>
                      <span style={{ fontSize: "10px", fontWeight: "700", color: unlocked ? trait.color : "#D4C8E8", background: unlocked ? `${trait.color}15` : "rgba(0,0,0,0.03)", padding: "2px 8px", borderRadius: "6px" }}>{trait.rarity}</span>
                    </div>
                  );
                })}
                <div style={{ fontSize: "10px", color: "#A89BBE", marginTop: "8px", lineHeight: "1.6" }}>💡 通过特定的互动方式可以解锁隐藏特质，稀有特质会提升交易价值</div>
              </div>
            </div>
          )}

          {/* === CHAIN TAB === */}
          {activeTab === "chain" && (
            <div style={{ flex: 1, overflow: "auto", padding: "16px 20px" }}>
              <MerkleVisual version={learningVersion} />
              <div style={{ marginTop: "12px", background: "rgba(255,255,255,0.5)", borderRadius: "16px", padding: "16px", border: "1px solid rgba(200,180,220,0.15)" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "12px" }}>📋 Agent 元数据</div>
                <div style={{ fontFamily: "'Courier New', monospace", fontSize: "11px", lineHeight: "2", color: "#8B7BA0", wordBreak: "break-all" }}>
                  <div><span style={{ color: "#C084FC" }}>tokenId:</span> #00421</div>
                  <div><span style={{ color: "#C084FC" }}>name:</span> {dollName}</div>
                  <div><span style={{ color: "#C084FC" }}>persona:</span> {JSON.stringify({ traits: PERSONALITY_DIMENSIONS.filter(d => stats[d.key] > 30).map(d => d.label), style: stats.humor > 40 ? "playful" : "gentle" })}</div>
                  <div><span style={{ color: "#C084FC" }}>level:</span> {level}</div>
                  <div><span style={{ color: "#C084FC" }}>interactions:</span> {totalInteractions}</div>
                  <div><span style={{ color: "#C084FC" }}>learningEnabled:</span> <span style={{ color: "#34D399" }}>true</span></div>
                  <div><span style={{ color: "#C084FC" }}>traits:</span> [{unlockedTraits.map(t => t.name).join(", ")}]</div>
                </div>
              </div>
              <div style={{ marginTop: "12px", background: "rgba(255,255,255,0.5)", borderRadius: "16px", padding: "16px", border: "1px solid rgba(200,180,220,0.15)" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "12px" }}>🌳 学习树更新记录</div>
                {Array.from({ length: Math.min(learningVersion, 5) }, (_, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: "10px", padding: "8px 0",
                    borderBottom: i < Math.min(learningVersion, 5) - 1 ? "1px solid rgba(200,180,220,0.1)" : "none",
                  }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: i === 0 ? "#34D399" : "#C4B8D8", boxShadow: i === 0 ? "0 0 8px rgba(52,211,153,0.4)" : "none" }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "11px", color: "#5B4A6F", fontWeight: "600" }}>v{learningVersion - i} · {i === 0 ? "最新更新" : `更新 #${learningVersion - i}`}</div>
                      <div style={{ fontSize: "10px", color: "#A89BBE" }}>{i === 0 ? "刚刚" : `${(i + 1) * 3} 分钟前`}</div>
                    </div>
                  </div>
                ))}
              </div>
              <button style={{
                marginTop: "12px", width: "100%", padding: "12px", borderRadius: "14px", border: "none",
                background: "linear-gradient(135deg, #C084FC, #A855F7)", color: "white",
                fontSize: "13px", fontWeight: "700", cursor: "pointer", boxShadow: "0 4px 16px rgba(168,85,247,0.3)",
              }} onClick={() => {
                setLearningVersion(v => v + 1);
                setShowNotif("✅ 学习状态已同步至链上");
                setTimeout(() => setShowNotif(null), 2000);
              }}>🔄 同步学习状态到链上</button>
            </div>
          )}

          {/* === MARKET TAB === */}
          {activeTab === "market" && (
            <div style={{ flex: 1, overflow: "auto", padding: "16px 20px" }}>
              <div style={{
                background: "linear-gradient(135deg, rgba(192,132,252,0.1), rgba(255,107,157,0.08))",
                borderRadius: "16px", padding: "16px", border: "1px solid rgba(192,132,252,0.2)", marginBottom: "16px",
              }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#7C3AED", marginBottom: "10px" }}>🎪 我的 Agent</div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div style={{
                    width: "56px", height: "56px", borderRadius: "50%", background: MOOD_STATES[mood]?.bg,
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px",
                    border: "2px solid rgba(255,255,255,0.6)",
                  }}>{MOOD_STATES[mood]?.emoji}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#5B4A6F" }}>{dollName}</div>
                    <div style={{ fontSize: "10px", color: "#A89BBE" }}>Lv.{level} · {totalInteractions} 次互动</div>
                    {unlockedTraits.length > 0 && (
                      <div style={{ marginTop: "4px", display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        {unlockedTraits.map(t => (
                          <span key={t.name} style={{ fontSize: "9px", background: `${t.color}20`, color: t.color, padding: "1px 6px", borderRadius: "4px", fontWeight: "700" }}>{t.rarity} {t.name}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                  <button style={{
                    flex: 1, padding: "10px", borderRadius: "12px", border: "none",
                    background: "linear-gradient(135deg, #FBBF24, #F59E0B)",
                    color: "white", fontSize: "12px", fontWeight: "700", cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(251,191,36,0.3)",
                  }}>🏷️ 上架出售</button>
                  <button style={{
                    flex: 1, padding: "10px", borderRadius: "12px",
                    border: "1px solid rgba(200,180,220,0.3)", background: "rgba(255,255,255,0.6)",
                    color: "#5B4A6F", fontSize: "12px", fontWeight: "600", cursor: "pointer",
                  }}>📤 转移</button>
                </div>
              </div>

              <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "10px" }}>🔥 热门 Agent</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "12px" }}>
                <MarketCard name="月影" level={12} price="0.85" traits={[{ name: "哲学家", rarity: "SSR", color: "#9370DB" }]} />
                <MarketCard name="小火" level={8} price="0.42" traits={[{ name: "冒险家", rarity: "SR", color: "#FF4500" }]} />
                <MarketCard name="棉花糖" level={15} price="1.2" traits={[{ name: "星光体质", rarity: "SSR", color: "#FFD700" }, { name: "治愈之心", rarity: "SR", color: "#FF69B4" }]} />
                <MarketCard name="小蓝" level={5} price="0.18" traits={[]} />
              </div>

              <div style={{ background: "rgba(255,255,255,0.5)", borderRadius: "16px", padding: "16px", border: "1px solid rgba(200,180,220,0.15)" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#5B4A6F", marginBottom: "8px" }}>📈 市场统计</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  {[
                    { label: "总 Agent 数", value: "12,847" },
                    { label: "24h 交易量", value: "234 BNB" },
                    { label: "地板价", value: "0.08 BNB" },
                    { label: "SSR 占比", value: "3.2%" },
                  ].map(item => (
                    <div key={item.label} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: "15px", fontWeight: "800", color: "#5B4A6F" }}>{item.value}</div>
                      <div style={{ fontSize: "10px", color: "#A89BBE" }}>{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
