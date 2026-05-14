import { useCallback, useEffect, useRef, useState } from 'react'

import { apiFetch, wsUrl } from '../lib/api'

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
  const [phase, setPhase] = useState<Phase>('idle')
  const wsRef = useRef<WebSocket | null>(null)
  const lastQueryRef = useRef('')

  const appendEvent = useCallback((e: WsEvent) => {
    setEvents((prev) => [...prev.slice(-200), e])
  }, [])

  useEffect(() => {
    return () => {
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [])

  const createSession = useCallback(async () => {
    setError(null)
    setPhase('creating')
    setStatus('创建会话…')
    try {
      const r = await apiFetch('/sessions', { method: 'POST' })
      if (!r.ok) {
        setError(`创建会话失败（HTTP ${r.status}）`)
        setStatus('')
        setPhase('idle')
        return
      }
      const j = (await r.json()) as { session_id: string }
      setSessionId(j.session_id)
      setEvents([])
      setFinalAnswer('')
      setMessages([])
      setUploadReady(false)
      setUploadMeta(null)
      setGoal('')
      lastQueryRef.current = ''
      setStatus('会话已创建。')
      setPhase('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建会话时网络异常')
      setStatus('')
      setPhase('idle')
    }
  }, [])

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
        setUploadMeta({
          fileName: file.name,
          fileSize: file.size,
          rows: j.rows,
        })
        setStatus(`已上传 ${j.rows} 条房源记录`)
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
    setStatus('')
    setError(null)
    setPhase('idle')
  }, [])

  const sendQuery = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) {
        setError('请输入分析问题。')
        return
      }
      if (!sessionId) {
        setError('请先创建会话并上传 CSV。')
        return
      }
      if (!uploadReady) {
        setError('请先上传 CSV 文件。')
        return
      }
      setError(null)
      wsRef.current?.close()
      wsRef.current = null
      setEvents([])
      setFinalAnswer('')
      setGoal(trimmed)
      lastQueryRef.current = trimmed
      setMessages((prev) => [...prev, { id: newId(), role: 'user', content: trimmed }])
      setPhase('running')
      setStatus('连接 WebSocket…')

      const ws = new WebSocket(wsUrl(sessionId))
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('分析进行中…')
        ws.send(JSON.stringify({ cmd: 'run', goal: trimmed, max_iterations: maxIter }))
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as WsEvent
          appendEvent(msg)
          if (msg.event === 'final') {
            const ans = String(msg.final_answer ?? '')
            setFinalAnswer(ans)
            setMessages((prev) => [...prev, { id: newId(), role: 'assistant', content: ans }])
          }
          if (msg.event === 'done') {
            setStatus('分析完成。')
            setPhase('complete')
          }
          if (msg.event === 'error') {
            const m = String(msg.message ?? '')
            const errText = m || '服务端返回错误'
            setMessages((prev) => [
              ...prev,
              {
                id: newId(),
                role: 'assistant',
                content: `**分析出错**\n\n${errText}`,
              },
            ])
            setStatus('')
            setPhase('idle')
          }
        } catch {
          appendEvent({ event: 'parse_error', raw: ev.data })
        }
      }

      ws.onerror = () => {
        const errText = 'WebSocket 连接异常，请确认后端已启动且代理配置正确。'
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            role: 'assistant',
            content: `**连接失败**\n\n${errText}`,
          },
        ])
        setStatus('')
        setPhase('idle')
      }

      ws.onclose = () => {
        wsRef.current = null
      }
    },
    [sessionId, uploadReady, maxIter, appendEvent],
  )

  const retryLastQuery = useCallback(() => {
    const t = lastQueryRef.current
    if (t) sendQuery(t)
  }, [sendQuery])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setSessionId(null)
    setEvents([])
    setFinalAnswer('')
    setMessages([])
    setUploadReady(false)
    setUploadMeta(null)
    setGoal('')
    lastQueryRef.current = ''
    setStatus('')
    setError(null)
    setPhase('idle')
  }, [])

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
    phase,
    isFormBusy,
    createSession,
    uploadFile,
    sendQuery,
    retryLastQuery,
    clearConversation,
    clearError,
    reset,
  }
}
