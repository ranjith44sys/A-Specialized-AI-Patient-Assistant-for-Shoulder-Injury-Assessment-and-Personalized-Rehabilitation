import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import ShoulderModelViewer from "./ShoulderModel";

const LANGUAGES = {
  EN: {
    label: "EN",
    name: "English",
    placeholder: "Describe your pain or symptoms…",
    send: "Send",
    typing: "Analyzing your condition",
    greeting: "Hello! I'm your AI Shoulder Assistant.",
    greetingSub: "Tell me about your shoulder pain or discomfort, and I'll provide personalized guidance.",
    chips: ["Rotator cuff pain", "Frozen shoulder", "Clicking sound", "Pain at night"],
    sections: {
      what: "What's happening?",
      do: "What you should do",
      avoid: "What to avoid",
      doctor: "When to see a doctor",
    },
    copy: "Copy",
    copied: "Copied!",
    new: "New Chat",
    history: "Chat History",
    dark: "Dark mode",
  },
  TA: {
    label: "தமிழ்",
    name: "Tamil",
    placeholder: "உங்கள் வலி அல்லது அறிகுறிகளை விவரிக்கவும்…",
    send: "அனுப்பு",
    typing: "உங்கள் நிலையை ஆய்வு செய்கிறோம்",
    greeting: "வணக்கம்! நான் உங்கள் AI தோள்பட்டை உதவியாளர்.",
    greetingSub: "உங்கள் தோள்பட்டை வலி அல்லது அசௌகரியம் பற்றி சொல்லுங்கள்.",
    chips: ["சுழலும் தசை வலி", "உறைந்த தோள்", "சத்தம் வருகிறது", "இரவு வலி"],
    sections: {
      what: "என்ன நடக்கிறது?",
      do: "நீங்கள் செய்ய வேண்டியவை",
      avoid: "தவிர்க்க வேண்டியவை",
      doctor: "மருத்துவரை எப்போது சந்திக்கணும்?",
    },
    copy: "நகலெடு",
    copied: "நகலெடுக்கப்பட்டது!",
    new: "புதிய அரட்டை",
    history: "அரட்டை வரலாறு",
    dark: "இருண்ட பயன்முறை",
  },
  HI: {
    label: "हिन्दी",
    name: "Hindi",
    placeholder: "अपने दर्द या लक्षण बताएं…",
    send: "भेजें",
    typing: "आपकी स्थिति का विश्लेषण कर रहे हैं",
    greeting: "नमस्ते! मैं आपका AI शोल्डर असिस्टेंट हूँ।",
    greetingSub: "अपने कंधे के दर्द या परेशानी के बारे में बताएं।",
    chips: ["रोटेटर कफ दर्द", "जमा हुआ कंधा", "क्लिक की आवाज़", "रात में दर्द"],
    sections: {
      what: "क्या हो रहा है?",
      do: "आपको क्या करना चाहिए",
      avoid: "क्या避किया जाए",
      doctor: "डॉक्टर से कब मिलें?",
    },
    copy: "कॉपी करें",
    copied: "कॉपी हो गया!",
    new: "नई चैट",
    history: "चैट इतिहास",
    dark: "डार्क मोड",
  },
};

const MOCK_RESPONSES = [
  {
    what: "Based on your description, you may be experiencing rotator cuff tendinitis — inflammation of the tendons that connect the muscles around your shoulder joint. This is very common and often caused by repetitive overhead movements or sudden strain.",
    do: ["Apply ice for 15–20 minutes every 2–3 hours for the first 48 hours", "Rest your shoulder and avoid activities that worsen the pain", "Take over-the-counter anti-inflammatory medication if needed (consult a pharmacist)", "Gently perform pendulum exercises to maintain mobility"],
    avoid: ["Avoid overhead lifting or reaching until pain improves", "Don't sleep on the affected shoulder", "Avoid activities that cause sharp or worsening pain", "Don't apply heat in the first 48 hours after injury"],
    doctor: ["Pain is severe or does not improve after 1–2 weeks of rest", "You hear or feel a 'pop' in your shoulder", "Significant swelling, bruising, or deformity appears", "You lose the ability to lift your arm or move it normally"],
    followUp: ["What exercises can I do?", "How long will recovery take?", "Can this become permanent?"],
  },
  {
    what: "Your symptoms suggest possible adhesive capsulitis, commonly known as 'frozen shoulder.' This condition causes the capsule surrounding the shoulder joint to become inflamed and thickened, leading to stiffness and reduced range of motion. It typically progresses through freezing, frozen, and thawing stages.",
    do: ["Perform gentle range-of-motion exercises daily", "Apply warm compresses before exercise to loosen the joint", "Consider physiotherapy — it's the most effective treatment", "Maintain activity as tolerated; complete rest can worsen stiffness"],
    avoid: ["Avoid forcing your shoulder into painful positions", "Don't stop moving it entirely — gentle movement is key", "Avoid high-impact activities like throwing or heavy lifting", "Don't ignore the condition; early treatment leads to better outcomes"],
    doctor: ["Pain is severe and uncontrolled with medication", "No improvement after 6 weeks of conservative treatment", "Symptoms appear after a fall or trauma", "You develop numbness or tingling down your arm"],
    followUp: ["How long does frozen shoulder last?", "Will I need surgery?", "What's the best sleeping position?"],
  },
];

