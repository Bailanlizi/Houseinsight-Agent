import { useCallback, useRef, useState } from 'react'
import './App.css'

type WsEvent = Record<string, unknown>

function apiBase(): string {
  const b = import.meta.env.VITE_API_BASE as string | undefined
  return b?.replace(/\/$/, '') ?? ''
}

function wsUrl(sessionId: string): string {
  const api = import.meta.env.VITE_API_BASE as string | undefined
  if (api) {
    const u = new URL(api)
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    u.pathname = `/sessions/${sessionId}/ws`
    u.search = ''
    u.hash = ''
    return u.toString()
  }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/sessions/${sessionId}/ws`
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = apiBase()
  const url = base ? `${base}${path}` : path
  return fetch(url, init)
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [goal, setGoal] = useState('分析这个数据集')
  const [maxIter, setMaxIter] = useState(15)
  const [events, setEvents] = useState<WsEvent[]>([])
  const [finalAnswer, setFinalAnswer] = useState('')
  const [status, setStatus] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  const appendEvent = useCallback((e: WsEvent) => {
    setEvents((prev) => [...prev.slice(-200), e])
  }, [])

  const createSession = async () => {
    setStatus('创建会话…')
    const r = await apiFetch('/sessions', { method: 'POST' })
    if (!r.ok) {
      setStatus(`创建失败: ${r.status}`)
      return
    }
    const j = (await r.json()) as { session_id: string }
    setSessionId(j.session_id)
    setEvents([])
    setFinalAnswer('')
    setStatus(`会话已创建: ${j.session_id}`)
  }

  const onUpload = async (file: File | null) => {
    if (!file || !sessionId) return
    setStatus('上传 CSV…')
    const fd = new FormData()
    fd.append('file', file)
    const r = await apiFetch(`/sessions/${sessionId}/upload`, { method: 'POST', body: fd })
    if (!r.ok) {
      setStatus(`上传失败: ${r.status}`)
      return
    }
    const j = (await r.json()) as { rows: number; columns: string[] }
    setStatus(`已上传 ${j.rows} 行，列: ${j.columns.join(', ')}`)
  }

  const runAnalysis = () => {
    if (!sessionId) {
      setStatus('请先创建会话并上传 CSV')
      return
    }
    wsRef.current?.close()
    setEvents([])
    setFinalAnswer('')
    setStatus('连接 WebSocket…')
    const ws = new WebSocket(wsUrl(sessionId))
    wsRef.current = ws
    ws.onopen = () => {
      setStatus('已连接，发送 run…')
      ws.send(JSON.stringify({ cmd: 'run', goal, max_iterations: maxIter }))
    }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as WsEvent
        appendEvent(msg)
        if (msg.event === 'final') {
          setFinalAnswer(String(msg.final_answer ?? ''))
        }
        if (msg.event === 'done') {
          setStatus('分析完成')
        }
        if (msg.event === 'error') {
          setStatus(`错误: ${String(msg.message ?? '')}`)
        }
      } catch {
        appendEvent({ event: 'parse_error', raw: ev.data })
      }
    }
    ws.onerror = () => setStatus('WebSocket 错误')
    ws.onclose = () => {
      wsRef.current = null
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>HouseInsight Agent</h1>
        <p className="muted">上传 CSV → 输入目标 → WebSocket 实时进度</p>
      </header>

      <section className="panel">
        <button type="button" onClick={createSession}>
          1. 创建会话
        </button>
        {sessionId && (
          <span className="sid">
                会话 ID: <code>{sessionId}</code>
              </span>
        )}
      </section>

      <section className="panel">
        <label>
          2. 选择 CSV
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={!sessionId}
            onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
          />
        </label>
      </section>

      <section className="panel">
        <label>
          分析目标
          <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={3} />
        </label>
        <label>
          最大迭代
          <input
            type="number"
            min={1}
            max={50}
            value={maxIter}
            onChange={(e) => setMaxIter(Number(e.target.value) || 15)}
          />
        </label>
        <button type="button" disabled={!sessionId} onClick={runAnalysis}>
          3. 开始分析（WebSocket）
        </button>
      </section>

      <p className="status">{status}</p>

      <section className="split">
        <div className="col">
          <h2>事件流</h2>
          <ul className="events">
            {events.map((e, i) => (
              <li key={i}>
                <strong>{String(e.event)}</strong>
                {e.node != null && <span> · {String(e.node)}</span>}
                {e.tool != null && <span> · {String(e.tool)}</span>}
                {e.ok != null && <span> · ok={String(e.ok)}</span>}
              </li>
            ))}
          </ul>
        </div>
        <div className="col">
          <h2>最终回答</h2>
          <pre className="answer">{finalAnswer || '—'}</pre>
        </div>
      </section>
    </div>
  )
}
