import type { Phase } from '../hooks/useSessionRun'

type Props = {
  phase: Phase
  uploadReady: boolean
  cleaningDone: boolean
  status: string
}

/** 窄屏「对话」Tab 顶部：当前数据/清洗/运行状态（只读） */
export function SessionStatusBar({ phase, uploadReady, cleaningDone, status }: Props) {
  let line = ''
  if (!uploadReady) {
    line = '请先在「数据」Tab 上传 CSV'
  } else if (!cleaningDone) {
    line = phase === 'running' ? '清洗或分析进行中…' : '请在「数据」Tab 点击「运行清洗」'
  } else if (phase === 'running') {
    line = '分析进行中…'
  } else {
    line = '可以提问'
  }

  return (
    <div className="session-status-bar" role="status">
      <p className="session-status-bar__main">{line}</p>
      {status ? <p className="session-status-bar__detail">{status}</p> : null}
    </div>
  )
}
