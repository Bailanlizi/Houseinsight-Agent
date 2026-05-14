import { useCallback, useRef } from 'react'
import type { DragEvent } from 'react'

import type { Phase, UploadMeta } from '../hooks/useSessionRun'

type Props = {
  sessionId: string | null
  phase: Phase
  isBusy: boolean
  status: string
  uploadMeta: UploadMeta
  uploadReady: boolean
  cleaningDone: boolean
  cleaningSummary: string
  uploadFile: (file: File | null) => Promise<void>
  runCleaning: () => void
  onNewChat: () => void
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function DataPanel({
  sessionId,
  phase,
  isBusy,
  status,
  uploadMeta,
  uploadReady,
  cleaningDone,
  cleaningSummary,
  uploadFile,
  runCleaning,
  onNewChat,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null)

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      const f = e.dataTransfer.files?.[0]
      if (f && (f.name.endsWith('.csv') || f.type === 'text/csv')) void uploadFile(f)
    },
    [uploadFile],
  )

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
  }, [])

  const openFile = useCallback(() => {
    if (sessionId && !isBusy) fileRef.current?.click()
  }, [sessionId, isBusy])

  const confirmNewChat = useCallback(() => {
    if (window.confirm('确定清空当前对话？已上传的 CSV 将保留。')) onNewChat()
  }, [onNewChat])

  const filePickDisabled = !sessionId || isBusy

  return (
    <section className="data-panel" aria-labelledby="data-panel-title">
      <div className="data-panel__head">
        <h2 id="data-panel-title" className="data-panel__title">
          数据管理
        </h2>
        <button type="button" className="btn btn-ghost data-panel__new-chat" onClick={confirmNewChat} disabled={isBusy || !sessionId}>
          新建对话
        </button>
      </div>

      {sessionId && (
        <p className="data-panel__session" id="data-session-label">
          会话 ID：<code>{sessionId}</code>
        </p>
      )}

      <input
        ref={fileRef}
        id="csv-upload"
        type="file"
        accept=".csv,text/csv"
        className="data-panel__file-hidden"
        disabled={filePickDisabled}
        aria-describedby={sessionId ? 'data-session-label csv-hint' : 'csv-hint'}
        onChange={(e) => void uploadFile(e.target.files?.[0] ?? null)}
      />

      <div
        className={`data-panel__drop${!sessionId ? ' data-panel__drop--off' : ''}`}
        onDrop={sessionId ? onDrop : undefined}
        onDragOver={sessionId ? onDragOver : undefined}
        role={sessionId ? 'button' : undefined}
        tabIndex={sessionId && !isBusy ? 0 : -1}
        aria-label="拖拽 CSV 到此处上传"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            openFile()
          }
        }}
        onClick={openFile}
      >
        <span className="data-panel__drop-title">拖拽 CSV 到此处</span>
        <span className="data-panel__drop-sub">或点击下方按钮选择文件</span>
      </div>

      <div className="data-panel__upload-row">
        <label
          htmlFor="csv-upload"
          className={`btn btn-primary data-panel__upload-btn${filePickDisabled ? ' data-panel__upload-btn--off' : ''}`}
          aria-disabled={filePickDisabled}
        >
          选择 CSV 文件
        </label>
        <button
          type="button"
          className="btn btn-primary data-panel__upload-btn"
          onClick={runCleaning}
          disabled={!uploadReady || isBusy || cleaningDone}
        >
          运行清洗
        </button>
      </div>

      <p id="csv-hint" className="data-panel__hint">
        打开页面时已自动创建会话；仅支持 CSV。上传后请先运行清洗，再在「对话」区提问（窄屏请先切换顶部「对话」Tab）。
      </p>

      {uploadMeta && (
        <div className="data-panel__meta" role="status">
          <p className="data-panel__meta-line">
            <strong>{uploadMeta.fileName}</strong> · {formatBytes(uploadMeta.fileSize)}
          </p>
          <p className="data-panel__meta-line">数据概览：约 {uploadMeta.rows} 条房源记录</p>
        </div>
      )}

      {cleaningDone && cleaningSummary && (
        <details className="data-panel__clean-out">
          <summary>清洗结果摘要（可展开）</summary>
          <pre className="data-panel__clean-pre">{cleaningSummary}</pre>
        </details>
      )}

      {(phase === 'creating' || phase === 'uploading') && (
        <div className="data-panel__skeleton" aria-busy="true">
          <div className="sk-line" />
          <div className="sk-line sk-line--short" />
        </div>
      )}

      {status && (
        <p className={`data-panel__status data-panel__status--${phase === 'running' ? 'run' : 'idle'}`} role="status">
          {status}
        </p>
      )}
    </section>
  )
}
