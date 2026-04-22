import { useState, useEffect, useRef } from 'react'

// ─── TYPES ────────────────────────────────────────────────────────────────────
interface User { id: string; name: string; email: string; role: string }
interface Lead {
  id: number; name: string; practice: string; city: string
  specialty: string; phone: string; score: number; status: string; source: string
}
interface Task {
  id: number; title: string; assignee: string; done: boolean; priority: string
}
interface ChatMsg { role: 'user' | 'ai' | 'system'; text: string }

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const TEAM = [
  { id: 'davide',       name: 'Davide Duranti', role: 'CEO / Strategy',        initials: 'DD', color: '#7b9aff', email: 'info@medwavegroup.com',         phone: '+27794272486' },
  { id: 'francois',    name: 'Francois',        role: 'COO',                   initials: 'FR', color: '#e8ff47', email: 'francois@medwavegroup.com',      phone: '' },
  { id: 'erich',       name: 'Erich',           role: 'MedWave Team',          initials: 'ER', color: '#47ffd4', email: 'erich@medwavegroup.com',         phone: '' },
  { id: 'sterrenberg', name: 'Sterrenberg',     role: 'MedWave Team',          initials: 'ST', color: '#ff9447', email: 'sterrenberg@medwavegroup.com',   phone: '' },
  { id: 'hazel',       name: 'Hazel',           role: 'Lead Scraper & Caller', initials: 'HZ', color: '#ff47c8', email: 'hazel@medwavegroup.com',         phone: '' },
  { id: 'azola',       name: 'Azola',           role: 'Lead Scraper & Caller', initials: 'AZ', color: '#47c8ff', email: 'azola@medwavegroup.com',         phone: '' },
]

const MOCK_LEADS: Lead[] = [
  { id: 1, name: 'Dr. Sarah Botha', practice: 'Cape Wellness Clinic', city: 'Cape Town', specialty: 'GP / Holistic', phone: '082 444 1122', score: 92, status: 'hot', source: 'Google Maps' },
  { id: 2, name: 'Dr. James Nkosi', practice: 'Joburg Sports Medicine', city: 'Sandton', specialty: 'Sports Medicine', phone: '011 234 5678', score: 78, status: 'warm', source: 'Google Maps' },
  { id: 3, name: 'Dr. Fatima Essop', practice: 'Natural Health Hub', city: 'Durban', specialty: 'Wellness / Naturopath', phone: '031 765 4321', score: 88, status: 'hot', source: 'Website' },
  { id: 4, name: 'Mpho Dlamini', practice: 'Ubuntu Physio', city: 'Pretoria', specialty: 'Physiotherapy', phone: '012 333 9900', score: 65, status: 'warm', source: 'Google Maps' },
  { id: 5, name: 'Dr. Lisa van Zyl', practice: 'Stellenbosch Integrative', city: 'Stellenbosch', specialty: 'Integrative Med', phone: '021 888 2211', score: 84, status: 'hot', source: 'Referral' },
  { id: 6, name: 'Dr. Pieter Swart', practice: 'East Rand Medical', city: 'Boksburg', specialty: 'GP', phone: '011 456 7890', score: 45, status: 'cold', source: 'Google Maps' },
]

const INIT_TASKS: Task[] = [
  { id: 1, title: 'Run OpenClaw scrape — 500 GP leads, Cape Town & Gauteng', assignee: 'davide', done: false, priority: 'high' },
  { id: 2, title: 'Review and qualify new lead batch from this week\'s scrape', assignee: 'erich', done: false, priority: 'medium' },
  { id: 3, title: 'Verify contact details for top 10 hot leads via LinkedIn & website', assignee: 'sterrenberg', done: false, priority: 'high' },
  { id: 4, title: 'Follow up with 3 hot leads from last week', assignee: 'davide', done: false, priority: 'high' },
]