let msgCount = 0;

export default function App() {
  const [lang, setLang] = useState("EN");
  const [dark, setDark] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [visibleSections, setVisibleSections] = useState({});
  const [image, setImage] = useState(null);
  const [show3D, setShow3D] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [history] = useState([
    { id: 1, title: "Rotator cuff inquiry", date: "Apr 3" },
    { id: 2, title: "Shoulder clicking sound", date: "Apr 1" },
    { id: 3, title: "Post-surgery recovery", date: "Mar 28" },
  ]);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const t = LANGUAGES[lang];

  useEffect(() => {
    document.documentElement.style.setProperty("--is-dark", dark ? "1" : "0");
  }, [dark]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const parseResponse = (rawText) => {
    if (!rawText) return { what: "", do: [], avoid: [], doctor: [] };
    const sections = { what: "", do: [], avoid: [], doctor: [] };
    const patterns = [
      { key: "what", markers: ["1.", "What is happening", "என்ன நடக்கிறது", "क्या हो रहा"] },
      { key: "do", markers: ["2.", "What you should do", "என்ன செய்ய வேண்டியவை", "நீங்கள் செய்ய வேண்டியவை", "आपको क्या करना"] },
      { key: "avoid", markers: ["3.", "What to avoid", "தவிர்க்க வேண்டியவை", "क्या न करें"] },
      { key: "doctor", markers: ["4.", "When to see a doctor", "மருத்துவரை எப்போது", "மருத்துவரை எப்போது சந்திக்கணும்", "डॉक्टर से कब"] },
    ];
    const lines = rawText.split("\n").map((l) => l.trim()).filter(Boolean);
    let currentKey = null;
    let buffer = [];
    for (const line of lines) {
      let matched = false;
      for (const { key, markers } of patterns) {
        if (markers.some((m) => line.includes(m))) {
          if (currentKey) {
            if (currentKey === "what") sections[currentKey] = buffer.join(" ");
            else sections[currentKey] = buffer.map(b => b.replace(/^[-•*]\s*/, ""));
          }
          currentKey = key;
          buffer = [];
          matched = true;
          break;
        }
      }
      if (!matched && currentKey) buffer.push(line);
    }
    if (currentKey) {
      if (currentKey === "what") sections[currentKey] = buffer.join(" ");
      else sections[currentKey] = buffer.map(b => b.replace(/^[-•*]\s*/, ""));
    }
    if (!sections.what && buffer.length) sections.what = buffer.join(" ");
    return sections;
  };

  const revealSections = useCallback((msgId) => {
    const keys = ["what", "do", "avoid", "doctor"];
    keys.forEach((key, i) => {
      setTimeout(() => {
        setVisibleSections((prev) => ({
          ...prev,
          [`${msgId}-${key}`]: true,
        }));
      }, i * 400);
    });
  }, []);

  const sendMessage = useCallback(
    async (text, explicitRegion = null) => {
      const activeRegion = explicitRegion || selectedRegion;
      const typeofText = typeof text === "string" ? text : "";
      const trimmed = (typeofText || input).trim();
      if ((!trimmed && !image && !activeRegion) || typing) return;
      setInput("");

      const userMsgText = activeRegion 
        ? `📍 [Pain Location: ${activeRegion.label}]` 
        : (trimmed || (image ? "Uploaded an image" : ""));
      
      const userMsg = { id: ++msgCount, role: "user", text: userMsgText, hasImage: !!image };
      setMessages((prev) => [...prev, userMsg]);
      setTyping(true);

      try {
        let responseData;
        if (image) {
          const formData = new FormData();
          formData.append("input", trimmed);
          formData.append("language", lang.toLowerCase());
          formData.append("image", image);
          if (activeRegion) {
            formData.append("pain_location", activeRegion.label);
          }
          const { data } = await axios.post("/analyze", formData, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          responseData = data;
        } else {
          const payload = {
            input: trimmed,
            language: lang.toLowerCase(),
          };
          if (activeRegion) {
            payload.pain_location = activeRegion.label;
          }
          const { data } = await axios.post("/analyze", payload);
          responseData = data;
        }
        
        setImage(null);
        setSelectedRegion(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        
        const data = responseData;

        // Auto-update the UI language toggle if the server detected users typing in another language
        if (data.language && data.language.toUpperCase() !== lang) {
          setLang(data.language.toUpperCase());
        }

        if (data.follow_up_questions && data.follow_up_questions.length > 0) {
          const defaultIntakeMsgs = {
            EN: "I am currently analyzing your symptoms. To provide a precise clinical assessment, I need a few more details:\n\n",
            TA: "உங்கள் அறிகுறிகளை நான் ஆய்வு செய்கிறேன். துல்லியமான மருத்துவ மதிப்பீட்டை வழங்க, எனக்கு இன்னும் சில விவரங்கள் தேவை:\n\n",
            HI: "मैं आपके लक्षणों का विश्लेषण कर रहा हूँ। सटीक नैदानिक मूल्यांकन प्रदान करने के लिए, मुझे कुछ और विवरण चाहिए:\n\n"
          };
          
          const followUpOnlyMsgs = {
            EN: "To provide a precise clinical assessment, I need a few more details:\n\n",
            TA: "துல்லியமான மருத்துவ மதிப்பீட்டை வழங்க, எனக்கு இன்னும் சில விவரங்கள் தேவை:\n\n",
            HI: "सटीक नैदानिक मूल्यांकन प्रदान करने के लिए, मुझे कुछ और विवरण चाहिए:\n\n"
          };

          const locationMsgs = {
            EN: `I've noted the location of your pain as ${data.pain_location}. `,
            TA: `${data.pain_location} பகுதியில் நீங்கள் வலி இருப்பதாகத் தெரிவித்துள்ளீர்கள். `,
            HI: `मैंने आपके दर्द के स्थान को ${data.pain_location} के रूप में नोट किया है। `
          };

          let intro = "";
          let prefix = "";
          if (data.image_description) prefix += `🔍 ${data.image_description}\n\n`;
          if (data.pain_location) prefix += locationMsgs[lang] || locationMsgs.EN;
          
          if (prefix) {
            intro = prefix + (followUpOnlyMsgs[lang] || followUpOnlyMsgs.EN);
          } else {
            intro = defaultIntakeMsgs[lang] || defaultIntakeMsgs.EN;
          }

          const questionsText = data.follow_up_questions.map((q) => `• ${q}`).join("\n");

          const aiMsg = {
            id: ++msgCount,
            role: "ai",
            type: "intake",
            text: intro + questionsText,
            followUp: data.follow_up_questions,
          };
          setTyping(false);
          setMessages((prev) => [...prev, aiMsg]);
        } else if (data.response) {
          const parsed = parseResponse(data.response);
          const aiMsg = {
            id: ++msgCount,
            role: "ai",
            type: "final",
            ...parsed,
            followUp: [],
          };
          setTyping(false);
          setMessages((prev) => [...prev, aiMsg]);
          setTimeout(() => revealSections(aiMsg.id), 100);
        }
      } catch (err) {
        const aiMsg = {
          id: ++msgCount,
          role: "ai",
          what: "Connection error. Please try again later.",
          do: [], avoid: [], doctor: [], followUp: [],
        };
        setTyping(false);
        setMessages((prev) => [...prev, aiMsg]);
        setTimeout(() => revealSections(aiMsg.id), 100);
      }
    },
    [input, revealSections, lang, typing, image, selectedRegion]
  );

  const copyText = (msg, id) => {
    const text = [
      `What's happening: ${msg.what}`,
      `Do: ${msg.do?.join(", ")}`,
      `Avoid: ${msg.avoid?.join(", ")}`,
      `See a doctor if: ${msg.doctor?.join(", ")}`,
    ].join("\n\n");
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const bg = dark
    ? { app: "#0d1117", sidebar: "#161b22", header: "#161b22eb", chat: "#0d1117", inputArea: "#161b22", card: "#1c2130", cardBorder: "#2d3548", text: "#e6edf3", textSub: "#8b949e", bubble: "#1c2130", bubbleUser: "#1d4ed8", accent: "#60a5fa", green: "#22c55e", yellow: "#f59e0b", red: "#ef4444", chip: "#1e293b", chipText: "#94a3b8" }
    : { app: "#f8fafc", sidebar: "#ffffff", header: "#ffffffeb", chat: "#f8fafc", inputArea: "#ffffff", card: "#ffffff", cardBorder: "#e2e8f0", text: "#0f172a", textSub: "#64748b", bubble: "#ffffff", bubbleUser: "#2563eb", accent: "#2563eb", green: "#16a34a", yellow: "#d97706", red: "#dc2626", chip: "#f1f5f9", chipText: "#475569" };

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', 'Noto Sans', system-ui, sans-serif", background: bg.app, minHeight: "100vh", display: "flex", flexDirection: "column", color: bg.text, transition: "background 0.3s, color 0.3s" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #94a3b820; border-radius: 2px; }
        .fade-in { animation: fadeSlideUp 0.45s cubic-bezier(0.34,1.3,0.64,1) forwards; opacity: 0; }
        @keyframes fadeSlideUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
        .card-hover { transition: transform 0.18s ease, box-shadow 0.18s ease; }
        .card-hover:hover { transform: translateY(-2px); }
        .btn-hover { transition: all 0.15s ease; }
        .btn-hover:hover { opacity: 0.85; transform: scale(1.03); }
        .btn-hover:active { transform: scale(0.97); }
        .chip-btn { transition: all 0.15s ease; cursor: pointer; }
        .chip-btn:hover { transform: translateY(-1px); opacity: 0.85; }
        .typing-dot { animation: typingPulse 1.4s ease-in-out infinite; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typingPulse { 0%,80%,100%{transform:scale(0.6);opacity:0.4} 40%{transform:scale(1);opacity:1} }
        .section-reveal { animation: sectionIn 0.5s cubic-bezier(0.34,1.2,0.64,1) forwards; opacity: 0; }
        @keyframes sectionIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
        .sidebar-overlay { position:fixed;inset:0;background:#00000060;z-index:30;backdrop-filter:blur(4px); }
        .sidebar { position:fixed;left:0;top:0;bottom:0;width:280px;z-index:40;overflow-y:auto;transition:transform 0.3s cubic-bezier(0.4,0,0.2,1); }
        .send-btn { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color:#fff; border:none; border-radius:12px; padding:0 20px; height:48px; font-size:15px; font-weight:600; cursor:pointer; display:flex;align-items:center;gap:8px;white-space:nowrap; }
        .send-btn:hover { background: linear-gradient(135deg,#3b82f6 0%,#2563eb 100%); transform:scale(1.02); }
        .send-btn:active { transform:scale(0.98); }
        input[type=text], textarea { outline:none; }
        .lang-btn { border-radius:8px; padding:5px 10px; font-size:13px; font-weight:500; cursor:pointer; transition:all 0.15s; border:1.5px solid transparent; }
      `}</style>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div
        className="sidebar"
        style={{
          background: bg.sidebar,
          borderRight: `1px solid ${bg.cardBorder}`,
          transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)",
          padding: "24px 0",
          boxShadow: sidebarOpen ? "4px 0 32px #00000020" : "none",
        }}
      >
        <div style={{ padding: "0 20px 20px", borderBottom: `1px solid ${bg.cardBorder}` }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: bg.text }}>{t.history}</span>
            <button onClick={() => setSidebarOpen(false)} style={{ background: "none", border: "none", color: bg.textSub, cursor: "pointer", fontSize: 20, lineHeight: 1 }}>✕</button>
          </div>
          <button
            className="btn-hover"
            style={{ width: "100%", background: bg.accent, color: "#fff", border: "none", borderRadius: 10, padding: "10px 16px", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
            onClick={() => { setMessages([]); setSidebarOpen(false); }}
          >
            <span>＋</span> {t.new}
          </button>
        </div>
        <div style={{ padding: "12px 12px 0" }}>
          {history.map((h) => (
            <div
              key={h.id}
              className="chip-btn"
              style={{ padding: "10px 12px", borderRadius: 8, marginBottom: 4, display: "flex", justifyContent: "space-between", alignItems: "center" }}
              onClick={() => setSidebarOpen(false)}
            >
              <span style={{ fontSize: 13, fontWeight: 500, color: bg.text, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.title}</span>
              <span style={{ fontSize: 11, color: bg.textSub, marginLeft: 8 }}>{h.date}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Header */}
      <header style={{ position: "sticky", top: 0, zIndex: 20, background: bg.header, backdropFilter: "blur(16px)", borderBottom: `1px solid ${bg.cardBorder}`, padding: "0 20px", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between", transition: "background 0.3s" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => setSidebarOpen(true)} style={{ background: "none", border: "none", color: bg.textSub, cursor: "pointer", fontSize: 20, padding: 6, borderRadius: 8, display: "flex" }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><line x1="2" y1="5" x2="16" y2="5" stroke={bg.textSub} strokeWidth="1.4" strokeLinecap="round"/><line x1="2" y1="9" x2="16" y2="9" stroke={bg.textSub} strokeWidth="1.4" strokeLinecap="round"/><line x1="2" y1="13" x2="16" y2="13" stroke={bg.textSub} strokeWidth="1.4" strokeLinecap="round"/></svg>
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
            {/* Unique elegant logo mark */}
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Outer thin ring */}
              <circle cx="18" cy="18" r="17" stroke="url(#hg)" strokeWidth="0.8" fill="none" opacity="0.6"/>
              {/* Inner filled circle */}
              <circle cx="18" cy="18" r="12" fill="url(#hg)" opacity="0.12"/>
              {/* Abstract shoulder arc — elegant upward curve */}
              <path d="M10 24 Q12 13 18 11 Q24 13 26 24" stroke="url(#hg)" strokeWidth="1.6" strokeLinecap="round" fill="none"/>
              {/* Spine line — vertical centerline */}
              <line x1="18" y1="11" x2="18" y2="26" stroke="url(#hg2)" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
              {/* Left joint dot */}
              <circle cx="10" cy="24" r="1.8" fill="#60a5fa"/>
              {/* Right joint dot */}
              <circle cx="26" cy="24" r="1.8" fill="#06b6d4"/>
              {/* Crown / AI spark — top center */}
              <circle cx="18" cy="8" r="1.4" fill="url(#hg)"/>
              <line x1="18" y1="4" x2="18" y2="6.5" stroke="#60a5fa" strokeWidth="1" strokeLinecap="round" opacity="0.7"/>
              <line x1="14.5" y1="5.2" x2="15.8" y2="7.2" stroke="#60a5fa" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
              <line x1="21.5" y1="5.2" x2="20.2" y2="7.2" stroke="#60a5fa" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
              <defs>
                <linearGradient id="hg" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#2563eb"/>
                  <stop offset="100%" stopColor="#06b6d4"/>
                </linearGradient>
                <linearGradient id="hg2" x1="0" y1="0" x2="0" y2="36" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.8"/>
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.2"/>
                </linearGradient>
              </defs>
            </svg>
            {/* Wordmark */}
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
                <span style={{ fontSize: 15, fontWeight: 700, background: "linear-gradient(90deg,#2563eb,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "-0.3px" }}>AI</span>
                <span style={{ fontSize: 15, fontWeight: 300, color: bg.textSub, letterSpacing: "-0.1px" }}>Shoulder</span>
                <span style={{ fontSize: 15, fontWeight: 300, color: bg.textSub, letterSpacing: "-0.1px" }}>Assistant</span>
              </div>
              <div style={{ fontSize: 10, color: bg.textSub, fontWeight: 400, letterSpacing: "0.5px", marginTop: 3, textTransform: "uppercase", opacity: 0.6 }}>Personalized Pain Guidance</div>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {Object.entries(LANGUAGES).map(([code, l]) => (
            <button
              key={code}
              className="lang-btn"
              style={{
                background: lang === code ? (dark ? "#1e3a5f" : "#eff6ff") : "transparent",
                color: lang === code ? bg.accent : bg.textSub,
                borderColor: lang === code ? bg.accent : "transparent",
              }}
              onClick={() => setLang(code)}
            >
              {l.label}
            </button>
          ))}
          <button
            className="btn-hover"
            onClick={() => setDark(!dark)}
            style={{ background: "none", border: `1.5px solid ${bg.cardBorder}`, borderRadius: 8, padding: "5px 10px", fontSize: 16, cursor: "pointer", color: bg.textSub }}
            title={t.dark}
          >
            {dark ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3.5" stroke={bg.textSub} strokeWidth="1.2"/><line x1="8" y1="1" x2="8" y2="2.5" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="8" y1="13.5" x2="8" y2="15" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="1" y1="8" x2="2.5" y2="8" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="13.5" y1="8" x2="15" y2="8" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="3.1" y1="3.1" x2="4.2" y2="4.2" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="11.8" y1="11.8" x2="12.9" y2="12.9" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="11.8" y1="4.2" x2="12.9" y2="3.1" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/><line x1="3.1" y1="12.9" x2="4.2" y2="11.8" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/></svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.5 10A6 6 0 016 2.5a6 6 0 100 11 6 6 0 007.5-3.5z" stroke={bg.textSub} strokeWidth="1.2" strokeLinejoin="round" fill="none"/></svg>
              )}
          </button>
        </div>
      </header>

      {/* Chat Area */}
      <main style={{ flex: 1, overflowY: "auto", padding: "24px 16px", maxWidth: 780, width: "100%", margin: "0 auto" }}>

        {/* Empty State */}
        {messages.length === 0 && !typing && (
          <div className="fade-in" style={{ textAlign: "center", padding: "60px 20px 40px" }}>
            <div style={{ margin: "0 auto 28px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="100" height="100" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="17" stroke="url(#cg)" strokeWidth="0.6" fill="none" opacity="0.4"/>
                <circle cx="18" cy="18" r="13" stroke="url(#cg)" strokeWidth="0.4" fill="none" opacity="0.25"/>
                <circle cx="18" cy="18" r="12" fill="url(#cg)" opacity="0.08"/>
                <path d="M10 24 Q12 13 18 11 Q24 13 26 24" stroke="url(#cg)" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
                <line x1="18" y1="11" x2="18" y2="27" stroke="url(#cg2)" strokeWidth="1.1" strokeLinecap="round" opacity="0.4"/>
                <circle cx="10" cy="24" r="2.2" fill="#2563eb"/>
                <circle cx="26" cy="24" r="2.2" fill="#06b6d4"/>
                <circle cx="18" cy="8" r="1.6" fill="url(#cg)"/>
                <line x1="18" y1="3.5" x2="18" y2="6.3" stroke="#60a5fa" strokeWidth="1.1" strokeLinecap="round" opacity="0.8"/>
                <line x1="14" y1="4.8" x2="15.5" y2="7" stroke="#60a5fa" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
                <line x1="22" y1="4.8" x2="20.5" y2="7" stroke="#60a5fa" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
                <defs>
                  <linearGradient id="cg" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#2563eb"/>
                    <stop offset="100%" stopColor="#06b6d4"/>
                  </linearGradient>
                  <linearGradient id="cg2" x1="0" y1="0" x2="0" y2="36" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.9"/>
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.1"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: bg.text, marginBottom: 10 }}>{t.greeting}</h2>
            <p style={{ fontSize: 15, color: bg.textSub, marginBottom: 36, maxWidth: 400, margin: "0 auto 36px", lineHeight: 1.6 }}>{t.greetingSub}</p>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, idx) => (
          <div key={msg.id} className="fade-in" style={{ marginBottom: 20, display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            {msg.role === "user" ? (
              <div style={{ maxWidth: "75%", background: bg.bubbleUser, color: "#fff", borderRadius: "18px 18px 4px 18px", padding: "12px 18px", fontSize: 15, fontWeight: 500, lineHeight: 1.5, boxShadow: "0 2px 12px #2563eb30" }}>
                {msg.text}
              </div>
            ) : (
              <div style={{ width: "100%", maxWidth: 720 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                  <div style={{ width: 30, height: 30, borderRadius: 8, background: dark ? "#0f172a" : "#f0f7ff", border: `1px solid ${dark ? "#1e3a5f" : "#bfdbfe"}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <svg width="18" height="18" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M10 24 Q12 13 18 11 Q24 13 26 24" stroke="url(#mg)" strokeWidth="2" strokeLinecap="round" fill="none"/>
                      <circle cx="10" cy="24" r="2.2" fill="#2563eb"/>
                      <circle cx="26" cy="24" r="2.2" fill="#06b6d4"/>
                      <circle cx="18" cy="8" r="1.8" fill="url(#mg)"/>
                      <line x1="18" y1="4" x2="18" y2="6.1" stroke="#60a5fa" strokeWidth="1.2" strokeLinecap="round"/>
                      <defs>
                        <linearGradient id="mg" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                          <stop offset="0%" stopColor="#2563eb"/>
                          <stop offset="100%" stopColor="#06b6d4"/>
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: bg.accent }}>AI Shoulder Assistant</span>
                </div>

                {msg.type === "intake" ? (
                  <>
                    <div className="fade-in" style={{ maxWidth: "85%", background: bg.card, color: bg.text, border: `1.5px solid ${bg.cardBorder}`, borderRadius: "18px 18px 18px 4px", padding: "16px 20px", fontSize: 14, lineHeight: 1.6, boxShadow: "0 4px 12px #00000008", whiteSpace: "pre-wrap" }}>
                      {msg.text}
                    </div>
                  </>
                ) : (
                  <>
                {/* Response Cards Grid */}
                <div style={{ display: "grid", gap: 12 }}>
                  {/* What's happening */}
                  {visibleSections[`${msg.id}-what`] && (
                    <div className="section-reveal card-hover" style={{ background: dark ? "#1e2d4a" : "#eff6ff", border: `1.5px solid ${dark ? "#2d4a7a" : "#bfdbfe"}`, borderRadius: 16, padding: "18px 20px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" stroke={dark ? "#93c5fd" : "#2563eb"} strokeWidth="1.2" fill="none"/><circle cx="10" cy="10" r="3" fill={dark ? "#93c5fd" : "#2563eb"} opacity="0.7"/><line x1="10" y1="1" x2="10" y2="4" stroke={dark ? "#93c5fd" : "#2563eb"} strokeWidth="1.2" strokeLinecap="round"/><line x1="10" y1="16" x2="10" y2="19" stroke={dark ? "#93c5fd" : "#2563eb"} strokeWidth="1.2" strokeLinecap="round"/><line x1="1" y1="10" x2="4" y2="10" stroke={dark ? "#93c5fd" : "#2563eb"} strokeWidth="1.2" strokeLinecap="round"/><line x1="16" y1="10" x2="19" y2="10" stroke={dark ? "#93c5fd" : "#2563eb"} strokeWidth="1.2" strokeLinecap="round"/></svg>
                        <span style={{ fontSize: 14, fontWeight: 700, color: dark ? "#93c5fd" : "#1d4ed8" }}>{t.sections.what}</span>
                      </div>
                      <p style={{ fontSize: 14, lineHeight: 1.7, color: bg.text }}>{msg.what}</p>
                    </div>
                  )}

                  {/* Do & Avoid side by side on wide screens */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    {visibleSections[`${msg.id}-do`] && (
                      <div className="section-reveal card-hover" style={{ background: dark ? "#14291f" : "#f0fdf4", border: `1.5px solid ${dark ? "#1a4730" : "#bbf7d0"}`, borderRadius: 16, padding: "18px 20px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" stroke={dark ? "#4ade80" : "#16a34a"} strokeWidth="1.2" fill="none"/><path d="M6 10.5l3 3 5-5.5" stroke={dark ? "#4ade80" : "#16a34a"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                          <span style={{ fontSize: 14, fontWeight: 700, color: dark ? "#4ade80" : "#15803d" }}>{t.sections.do}</span>
                        </div>
                        <ul style={{ paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                          {msg.do?.map((item, i) => (
                            <li key={i} style={{ fontSize: 13, lineHeight: 1.5, color: bg.text, display: "flex", gap: 8, alignItems: "flex-start" }}>
                              <span style={{ color: bg.green, marginTop: 2, flexShrink: 0, fontSize: 12 }}>▶</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {visibleSections[`${msg.id}-avoid`] && (
                      <div className="section-reveal card-hover" style={{ background: dark ? "#2a1f0f" : "#fffbeb", border: `1.5px solid ${dark ? "#5a3a0f" : "#fde68a"}`, borderRadius: 16, padding: "18px 20px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 2L18.5 17H1.5L10 2Z" stroke={dark ? "#fbbf24" : "#b45309"} strokeWidth="1.2" fill="none" strokeLinejoin="round"/><line x1="10" y1="8" x2="10" y2="12" stroke={dark ? "#fbbf24" : "#b45309"} strokeWidth="1.5" strokeLinecap="round"/><circle cx="10" cy="14.5" r="0.8" fill={dark ? "#fbbf24" : "#b45309"}/></svg>
                          <span style={{ fontSize: 14, fontWeight: 700, color: dark ? "#fbbf24" : "#b45309" }}>{t.sections.avoid}</span>
                        </div>
                        <ul style={{ paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                          {msg.avoid?.map((item, i) => (
                            <li key={i} style={{ fontSize: 13, lineHeight: 1.5, color: bg.text, display: "flex", gap: 8, alignItems: "flex-start" }}>
                              <span style={{ color: bg.yellow, marginTop: 2, flexShrink: 0, fontSize: 12 }}>▶</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Doctor card */}
                  {visibleSections[`${msg.id}-doctor`] && (
                    <div className="section-reveal card-hover" style={{ background: dark ? "#2a1212" : "#fff1f2", border: `1.5px solid ${dark ? "#6b2020" : "#fecaca"}`, borderRadius: 16, padding: "18px 20px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" stroke={dark ? "#f87171" : "#b91c1c"} strokeWidth="1.2" fill="none"/><line x1="10" y1="5.5" x2="10" y2="14.5" stroke={dark ? "#f87171" : "#b91c1c"} strokeWidth="1.6" strokeLinecap="round"/><line x1="5.5" y1="10" x2="14.5" y2="10" stroke={dark ? "#f87171" : "#b91c1c"} strokeWidth="1.6" strokeLinecap="round"/></svg>
                        <span style={{ fontSize: 14, fontWeight: 700, color: dark ? "#f87171" : "#b91c1c" }}>{t.sections.doctor}</span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
                        {msg.doctor?.map((item, i) => (
                          <div key={i} style={{ fontSize: 13, lineHeight: 1.5, color: bg.text, display: "flex", gap: 8, alignItems: "flex-start", background: dark ? "#3a1a1a" : "#fff5f5", borderRadius: 8, padding: "8px 10px" }}>
                            <span style={{ color: bg.red, flexShrink: 0, fontSize: 14 }}>●</span>
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions row */}
                {visibleSections[`${msg.id}-doctor`] && (
                  <div className="section-reveal" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 14, flexWrap: "wrap", gap: 10 }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                      {msg.followUp?.map((q) => (
                        <button
                          key={q}
                          className="chip-btn"
                          style={{ background: bg.chip, color: bg.chipText, border: `1.5px solid ${bg.cardBorder}`, borderRadius: 20, padding: "7px 14px", fontSize: 12, fontWeight: 500, cursor: "pointer" }}
                          onClick={() => sendMessage(q)}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                    <button
                      className="btn-hover"
                      onClick={() => copyText(msg, msg.id)}
                      style={{ background: "none", border: `1.5px solid ${bg.cardBorder}`, borderRadius: 8, padding: "6px 14px", fontSize: 12, color: copiedId === msg.id ? bg.green : bg.textSub, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontWeight: 500 }}
                    >
                      {copiedId === msg.id ? "✓" : "⧉"} {copiedId === msg.id ? t.copied : t.copy}
                    </button>
                  </div>
                )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {typing && (
          <div className="fade-in" style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: dark ? "#0f172a" : "#f0f7ff", border: `1px solid ${dark ? "#1e3a5f" : "#bfdbfe"}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <svg width="18" height="18" viewBox="0 0 36 36" fill="none"><path d="M10 24 Q12 13 18 11 Q24 13 26 24" stroke="url(#tg)" strokeWidth="2" strokeLinecap="round" fill="none"/><circle cx="10" cy="24" r="2.2" fill="#2563eb"/><circle cx="26" cy="24" r="2.2" fill="#06b6d4"/><circle cx="18" cy="8" r="1.8" fill="url(#tg)"/><line x1="18" y1="4" x2="18" y2="6.1" stroke="#60a5fa" strokeWidth="1.2" strokeLinecap="round"/><defs><linearGradient id="tg" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#2563eb"/><stop offset="100%" stopColor="#06b6d4"/></linearGradient></defs></svg>
                  </div>
            <div style={{ background: bg.card, border: `1px solid ${bg.cardBorder}`, borderRadius: "14px 14px 14px 4px", padding: "12px 18px", display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="typing-dot" style={{ width: 7, height: 7, borderRadius: "50%", background: bg.accent, animationDelay: `${i * 0.2}s` }} />
                ))}
              </div>
              <span style={{ fontSize: 13, color: bg.textSub, fontStyle: "italic" }}>{t.typing}…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Input Area */}
      <div style={{ position: "sticky", bottom: 0, background: bg.inputArea, borderTop: `1px solid ${bg.cardBorder}`, padding: "14px 16px", backdropFilter: "blur(16px)", transition: "background 0.3s" }}>
        <div style={{ maxWidth: 780, margin: "0 auto", display: "flex", flexDirection: "column", gap: 8 }}>
          {image && (
            <div style={{display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: dark ? "#1e293b" : "#f1f5f9", borderRadius: 8, width: "fit-content", border: `1px solid ${bg.cardBorder}`}}>
              <span style={{fontSize: 12, color: bg.text, fontWeight: 500}}>📷 {image.name}</span>
              <button className="btn-hover" onClick={() => setImage(null)} style={{background: "none", border: "none", cursor: "pointer", color: bg.red, fontWeight: "bold", marginLeft: 8}}>✕</button>
            </div>
          )}
          {selectedRegion && (
            <div style={{display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: dark ? "#1e3a5f" : "#eff6ff", borderRadius: 8, width: "fit-content", border: `1px solid ${bg.accent}`}}>
              <span style={{fontSize: 12, color: bg.text, fontWeight: 500}}>📍 {selectedRegion.label}</span>
              <button className="btn-hover" onClick={() => setSelectedRegion(null)} style={{background: "none", border: "none", cursor: "pointer", color: bg.accent, fontWeight: "bold", marginLeft: 8}}>✕</button>
            </div>
          )}
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end", width: "100%" }}>
            <div style={{ flex: 1, background: dark ? "#0d1117" : "#f8fafc", border: `1.5px solid ${bg.cardBorder}`, borderRadius: 16, padding: "12px 16px", display: "flex", alignItems: "center", transition: "border-color 0.2s", boxShadow: "0 1px 4px #00000008" }}
              onFocus={(e) => e.currentTarget.style.borderColor = bg.accent}
              onBlur={(e) => e.currentTarget.style.borderColor = bg.cardBorder}
            >
              <input type="file" ref={fileInputRef} onChange={(e) => e.target.files && setImage(e.target.files[0])} accept="image/jpeg, image/png" style={{ display: 'none' }} />
              <button
                className="btn-hover"
                onClick={() => fileInputRef.current?.click()}
                style={{ background: "none", border: "none", color: bg.textSub, cursor: "pointer", padding: "0 8px 0 0", fontSize: 22, display: "flex", alignItems: "center", fontWeight: 300 }}
                title="Upload image"
                aria-label="Upload image"
              >
                +
              </button>
              <button
                className="btn-hover"
                onClick={() => setShow3D(true)}
                style={{ background: "none", border: "none", color: bg.accent, cursor: "pointer", padding: "0 8px 0 0", display: "flex", alignItems: "center" }}
                title="Select Region on 3D Model"
                aria-label="Open 3D Model"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                  <line x1="12" y1="22.08" x2="12" y2="12"></line>
                </svg>
              </button>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder={t.placeholder}
                aria-label={t.placeholder}
                style={{ flex: 1, background: "none", border: "none", fontSize: 15, color: bg.text, fontFamily: "inherit", outline: "none" }}
              />
            <button
              className="btn-hover"
              style={{ background: "none", border: "none", color: bg.textSub, cursor: "pointer", padding: "0 4px", display: "flex", alignItems: "center" }}
              title="Voice input (coming soon)"
              aria-label="Voice input"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" opacity="0.5"><rect x="6" y="1" width="6" height="10" rx="3" stroke={bg.textSub} strokeWidth="1.2" fill="none"/><path d="M3 9a6 6 0 0012 0" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round" fill="none"/><line x1="9" y1="15" x2="9" y2="17" stroke={bg.textSub} strokeWidth="1.2" strokeLinecap="round"/></svg>
            </button>
          </div>
          <button
            className="send-btn btn-hover"
            onClick={() => sendMessage()}
            disabled={(!input.trim() && !image && !selectedRegion) || typing}
            style={{ opacity: (!input.trim() && !image && !selectedRegion) || typing ? 0.5 : 1, cursor: (!input.trim() && !image && !selectedRegion) || typing ? "not-allowed" : "pointer" }}
            aria-label={t.send}
          >
            <span style={{ fontSize: 16 }}>↑</span>
            {t.send}
          </button>
        </div>
        </div>
        <p style={{ textAlign: "center", fontSize: 11, color: bg.textSub, marginTop: 8 }}>
          AI-generated guidance only. Always consult a healthcare professional for medical decisions.
        </p>
      </div>
      
      {/* 3D Model Modal */}
      {show3D && (
        <ShoulderModelViewer 
          onClose={() => setShow3D(false)} 
          onRegionSelected={(label, coords) => {
            setShow3D(false);
            sendMessage("", { label, coords });
          }} 
        />
      )}
    </div>
  );
}
