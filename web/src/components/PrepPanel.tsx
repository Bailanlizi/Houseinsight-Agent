import { useState } from 'react'

import type { Phase, UploadMeta, WsEvent } from '../hooks/useSessionRun'

import { DataPanel } from './DataPanel'
import { EventLog } from './EventLog'

type PrepSub = 'data' | 'log'

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
  events: WsEvent[]
}

export function PrepPanel(props: Props) {
  const [sub, setSub] = useState<PrepSub>('data')

  return (
    <div className="prep-panel">
      <div className="prep-panel__tabs" role="tablist" aria-label="数据与日志">
        <button
          type="button"
          role="tab"
          aria-selected={sub === 'data'}
          className={`prep-panel__tab${sub === 'data' ? ' is-active' : ''}`}
          onClick={() => setSub('data')}
        >
          数据
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sub === 'log'}
          className={`prep-panel__tab${sub === 'log' ? ' is-active' : ''}`}
          onClick={() => setSub('log')}
        >
          事件日志
        </button>
      </div>
      <div className="prep-panel__scroll">
        {sub === 'data' ? (
          <DataPanel
            sessionId={props.sessionId}
            phase={props.phase}
            isBusy={props.isBusy}
            status={props.status}
            uploadMeta={props.uploadMeta}
            uploadReady={props.uploadReady}
            cleaningDone={props.cleaningDone}
            cleaningSummary={props.cleaningSummary}
            uploadFile={props.uploadFile}
            runCleaning={props.runCleaning}
            onNewChat={props.onNewChat}
          />
        ) : (
          <EventLog events={props.events} phase={props.phase} fillHeight />
        )}
      </div>
    </div>
  )
}
