import { useCallback, useEffect, useRef, useState } from 'react'

import { apiFetch, wsUrl } from '../lib/api'
import { CLEANING_PROMPT } from '../lib/cleaningPrompt'

export type WsEvent = Record<string, unknown>

export type Phase = 'idle' | 'creating' | 'uploading' | 'running' | 'complete'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export type UploadMeta = {
  fileName: string
  fileSize: number
  rows: number
} | null

function newId(): string {
  return crypto.randomUUID()
}

/** 避免 StrictMode 双 effect 各建一会话；仅首屏用 */
let hiSessionBootOnce = false

export function useSessionRun() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [goal, setGoal] = useState('')
  const [maxIter, setMaxIter] = useState(15)
  const [events, setEvents] = useState<WsEvent[]>([])
  const [finalAnswer, setFinalAnswer] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [uploadMeta, setUploadMeta] = useState<UploadMeta>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [uploadReady, setUploadReady] = useState(false)
  const [cleaningDone, setCleaningDone] = useState(false)
  const [cleaningSummary, setCleaningSummary] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const wsRef = useRef<WebSocket | null>(null)
  const lastQueryRef = useRef('')
  const wsRunKindRef = useRef<'clean' | 'chat'>('chat')
  const mountedRef = useRef(true)

  const appendEvent = useCallback((e: WsEvent) => {
    setEvents((prev) => [...prev.slice(-200), e])
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [])

  const fetchNewSession = useCallback(async (): Promise<boolean> => {
    setError(null)
    setPhase('creating')
    setStatus('正在准备会话…')
    try {
      const r = await apiFetch('/sessions', { method: 'POST' })
      if (!r.ok) {
        if (mountedRef.current) {
          setError(`创建会话失败（HTTP ${r.status}）`)
          setStatus('')
          setPhase('idle')
        }
        return false
      }
      const j = (await r.json()) as { session_id: string }
      if (!mountedRef.current) return true
      setSessionId(j.session_id)
      setEvents([])
      setFinalAnswer('')
      setMessages([])
      setUploadReady(false)
      setUploadMeta(null)
      setCleaningDone(false)
      setCleaningSummary('')
      setGoal('')
      lastQueryRef.current = ''
      setStatus('已就绪，请上传 CSV。')
      setPhase('idle')
      return true
    } catch (e) {
      if (mountedRef.current) {
        setError(e instanceof Error ? e.message : '创建会话时网络异常')
        setStatus('')
        setPhase('idle')
      }
      return false
    }
  }, [])

  useEffect(() => {
    if (hiSessionBootOnce) return
    hiSessionBootOnce = true
    void fetchNewSession()
  }, [fetchNewSession])

  const uploadFile = useCallback(
    async (file: File | null) => {
      if (!file || !sessionId) return
      setError(null)
      setPhase('uploading')
      setStatus('上传 CSV…')
      try {
        const fd = new FormData()
        fd.append('file', file)
        const r = await apiFetch(`/sessions/${sessionId}/upload`, { method: 'POST', body: fd })
        if (!r.ok) {
          setError(`上传失败（HTTP ${r.status}）`)
          setStatus('')
          setUploadReady(false)
          setUploadMeta(null)
          setPhase('idle')
          return
        }
        const j = (await r.json()) as { rows: number; columns: string[] }
        setUploadReady(true)
        setCleaningDone(false)
        setCleaningSummary('')
        setUploadMeta({
          fileName: file.name,
          fileSize: file.size,
          rows: j.rows,
        })
        setStatus(`已上传 ${j.rows} 条房源记录，请点击「运行清洗」。`)
        setPhase('idle')
      } catch (e) {
        setError(e instanceof Error ? e.message : '上传时网络异常')
        setUploadReady(false)
        setUploadMeta(null)
        setStatus('')
        setPhase('idle')
      }
    },
    [sessionId],
  )

  const clearConversation = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setMessages([])
    setEvents([])
    setFinalAnswer('')
    setGoal('')
    lastQueryRef.current = ''
    setStatus(cleaningDone ? '对话已清空，可继续提问。' : '')
    setError(null)
    setPhase('idle')
  }, [cleaningDone])

  const attachWsHandlers = useCallback(
    (ws: WebSocket) => {
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as WsEvent
          appendEvent(msg)
          const kind = wsRunKindRef.current

          if (msg.event === 'final') {
            const ans = String(msg.final_answer ?? '')
            setFinalAnswer(ans)
            if (kind === 'clean') {
              setCleaningSummary(ans)
            } else {
              setMessages((prev) => [...prev, { id: newId(), role: 'assistant', content: ans }])
            }
          }
          if (msg.event === 'done') {
            if (kind === 'clean') {
              setStatus('数据清洗阶段已完成，可在右侧提问。')
              setCleaningDone(true)
            } else {
              setStatus('分析完成。')
            }
            setPhase('complete')
          }
          if (msg.event === 'error') {
            const m = String(msg.message ?? '')
            const errText = m || '服务端返回错误'
            if (kind === 'clean') {
              setError(`清洗阶段：${errText}`)
            } else {
              setMessages((prev) => [
                ...prev,
                { id: newId(), role: 'assistant', content: `**分析出错**\n\n${errText}` },
              ])
            }
            setStatus('')
            setPhase('idle')
          }
        } catch {
          appendEvent({ event: 'parse_error', raw: ev.data })
        }
      }

      ws.onerror = () => {
        const errText = 'WebSocket 连接异常，请确认后端已启动且代理配置正确。'
        if (wsRunKindRef.current === 'clean') {
          setError(errText)
        } else {
          setMessages((prev) => [
            ...prev,
            { id: newId(), role: 'assistant', content: `**连接失败**\n\n${errText}` },
          ])
        }
        setStatus('')
        setPhase('idle')
      }

      ws.onclose = () => {
        wsRef.current = null
      }
    },
    [appendEvent],
  )

  const runCleaning = useCallback(() => {
    if (!sessionId) {
      setError('会话未就绪，请稍后重试或刷新页面。')
      return
    }
    if (!uploadReady) {
      setError('请先上传 CSV 文件。')
      return
    }
    if (cleaningDone) return

    setError(null)
    wsRef.current?.close()
    wsRef.current = null
    setEvents([])
    setFinalAnswer('')
    setCleaningSummary('')
    wsRunKindRef.current = 'clean'
    setPhase('running')
    setStatus('正在运行数据清洗…')

    const ws = new WebSocket(wsUrl(sessionId))
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('清洗任务进行中…')
      ws.send(JSON.stringify({ cmd: 'run', goal: CLEANING_PROMPT, max_iterations: maxIter }))
    }

    attachWsHandlers(ws)
  }, [sessionId, uploadReady, cleaningDone, maxIter, attachWsHandlers])

  const sendQuery = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) {
        setError('请输入分析问题。')
        return
      }
      if (!sessionId) {
        setError('会话未就绪。')
        return
      }
      if (!uploadReady) {
        setError('请先上传 CSV 文件。')
        return
      }
      if (!cleaningDone) {
        setError('请先完成左侧「运行清洗」后再提问。')
        return
      }

      setError(null)
      wsRef.current?.close()
      wsRef.current = null
      setEvents([])
      setFinalAnswer('')
      setGoal(trimmed)
      lastQueryRef.current = trimmed
      wsRunKindRef.current = 'chat'
      setMessages((prev) => [...prev, { id: newId(), role: 'user', content: trimmed }])
      setPhase('running')
      setStatus('连接 WebSocket…')

      const ws = new WebSocket(wsUrl(sessionId))
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('分析进行中…')
        ws.send(JSON.stringify({ cmd: 'run', goal: trimmed, max_iterations: maxIter }))
      }

      attachWsHandlers(ws)
    },
    [sessionId, uploadReady, cleaningDone, maxIter, attachWsHandlers],
  )

  const retryLastQuery = useCallback(() => {
    const t = lastQueryRef.current
    if (t) sendQuery(t)
  }, [sendQuery])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const reset = useCallback(async () => {
    wsRef.current?.close()
    wsRef.current = null
    setSessionId(null)
    setEvents([])
    setFinalAnswer('')
    setMessages([])
    setUploadReady(false)
    setUploadMeta(null)
    setCleaningDone(false)
    setCleaningSummary('')
    setGoal('')
    lastQueryRef.current = ''
    setStatus('')
    setError(null)
    setPhase('idle')
    await fetchNewSession()
  }, [fetchNewSession])

  const isFormBusy = phase === 'creating' || phase === 'uploading' || phase === 'running'

  return {
    sessionId,
    goal,
    setGoal,
    maxIter,
    setMaxIter,
    events,
    finalAnswer,
    messages,
    status,
    error,
    uploadReady,
    uploadMeta,
    cleaningDone,
    cleaningSummary,
    phase,
    isFormBusy,
    fetchNewSession,
    uploadFile,
    runCleaning,
    sendQuery,
    retryLastQuery,
    clearConversation,
    clearError,
    reset,
  }
}
