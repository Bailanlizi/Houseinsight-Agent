import { useCallback, useEffect, useRef, useState } from 'react'

import { apiFetch, wsUrl } from '../lib/api'

export type WsEvent = Record<string, unknown>

type Phase = 'idle' | 'creating' | 'uploading' | 'running' | 'complete'

export function useSessionRun() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [goal, setGoal] = useState('分析这个数据集')
  const [maxIter, setMaxIter] = useState(15)
  const [events, setEvents] = useState<WsEvent[]>([])
  const [finalAnswer, setFinalAnswer] = useState('')
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [uploadReady, setUploadReady] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const wsRef = useRef<WebSocket | null>(null)

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
      setUploadReady(false)
      setStatus(`会话已创建。`)
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
          setPhase('idle')
          return
        }
        const j = (await r.json()) as { rows: number; columns: string[] }
        setUploadReady(true)
        setStatus(`已上传 ${j.rows} 行；列：${j.columns.join('、')}`)
        setPhase('idle')
      } catch (e) {
        setError(e instanceof Error ? e.message : '上传时网络异常')
        setUploadReady(false)
        setStatus('')
        setPhase('idle')
      }
    },
    [sessionId],
  )

  const startRun = useCallback(() => {
    if (!sessionId) {
      setError('请先创建会话并上传 CSV。')
      return
    }
    if (!uploadReady) {
      setError('请先选择并上传 CSV 文件。')
      return
    }
    setError(null)
    wsRef.current?.close()
    wsRef.current = null
    setEvents([])
    setFinalAnswer('')
    setPhase('running')
    setStatus('连接 WebSocket…')

    const ws = new WebSocket(wsUrl(sessionId))
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('已连接，正在执行分析…')
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
          setStatus('分析完成。')
          setPhase('complete')
        }
        if (msg.event === 'error') {
          const m = String(msg.message ?? '')
          setError(m || '服务端返回错误')
          setStatus('')
          setPhase('idle')
        }
      } catch {
        appendEvent({ event: 'parse_error', raw: ev.data })
      }
    }

    ws.onerror = () => {
      setError('WebSocket 连接异常，请确认后端已启动且代理配置正确。')
      setStatus('')
      setPhase('idle')
    }

    ws.onclose = () => {
      wsRef.current = null
    }
  }, [sessionId, goal, maxIter, uploadReady, appendEvent])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setSessionId(null)
    setEvents([])
    setFinalAnswer('')
    setUploadReady(false)
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
    status,
    error,
    uploadReady,
    phase,
    isFormBusy,
    createSession,
    uploadFile,
    startRun,
    clearError,
    reset,
  }
}