// ─── STYLES ───────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0a0a0b;--surface:#111114;--surface2:#18181d;--border:#2a2a32;
    --accent:#e8ff47;--accent2:#47ffd4;--danger:#ff4747;--text:#e8e8f0;--muted:#6b6b7e;
    --ff:'Syne',sans-serif;--fm:'Space Mono',monospace;
  }
  html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--ff)}
  .app{min-height:100vh;display:grid;grid-template-rows:60px 1fr;grid-template-columns:240px 1fr;grid-template-areas:"hd hd""sb mn"}
  .hd{grid-area:hd;background:var(--surface);border-bottom:1px solid var(--border);padding:0 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
  .logo{font-size:17px;font-weight:800;letter-spacing:-.5px;display:flex;align-items:center;gap:9px}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 10px var(--accent);animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .hd-right{display:flex;align-items:center;gap:14px;font-family:var(--fm);font-size:11px;color:var(--muted)}
  .badge{padding:3px 10px;border-radius:20px;border:1px solid var(--accent);color:var(--accent);font-size:10px}
  .badge2{border-color:var(--accent2);color:var(--accent2)}
  .sb{grid-area:sb;background:var(--surface);border-right:1px solid var(--border);padding:20px 0;overflow-y:auto;position:sticky;top:60px;height:calc(100vh - 60px)}
  .mn{grid-area:mn;padding:28px 32px;overflow-y:auto;background:radial-gradient(ellipse at 80% 0%,rgba(232,255,71,.04) 0%,transparent 50%),radial-gradient(ellipse at 20% 100%,rgba(71,255,212,.03) 0%,transparent 50%),var(--bg)}
  .nav-lbl{font-family:var(--fm);font-size:9px;letter-spacing:2px;color:var(--muted);padding:0 20px;margin:16px 0 6px;text-transform:uppercase}
  .nav-it{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;font-size:13px;font-weight:600;color:var(--muted);transition:all .15s;border-left:2px solid transparent;margin:2px 0}
  .nav-it:hover{background:var(--surface2);color:var(--text)}
  .nav-it.on{background:var(--surface2);color:var(--accent);border-left-color:var(--accent)}
  .nbadge{margin-left:auto;background:var(--accent);color:var(--bg);font-family:var(--fm);font-size:9px;padding:2px 6px;border-radius:10px;font-weight:700}
  .nbadge2{background:var(--accent2);color:var(--bg)}
  .ph{margin-bottom:26px}
  .pt{font-size:26px;font-weight:800;letter-spacing:-1px}
  .ps{color:var(--muted);font-size:12px;margin-top:4px;font-family:var(--fm)}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px}
  .ct{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:14px;font-family:var(--fm)}
  .sg{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
  .sc{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 18px;position:relative;overflow:hidden}
  .sc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),transparent)}
  .sv{font-size:28px;font-weight:800;letter-spacing:-1px}
  .sl{font-family:var(--fm);font-size:10px;color:var(--muted);margin-top:3px}
  .sd{font-family:var(--fm);font-size:10px;color:var(--accent2);margin-top:5px}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:20px}
  .btn{padding:9px 18px;border-radius:8px;font-family:var(--ff);font-weight:700;font-size:12px;cursor:pointer;transition:all .15s;border:none;display:inline-flex;align-items:center;gap:7px}
  .btn-p{background:var(--accent);color:var(--bg)}.btn-p:hover{background:#f0ff6a;transform:translateY(-1px)}.btn-p:disabled{opacity:.5;cursor:not-allowed;transform:none}
  .btn-s{background:transparent;color:var(--text);border:1px solid var(--border)}.btn-s:hover{border-color:var(--accent);color:var(--accent)}
  .btn-t{background:var(--accent2);color:var(--bg)}.btn-t:hover{opacity:.9}
  .btn-d{background:transparent;color:var(--danger);border:1px solid var(--danger)}
  .btn-sm{padding:5px 11px;font-size:11px}
  .fi{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:9px 13px;color:var(--text);font-family:var(--fm);font-size:12px;outline:none;transition:border-color .15s}
  .fi:focus{border-color:var(--accent)}
  .flbl{font-family:var(--fm);font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;margin-bottom:5px;display:block}
  .fg{margin-bottom:14px}
  .frow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  select.fi option{background:var(--surface2)}
  textarea.fi{resize:vertical;min-height:80px}
  .tbl{width:100%;border-collapse:collapse}
  .tbl th{font-family:var(--fm);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);padding:7px 11px;text-align:left;border-bottom:1px solid var(--border)}
  .tbl td{padding:9px 11px;font-size:12px;border-bottom:1px solid rgba(42,42,50,.5);vertical-align:middle}
  .tbl tr:hover td{background:rgba(255,255,255,.02)}
  .tag{display:inline-block;padding:2px 7px;border-radius:4px;font-family:var(--fm);font-size:9px;font-weight:700;text-transform:uppercase}
  .tg{background:rgba(71,255,212,.12);color:var(--accent2);border:1px solid rgba(71,255,212,.2)}
  .ty{background:rgba(232,255,71,.12);color:var(--accent);border:1px solid rgba(232,255,71,.2)}
  .tr{background:rgba(255,71,71,.12);color:var(--danger);border:1px solid rgba(255,71,71,.2)}
  .tb{background:rgba(100,130,255,.12);color:#7b9aff;border:1px solid rgba(100,130,255,.2)}
  .tp{background:rgba(123,154,255,.12);color:#7b9aff;border:1px solid rgba(123,154,255,.2)}
  .sbar{width:60px;height:6px;background:var(--surface2);border-radius:3px;overflow:hidden}
  .sfill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--accent2),var(--accent))}
  .pbar{width:100%;height:4px;background:var(--surface2);border-radius:2px;overflow:hidden}
  .pfill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent2),var(--accent));transition:width .5s ease}
  .ti{display:flex;align-items:flex-start;gap:11px;padding:12px 14px;background:var(--surface2);border-radius:10px;border:1px solid var(--border);margin-bottom:9px;animation:fu .2s ease;transition:border-color .15s}
  .ti:hover{border-color:rgba(232,255,71,.3)}
  @keyframes fu{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .tck{width:17px;height:17px;border-radius:4px;border:1px solid var(--border);cursor:pointer;flex-shrink:0;margin-top:2px;display:flex;align-items:center;justify-content:center;transition:all .15s}
  .tck.on{background:var(--accent);border-color:var(--accent);color:var(--bg);font-size:10px}
  .av{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:var(--bg);flex-shrink:0}
  .chat-wrap{display:flex;flex-direction:column;height:460px}
  .msgs{flex:1;overflow-y:auto;padding:14px;background:var(--surface2);border-radius:10px;margin-bottom:10px;display:flex;flex-direction:column;gap:10px}
  .msgs::-webkit-scrollbar{width:4px}.msgs::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
  .msg{max-width:86%;padding:9px 13px;border-radius:10px;font-size:12px;line-height:1.6;animation:fu .2s ease}
  .mu{align-self:flex-end;background:var(--accent);color:var(--bg);font-weight:600}
  .mai{align-self:flex-start;background:var(--surface);border:1px solid var(--border);color:var(--text);font-family:var(--fm);white-space:pre-wrap}
  .ms{align-self:center;background:transparent;border:1px dashed var(--border);color:var(--muted);font-family:var(--fm);font-size:10px;padding:4px 11px;border-radius:20px}
  .ci{flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:9px 13px;color:var(--text);font-family:var(--ff);font-size:13px;outline:none;transition:border-color .15s}
  .ci:focus{border-color:var(--accent)}
  .spin{width:14px;height:14px;border:2px solid transparent;border-top-color:var(--bg);border-radius:50%;animation:sp .6s linear infinite;display:inline-block}
  @keyframes sp{to{transform:rotate(360deg)}}
  .pipe{display:flex;align-items:center;margin:18px 0}
  .ps2{flex:1;background:var(--surface2);border:1px solid var(--border);padding:11px 13px;text-align:center;position:relative}
  .ps2:first-child{border-radius:8px 0 0 8px}.ps2:last-child{border-radius:0 8px 8px 0}
  .ps2.on{background:rgba(232,255,71,.08);border-color:var(--accent)}
  .ps2::after{content:'→';position:absolute;right:-12px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;z-index:1}
  .ps2:last-child::after{display:none}
  .pn{font-size:18px;font-weight:800;color:var(--accent)}
  .pl{font-family:var(--fm);font-size:9px;color:var(--muted);margin-top:2px}
  .tcard{background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:13px;cursor:pointer;transition:all .15s;position:relative}
  .tcard:hover{border-color:var(--accent)}.tcard.sel{border-color:var(--accent);background:rgba(232,255,71,.05)}
  .tcard .ck{position:absolute;top:9px;right:9px;width:15px;height:15px;border-radius:50%;background:var(--accent);color:var(--bg);font-size:9px;display:flex;align-items:center;justify-content:center}
  .log-box{background:var(--surface2);border-radius:8px;padding:13px;font-family:var(--fm);font-size:10px;line-height:1.9;max-height:180px;overflow-y:auto;color:var(--muted)}
  /* LOGIN */
  .login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse at 50% 0%,rgba(232,255,71,.06) 0%,transparent 60%),var(--bg)}
  .login-box{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:40px;width:100%;max-width:420px}
  .login-logo{font-size:22px;font-weight:800;letter-spacing:-.5px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
  .login-sub{font-family:var(--fm);font-size:11px;color:var(--muted);margin-bottom:32px}
  .err{background:rgba(255,71,71,.12);border:1px solid rgba(255,71,71,.3);color:var(--danger);border-radius:8px;padding:10px 14px;font-family:var(--fm);font-size:11px;margin-bottom:14px}
  ::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
`

// ─── API HELPERS ──────────────────────────────────────────────────────────────
async function api(path: string, body?: object) {
  const res = await fetch(path, {
    method: body ? 'POST' : 'GET',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include', // sends the httpOnly cookie automatically
  })
  return res.json()
}

// ─── LOGIN SCREEN ─────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }: { onLogin: (u: User) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setLoading(true); setError('')
    try {
      const data = await api('/api/auth/login', { email, password })
      if (data.error) { setError(data.error); setLoading(false); return }
      onLogin(data.user)
    } catch {
      setError('Connection error — please try again')
      setLoading(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="login-logo"><div className="dot" />MedWave Agent</div>
        <div className="login-sub">Secure team dashboard · Sign in to continue</div>
        {error && <div className="err">{error}</div>}
        <div className="fg">
          <label className="flbl">Email</label>
          <input className="fi" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@medwavegroup.com" onKeyDown={e => e.key === 'Enter' && submit()} />
        </div>
        <div className="fg">
          <label className="flbl">Password</label>
          <input className="fi" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" onKeyDown={e => e.key === 'Enter' && submit()} />
        </div>
        <button className="btn btn-p" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} onClick={submit} disabled={loading}>
          {loading ? <><span className="spin" />Signing in…</> : 'Sign In →'}
        </button>
        <div style={{ marginTop: 20, fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)', textAlign: 'center' }}>
          Contact Davide to get your password
        </div>
      </div>
    </div>
  )
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [page, setPage] = useState('dashboard')
  const [leads, setLeads] = useState<Lead[]>(MOCK_LEADS)
  const [crmLeads, setCrmLeads] = useState<Lead[]>([])
  const [tasks, setTasks] = useState<Task[]>(INIT_TASKS)
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: 'system', text: 'MedWave Agent online — ask me to analyse leads, create tasks, or draft team messages.' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [scraping, setScraping] = useState(false)
  const [scrapeProgress, setScrapeProgress] = useState(0)
  const [deduping, setDeduping] = useState(false)
  const [dedupLog, setDedupLog] = useState<string[]>([])
  const [verifyingId, setVerifyingId] = useState<number | null>(null)
  const [verifyStatus, setVerifyStatus] = useState<Record<number, string>>({})
  const [selectedTeam, setSelectedTeam] = useState<string[]>([])
  const [dispatchMsg, setDispatchMsg] = useState('')
  const [dispatching, setDispatching] = useState(false)
  const [dispatchDone, setDispatchDone] = useState(false)
  const [scraperConfig, setScraperConfig] = useState({ keyword: 'holistic clinic', location: 'Cape Town', radius: '50', volume: '500', filter: 'GP,Wellness,Holistic,Physio' })
  const [transcript, setTranscript] = useState('')
  const [assessing, setAssessing] = useState(false)
  const [assessment, setAssessment] = useState('')
  const [assessScore, setAssessScore] = useState<number | null>(null)
  const [assessError, setAssessError] = useState('')
  const msgEnd = useRef<HTMLDivElement>(null)

  useEffect(() => { msgEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  if (!user) return <><style>{css}</style><LoginScreen onLogin={setUser} /></>

  const hotLeads = leads.filter(l => l.status === 'hot').length
  const doneTasks = tasks.filter(t => t.done).length

  // ── AI CHAT (calls secure backend) ─────────────────────────────────────────
  const sendChat = async () => {
    if (!chatInput.trim() || chatLoading) return
    const msg = chatInput.trim()
    setChatInput('')
    setMessages(m => [...m, { role: 'user', text: msg }])
    setChatLoading(true)
    const newHistory = [...chatHistory, { role: 'user', content: msg }]
    try {
      const data = await api('/api/ai/chat', { message: msg, history: chatHistory })
      if (data.error) throw new Error(data.error)
      setMessages(m => [...m, { role: 'ai', text: data.reply }])
      setChatHistory([...newHistory, { role: 'assistant', content: data.reply }])
    } catch (e: unknown) {
      setMessages(m => [...m, { role: 'ai', text: `Error: ${e instanceof Error ? e.message : 'unknown'}` }])
    }
    setChatLoading(false)
  }

  // ── SCRAPE + AUTO DEDUP ─────────────────────────────────────────────────────
  const runScrape = async () => {
    setScraping(true); setScrapeProgress(0)
    for (let i = 0; i <= 100; i += 5) {
      await new Promise(r => setTimeout(r, 80))
      setScrapeProgress(i)
    }
    setScraping(false)
    // Auto-dedup against CRM
    setMessages(m => [...m, { role: 'system', text: '🔄 Scrape done — checking leads against GoHighLevel CRM…' }])
    await runDedup(leads)
  }

  const runDedup = async (leadList: Lead[]) => {
    setDeduping(true)
    setDedupLog(['🔄 Connecting to GoHighLevel CRM…'])
    try {
      const data = await api('/api/leads/dedup', { leads: leadList })
      if (data.error) {
        setDedupLog(['⚠️ CRM dedup error: ' + data.error])
      } else {
        setLeads(data.newLeads)
        setCrmLeads((prev: Lead[]) => {
          const ids = new Set(prev.map((l: Lead) => l.id))
          return [...prev, ...data.crmLeads.filter((l: Lead) => !ids.has(l.id))]
        })
        setDedupLog(data.log)
        if (data.crmLeads.length > 0) {
          setMessages(m => [...m, { role: 'system', text: `✅ Dedup complete: ${data.newLeads.length} new · ${data.crmLeads.length} already in CRM` }])
          setPage('crm')
        }
      }
    } catch {
      setDedupLog(['⚠️ Could not reach dedup service'])
    }
    setDeduping(false)
  }

  // ── VERIFY + EMAIL ──────────────────────────────────────────────────────────
  const verifyLead = async (lead: Lead) => {
    setVerifyingId(lead.id)
    setMessages(m => [...m, { role: 'system', text: `🔍 Verifying ${lead.name} across multiple sources…` }])
    try {
      const data = await api('/api/leads/verify', { lead })
      if (data.error) throw new Error(data.error)
      setVerifyStatus(s => ({ ...s, [lead.id]: 'done' }))
      setMessages(m => [...m,
        { role: 'ai', text: `✅ ${lead.name} verified:\n\n${data.brief}` },
        { role: 'system', text: '📧 Full brief emailed to info@medwavegroup.com' }
      ])
      setPage('assistant')
    } catch (e: unknown) {
      setMessages(m => [...m, { role: 'ai', text: `Verification error: ${e instanceof Error ? e.message : 'unknown'}` }])
    }
    setVerifyingId(null)
  }

  // ── AI GENERATE TASKS ───────────────────────────────────────────────────────
  const generateTasks = async () => {
    setChatLoading(true)
    const data = await api('/api/ai/chat', {
      message: 'Generate 3 high-priority tasks for the MedWave team this week. Focus on: scaling lead outreach to 1000/day and closing PBM sales. Format: numbered list with [Davide] / [Erich] / [Sterrenberg] prefix then task.',
      history: []
    })
    if (data.reply) {
      const lines = data.reply.split('\n').filter((l: string) => l.match(/^\d+\./))
      lines.forEach((line: string, i: number) => {
        const aMatch = line.match(/\[(.*?)\]/)
        const title = line.replace(/^\d+\.\s*/, '').replace(/\[.*?\]\s*/, '').trim()
        const assigneeName = aMatch?.[1]?.toLowerCase() ?? 'davide'
        const assignee = TEAM.find(t => assigneeName.includes(t.id))?.id ?? 'davide'
        if (title) setTasks(ts => [...ts, { id: Date.now() + i, title, assignee, done: false, priority: 'high' }])
      })
      setMessages(m => [...m, { role: 'ai', text: data.reply }])
    }
    setChatLoading(false)
    setPage('tasks')
  }

  // ── DISPATCH EMAIL ──────────────────────────────────────────────────────────
  const sendDispatch = async () => {
    if (!dispatchMsg || selectedTeam.length === 0) return
    setDispatching(true)
    // First AI-draft if needed
    let body = dispatchMsg
    if (body.length < 40) {
      const data = await api('/api/ai/chat', {
        message: `Draft a concise team dispatch under 100 words. Recipients: ${selectedTeam.join(', ')}. Context: ${body}`,
        history: []
      })
      body = data.reply ?? body
      setDispatchMsg(body)
    }
    const data = await api('/api/dispatch/email', { recipientIds: selectedTeam, body, subject: 'MedWave Team Update' })
    setDispatching(false)
    if (!data.error) {
      setDispatchDone(true)
      setTimeout(() => setDispatchDone(false), 4000)
    }
  }

  // ── ASSESS SALES CALL ───────────────────────────────────────────────────────
  const runAssessment = async () => {
    if (!transcript.trim() || assessing) return
    setAssessing(true); setAssessError(''); setAssessment(''); setAssessScore(null)
    try {
      const data = await api('/api/ai/assess-call', { transcript })
      if (data.error) { setAssessError(data.error); setAssessing(false); return }
      setAssessment(data.assessment || '')
      setAssessScore(typeof data.score === 'number' ? data.score : null)
    } catch {
      setAssessError('Could not reach assessment service')
    }
    setAssessing(false)
  }

  const handleTranscriptFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => setTranscript(String(reader.result ?? ''))
    reader.readAsText(file)
  }

  const logout = async () => { await api('/api/auth/logout'); setUser(null) }
  const toggleTask = (id: number) => setTasks(ts => ts.map(t => t.id === id ? { ...t, done: !t.done } : t))
  const getAv = (id: string) => { const m = TEAM.find(t => t.id === id); return m ? <div className="av" style={{ background: m.color }}>{m.initials}</div> : null }

  // ── PAGES ───────────────────────────────────────────────────────────────────
  const Dashboard = () => (
    <div>
      <div className="ph"><div className="pt">Command Centre</div><div className="ps">MedWave Group · Eastern Cape, South Africa</div></div>
      <div className="sg">
        {[{ v: leads.length, l: 'Pipeline Leads', d: 'Active' }, { v: hotLeads, l: 'Hot Leads', d: 'Score > 80' }, { v: crmLeads.length, l: 'In CRM Already', d: 'Deduplicated' }, { v: `${doneTasks}/${tasks.length}`, l: 'Tasks Done', d: 'This sprint' }]
          .map((s, i) => <div className="sc" key={i}><div className="sv">{s.v}</div><div className="sl">{s.l}</div><div className="sd">{s.d}</div></div>)}
      </div>
      <div className="pipe">
        {[['500+', 'Scrape\nLeads'], ['124', 'Qualify\nwith AI'], ['38', 'Dedup\nCRM'], ['22', 'Outreach\nSent'], ['8', 'Demo\nBooked'], ['3', 'Closed']].map(([n, l], i) => (
          <div key={i} className={`ps2 ${i < 3 ? 'on' : ''}`}><div className="pn">{n}</div><div className="pl" style={{ whiteSpace: 'pre' }}>{l}</div></div>
        ))}
      </div>
      <div className="two">
        <div className="card"><div className="ct">Active Tasks</div>
          {tasks.filter(t => !t.done).slice(0, 3).map(t => (
            <div key={t.id} style={{ padding: '9px 0', borderBottom: '1px solid var(--border)', display: 'flex', gap: 9, alignItems: 'center' }}>
              {getAv(t.assignee)}
              <div style={{ flex: 1, fontSize: 12 }}>{t.title}</div>
              <span className={`tag ${t.priority === 'high' ? 'tr' : 'ty'}`}>{t.priority}</span>
            </div>
          ))}
          <button className="btn btn-s btn-sm" style={{ marginTop: 10, width: '100%' }} onClick={() => setPage('tasks')}>View All →</button>
        </div>
        <div className="card"><div className="ct">Hot Leads</div>
          {leads.filter(l => l.status === 'hot').slice(0, 3).map(l => (
            <div key={l.id} style={{ padding: '9px 0', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div><div style={{ fontSize: 13, fontWeight: 600 }}>{l.name}</div><div style={{ fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)' }}>{l.specialty} · {l.city}</div></div>
              <div style={{ textAlign: 'right' }}><div style={{ fontFamily: 'var(--fm)', fontSize: 18, fontWeight: 700, color: 'var(--accent)' }}>{l.score}</div><div style={{ fontFamily: 'var(--fm)', fontSize: 9, color: 'var(--muted)' }}>score</div></div>
            </div>
          ))}
          <button className="btn btn-s btn-sm" style={{ marginTop: 10, width: '100%' }} onClick={() => setPage('leads')}>View All →</button>
        </div>
      </div>
    </div>
  )

  const Scraper = () => (
    <div>
      <div className="ph"><div className="pt">Lead Scraper</div><div className="ps">google maps → openclaw → ai qualification → crm dedup</div></div>
      <div className="two">
        <div className="card"><div className="ct">Configuration</div>
          <div className="fg"><label className="flbl">Search Keyword</label><input className="fi" value={scraperConfig.keyword} onChange={e => setScraperConfig(c => ({ ...c, keyword: e.target.value }))} /></div>
          <div className="frow">
            <div className="fg"><label className="flbl">City / Region</label><input className="fi" value={scraperConfig.location} onChange={e => setScraperConfig(c => ({ ...c, location: e.target.value }))} /></div>
            <div className="fg"><label className="flbl">Radius (km)</label><input className="fi" type="number" value={scraperConfig.radius} onChange={e => setScraperConfig(c => ({ ...c, radius: e.target.value }))} /></div>
          </div>
          <div className="frow">
            <div className="fg"><label className="flbl">Volume</label>
              <select className="fi" value={scraperConfig.volume} onChange={e => setScraperConfig(c => ({ ...c, volume: e.target.value }))}>
                <option value="100">100 leads</option><option value="500">500 leads</option><option value="1000">1,000 leads</option>
              </select>
            </div>
            <div className="fg"><label className="flbl">Specialty Filter</label><input className="fi" value={scraperConfig.filter} onChange={e => setScraperConfig(c => ({ ...c, filter: e.target.value }))} /></div>
          </div>
          <button className="btn btn-p" style={{ width: '100%' }} onClick={runScrape} disabled={scraping || deduping}>
            {scraping ? <><span className="spin" />Scraping…</> : deduping ? <><span className="spin" />Deduping CRM…</> : '▶ Run Scraper + CRM Dedup'}
          </button>
          {(scraping || scrapeProgress > 0) && (
            <div style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)', marginBottom: 4 }}><span>Scraping</span><span>{scrapeProgress}%</span></div>
              <div className="pbar"><div className="pfill" style={{ width: `${scrapeProgress}%` }} /></div>
              {scrapeProgress === 100 && !deduping && <div style={{ marginTop: 8, fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--accent2)' }}>✓ {scraperConfig.volume} leads extracted → CRM dedup running</div>}
            </div>
          )}
        </div>
        <div className="card"><div className="ct">AI Qualification + CRM Dedup Pipeline</div>
          <div style={{ fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--muted)', lineHeight: 1.9, marginBottom: 14 }}>
            <b style={{ color: 'var(--accent)' }}>Step 1</b> — Scrape Google Maps via OpenClaw<br />
            <b style={{ color: 'var(--accent)' }}>Step 2</b> — AI scores each lead 0–100 vs your ICP<br />
            <b style={{ color: 'var(--accent)' }}>Step 3</b> — Check every lead against GHL CRM (server-side)<br />
            <b style={{ color: 'var(--accent)' }}>Step 4</b> — Duplicates → "In CRM Already" folder<br />
            <b style={{ color: 'var(--accent)' }}>Step 5</b> — Net-new leads → pipeline for outreach
          </div>
          {dedupLog.length > 0 && (
            <div className="log-box">
              {dedupLog.map((l, i) => <div key={i} style={{ color: l.includes('IN CRM') ? 'var(--accent2)' : l.includes('NEW') ? 'var(--accent)' : l.includes('Done') ? 'var(--text)' : 'var(--muted)' }}>{l || ' '}</div>)}
              {deduping && <div style={{ color: 'var(--accent)' }}>▌ checking…</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  const Leads = () => (
    <div>
      <div className="ph"><div className="pt">Lead Pipeline</div><div className="ps">{leads.length} leads · {hotLeads} hot · net-new only (CRM dupes removed)</div></div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div className="ct" style={{ marginBottom: 0 }}>All Net-New Leads</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-s btn-sm" onClick={() => runDedup(leads)} disabled={deduping}>{deduping ? 'Checking…' : '🔄 Re-check CRM'}</button>
            <button className="btn btn-p btn-sm" onClick={() => setPage('scraper')}>+ Scrape More</button>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="tbl">
            <thead><tr><th>Name</th><th>Practice</th><th>City</th><th>Specialty</th><th>Score</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {leads.map(l => (
                <tr key={l.id}>
                  <td style={{ fontWeight: 600 }}>{l.name}</td>
                  <td style={{ color: 'var(--muted)', fontSize: 11 }}>{l.practice}</td>
                  <td style={{ fontFamily: 'var(--fm)', fontSize: 11 }}>{l.city}</td>
                  <td><span className="tag tb">{l.specialty}</span></td>
                  <td><div style={{ display: 'flex', alignItems: 'center', gap: 7 }}><div className="sbar"><div className="sfill" style={{ width: `${l.score}%` }} /></div><span style={{ fontFamily: 'var(--fm)', fontSize: 11 }}>{l.score}</span></div></td>
                  <td><span className={`tag ${l.status === 'hot' ? 'tr' : l.status === 'warm' ? 'ty' : 'tg'}`}>{l.status}</span></td>
                  <td>
                    <button className="btn btn-p btn-sm" onClick={() => verifyLead(l)} disabled={verifyingId === l.id}>
                      {verifyingId === l.id ? <><span className="spin" style={{ borderTopColor: 'var(--bg)' }} />Verifying…</> : verifyStatus[l.id] ? '✓ Emailed' : '🔍 Verify & Email'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  const CRMAlready = () => (
    <div>
      <div className="ph"><div className="pt">In CRM Already</div><div className="ps">{crmLeads.length} contacts found in GoHighLevel · removed from active pipeline</div></div>
      {dedupLog.length > 0 && <div className="card" style={{ marginBottom: 18 }}><div className="ct">Last Dedup Log</div><div className="log-box">{dedupLog.map((l, i) => <div key={i} style={{ color: l.includes('IN CRM') ? 'var(--accent2)' : l.includes('NEW') ? 'var(--accent)' : 'var(--muted)' }}>{l || ' '}</div>)}</div></div>}
      <button className="btn btn-p" style={{ marginBottom: 18 }} onClick={() => runDedup(leads)} disabled={deduping}>{deduping ? <><span className="spin" style={{ borderTopColor: 'var(--bg)' }} />Checking…</> : '🔄 Run CRM Dedup Now'}</button>
      {crmLeads.length === 0
        ? <div className="card" style={{ textAlign: 'center', padding: '50px 20px' }}><div style={{ fontSize: 36, marginBottom: 10 }}>📭</div><div style={{ fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--muted)' }}>No CRM duplicates found yet.<br />Run a scrape or click "Run CRM Dedup Now".</div></div>
        : <div className="card">
          <div className="ct">GoHighLevel Contacts — Already in CRM</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="tbl">
              <thead><tr><th>Name</th><th>Practice</th><th>City</th><th>Specialty</th><th>Phone</th><th>ICP Score</th><th>CRM Status</th></tr></thead>
              <tbody>
                {crmLeads.map(l => (
                  <tr key={l.id}>
                    <td style={{ fontWeight: 600 }}>{l.name}</td>
                    <td style={{ color: 'var(--muted)', fontSize: 11 }}>{l.practice}</td>
                    <td style={{ fontFamily: 'var(--fm)', fontSize: 11 }}>{l.city}</td>
                    <td><span className="tag tb">{l.specialty}</span></td>
                    <td style={{ fontFamily: 'var(--fm)', fontSize: 11 }}>{l.phone}</td>
                    <td><div style={{ display: 'flex', alignItems: 'center', gap: 7 }}><div className="sbar"><div className="sfill" style={{ width: `${l.score}%`, background: 'linear-gradient(90deg,#7b9aff,#47ffd4)' }} /></div><span style={{ fontFamily: 'var(--fm)', fontSize: 11 }}>{l.score}</span></div></td>
                    <td><span className="tag tp">✓ In GHL</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12, fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)' }}>These contacts are tracked in GHL Location: QdLXaFEqrdF0JbVbpKLw</div>
        </div>}
    </div>
  )

  const Tasks = () => (
    <div>
      <div className="ph"><div className="pt">Task Board</div><div className="ps">{doneTasks}/{tasks.length} complete · assigned to your team</div></div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        <button className="btn btn-p" onClick={generateTasks} disabled={chatLoading}>{chatLoading ? <><span className="spin" />Generating…</> : '⚡ AI Generate Tasks'}</button>
        <button className="btn btn-s" onClick={() => setPage('dispatch')}>📤 Dispatch to Team</button>
      </div>
      <div className="pbar" style={{ marginBottom: 18 }}><div className="pfill" style={{ width: `${tasks.length ? (doneTasks / tasks.length) * 100 : 0}%` }} /></div>
      {tasks.map(t => (
        <div className="ti" key={t.id}>
          <div className={`tck ${t.done ? 'on' : ''}`} onClick={() => toggleTask(t.id)}>{t.done ? '✓' : ''}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 600, textDecoration: t.done ? 'line-through' : 'none', color: t.done ? 'var(--muted)' : 'var(--text)', marginBottom: 5 }}>{t.title}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              {getAv(t.assignee)}
              <span style={{ fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)' }}>{TEAM.find(m => m.id === t.assignee)?.name}</span>
              <span className={`tag ${t.priority === 'high' ? 'tr' : 'ty'}`}>{t.priority}</span>
              {t.done && <span className="tag tg">done</span>}
            </div>
          </div>
          <button className="btn btn-d btn-sm" onClick={() => setTasks(ts => ts.filter(x => x.id !== t.id))}>✕</button>
        </div>
      ))}
    </div>
  )

  const Dispatch = () => (
    <div>
      <div className="ph"><div className="pt">Team Dispatch</div><div className="ps">AI-draft and email your team directly</div></div>
      <div className="two">
        <div className="card"><div className="ct">Recipients</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {TEAM.map(m => (
              <div key={m.id} className={`tcard ${selectedTeam.includes(m.id) ? 'sel' : ''}`} onClick={() => setSelectedTeam(s => s.includes(m.id) ? s.filter(x => x !== m.id) : [...s, m.id])}>
                {selectedTeam.includes(m.id) && <div className="ck">✓</div>}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="av" style={{ width: 30, height: 30, fontSize: 11, background: m.color }}>{m.initials}</div>
                  <div><div style={{ fontWeight: 700, fontSize: 13 }}>{m.name}</div>
                    <div style={{ fontFamily: 'var(--fm)', fontSize: 9, color: 'var(--accent2)' }}>{m.email}</div>
                    {m.phone && <div style={{ fontFamily: 'var(--fm)', fontSize: 9, color: 'var(--muted)' }}>{m.phone}</div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card"><div className="ct">Message</div>
          <div className="fg"><label className="flbl">Context / Message</label>
            <textarea className="fi" rows={5} value={dispatchMsg} onChange={e => setDispatchMsg(e.target.value)} placeholder="Type your update or just a brief — AI will draft it properly…" />
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className="btn btn-s" disabled={dispatching || selectedTeam.length === 0 || !dispatchMsg} onClick={sendDispatch}>
              {dispatching ? <><span className="spin" style={{ borderTopColor: 'var(--text)' }} />Sending…</> : '📧 AI Draft + Send Email'}
            </button>
          </div>
          {dispatchDone && <div style={{ marginTop: 12, fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--accent2)' }}>✓ Sent to: {selectedTeam.map(id => TEAM.find(t => t.id === id)?.email).filter(Boolean).join(', ')}</div>}
          {selectedTeam.length > 0 && <div style={{ marginTop: 10, fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)' }}>To: {selectedTeam.map(id => TEAM.find(t => t.id === id)?.email).filter(Boolean).join(' · ')}</div>}
        </div>
      </div>
    </div>
  )

  const CallCoach = () => {
    const scoreColor = assessScore == null ? 'var(--muted)'
      : assessScore >= 9 ? 'var(--accent2)'
      : assessScore >= 7 ? 'var(--accent)'
      : assessScore >= 5 ? '#ffb547'
      : 'var(--danger)'
    const scoreLabel = assessScore == null ? ''
      : assessScore >= 9 ? 'Excellent'
      : assessScore >= 7 ? 'Strong'
      : assessScore >= 5 ? 'Average'
      : assessScore >= 3 ? 'Below Average'
      : 'Poor'
    return (
      <div>
        <div className="ph"><div className="pt">Call Coach</div><div className="ps">paste a google meet transcript · scored against the medwave six-stage framework</div></div>
        <div className="two">
          <div className="card">
            <div className="ct">Transcript</div>
            <div className="fg">
              <label className="flbl">Paste transcript or upload .txt</label>
              <textarea
                className="fi"
                rows={18}
                value={transcript}
                onChange={e => setTranscript(e.target.value)}
                placeholder="Paste the full Google Meet transcript here — speaker labels and timestamps are fine…"
              />
            </div>
            <div style={{ display: 'flex', gap: 9, alignItems: 'center', flexWrap: 'wrap' }}>
              <label className="btn btn-s btn-sm" style={{ cursor: 'pointer' }}>
                📄 Upload .txt
                <input
                  type="file"
                  accept=".txt,.vtt,.md,text/plain"
                  style={{ display: 'none' }}
                  onChange={e => { const f = e.target.files?.[0]; if (f) handleTranscriptFile(f) }}
                />
              </label>
              <button className="btn btn-s btn-sm" onClick={() => { setTranscript(''); setAssessment(''); setAssessScore(null); setAssessError('') }}>Clear</button>
              <div style={{ flex: 1 }} />
              <span style={{ fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--muted)' }}>{transcript.length.toLocaleString()} chars</span>
              <button className="btn btn-p" onClick={runAssessment} disabled={assessing || transcript.trim().length < 100}>
                {assessing ? <><span className="spin" />Assessing…</> : '▶ Assess Call'}
              </button>
            </div>
            {assessError && <div className="err" style={{ marginTop: 12 }}>{assessError}</div>}
          </div>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div className="ct" style={{ marginBottom: 0 }}>Assessment</div>
              {assessScore != null && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className="tag" style={{ borderColor: scoreColor, color: scoreColor, background: 'transparent', border: `1px solid ${scoreColor}` }}>{scoreLabel}</span>
                  <div style={{ fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--muted)' }}>Score</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: scoreColor, letterSpacing: '-1px' }}>{assessScore}<span style={{ fontSize: 13, color: 'var(--muted)' }}>/10</span></div>
                </div>
              )}
            </div>
            {!assessment && !assessing && (
              <div style={{ fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--muted)', lineHeight: 1.9 }}>
                Framework covers 6 stages:<br />
                <b style={{ color: 'var(--accent)' }}>1.</b> Introduction & Fit · <b style={{ color: 'var(--accent)' }}>2.</b> PPP Discovery (+ PIE)<br />
                <b style={{ color: 'var(--accent)' }}>3.</b> Diagnosis · <b style={{ color: 'var(--accent)' }}>4.</b> Permission to Pitch<br />
                <b style={{ color: 'var(--accent)' }}>5.</b> Value Pitch (Patient / Productivity / Profitability)<br />
                <b style={{ color: 'var(--accent)' }}>6.</b> Close (Deposit Ask)<br /><br />
                Paste a transcript and click <b style={{ color: 'var(--accent)' }}>Assess Call</b> to get stage-by-stage feedback, strengths, gaps, Hormozi-vs-Minor style alignment, and a coaching direction.
              </div>
            )}
            {assessing && <div style={{ fontFamily: 'var(--fm)', fontSize: 11, color: 'var(--muted)' }}>▌ analysing transcript against the six-stage framework…</div>}
            {assessment && (
              <div style={{ fontFamily: 'var(--fm)', fontSize: 12, lineHeight: 1.75, color: 'var(--text)', whiteSpace: 'pre-wrap', maxHeight: 560, overflowY: 'auto', paddingRight: 6 }}>
                {assessment}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  const Assistant = () => (
    <div>
      <div className="ph"><div className="pt">AI Assistant</div><div className="ps">powered by GLM-4.5-Air · always on · context-aware</div></div>
      <div className="card">
        <div className="chat-wrap">
          <div className="msgs">
            {messages.map((m, i) => <div key={i} className={`msg ${m.role === 'user' ? 'mu' : m.role === 'ai' ? 'mai' : 'ms'}`}>{m.text}</div>)}
            {chatLoading && <div className="msg mai">▌ thinking…</div>}
            <div ref={msgEnd} />
          </div>
          <div style={{ display: 'flex', gap: 9 }}>
            <input className="ci" value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendChat()} placeholder="Ask me anything about MedWave leads, tasks, strategy…" />
            <button className="btn btn-p" onClick={sendChat} disabled={chatLoading}>{chatLoading ? <span className="spin" /> : 'Send'}</button>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {['Scrape 500 GP leads in Gauteng', 'Which leads should I call today?', 'Create tasks for this week', 'How is the pipeline looking?', 'Draft a WhatsApp follow-up for a hot lead'].map(s => (
          <button key={s} className="btn btn-s btn-sm" onClick={() => setChatInput(s)}>{s}</button>
        ))}
      </div>
    </div>
  )

  // ── NAV + SHELL ─────────────────────────────────────────────────────────────
  const NAV = [
    { id: 'dashboard', label: 'Dashboard', icon: '⬛' },
    { id: 'scraper', label: 'Lead Scraper', icon: '⚙' },
    { id: 'leads', label: 'Leads', icon: '◎', badge: leads.filter(l => l.status === 'hot').length, cls: '' },
    { id: 'crm', label: 'In CRM Already', icon: '🗄', badge: crmLeads.length, cls: '2' },
    { id: 'tasks', label: 'Tasks', icon: '☑', badge: tasks.filter(t => !t.done).length, cls: '' },
    { id: 'dispatch', label: 'Dispatch', icon: '↑' },
    { id: 'coach', label: 'Call Coach', icon: '◉' },
    { id: 'assistant', label: 'AI Assistant', icon: '◈' },
  ]

  return (
    <>
      <style>{css}</style>
      <div className="app">
        <header className="hd">
          <div className="logo"><div className="dot" />MedWave Agent</div>
          <div className="hd-right">
            <div className="badge">● AGENT ONLINE</div>
            <div className="badge badge2">● CRM LINKED</div>
            <span style={{ color: 'var(--muted)' }}>GLM-4.5-Air</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="av" style={{ width: 26, height: 26, fontSize: 10, background: TEAM.find(t => t.id === user.id)?.color ?? '#7b9aff' }}>
                {TEAM.find(t => t.id === user.id)?.initials ?? user.name[0]}
              </div>
              <span>{user.name}</span>
            </div>
            <button className="btn btn-s btn-sm" onClick={logout}>Sign Out</button>
          </div>
        </header>
        <nav className="sb">
          <div>
            <div className="nav-lbl">Navigation</div>
            {NAV.map(n => (
              <div key={n.id} className={`nav-it ${page === n.id ? 'on' : ''}`} onClick={() => setPage(n.id)}>
                <span>{n.icon}</span>{n.label}
                {(n.badge ?? 0) > 0 && <span className={`nbadge${n.cls ?? ''}`}>{n.badge}</span>}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <div className="nav-lbl">Team</div>
            {TEAM.map(m => (
              <div key={m.id} className="nav-it" style={{ gap: 9 }}>
                <div className="av" style={{ width: 20, height: 20, fontSize: 8, background: m.color }}>{m.initials}</div>
                <div><div style={{ fontSize: 12 }}>{m.name}</div><div style={{ fontFamily: 'var(--fm)', fontSize: 9, color: 'var(--muted)' }}>{m.role}</div></div>
              </div>
            ))}
          </div>
        </nav>
        <main className="mn">
          {page === 'dashboard' && <Dashboard />}
          {page === 'scraper' && <Scraper />}
          {page === 'leads' && <Leads />}
          {page === 'crm' && <CRMAlready />}
          {page === 'tasks' && <Tasks />}
          {page === 'dispatch' && <Dispatch />}
          {page === 'coach' && <CallCoach />}
          {page === 'assistant' && <Assistant />}
        </main>
      </div>
    </>
  )
}
