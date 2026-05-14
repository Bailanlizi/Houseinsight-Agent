import { useCallback, useEffect, useState } from 'react'

import { ChatContainer } from './components/ChatContainer'
import { DataPanel } from './components/DataPanel'
import { ErrorBanner } from './components/ErrorBanner'
import { EventLog } from './components/EventLog'
import { Header } from './components/Header'
import { useSessionRun } from './hooks/useSessionRun'
import './App.css'

export default function App() {
  const run = useSessionRun()
  const [draft, setDraft] = useState('')
  const [narrow, setNarrow] = useState(false)
  const [mobileTab, setMobileTab] = useState<'data' | 'chat'>('data')

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1023px)')
    const fn = () => {
      setNarrow(mq.matches)
      if (!mq.matches) setMobileTab('data')
    }
    fn()
    mq.addEventListener('change', fn)
    return () => mq.removeEventListener('change', fn)
  }, [])

  const onSend = useCallback((text: string) => {
    run.sendQuery(text)
  }, [run])

  const onExample = useCallback(
    (text: string) => {
      run.sendQuery(text)
    },
    [run],
  )

  const lastUserForRetry =
    [...run.messages].reverse().find((m) => m.role === 'user')?.content ?? ''

  return (
    <div className="hi-app">
      <Header />

      <ErrorBanner
        message={run.error}
        onDismiss={run.clearError}
        onRetry={lastUserForRetry ? () => run.retryLastQuery() : undefined}
        retryLabel="重试上次问题"
      />

      {narrow && (
        <div className="hi-tabs" role="tablist" aria-label="视图切换">
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === 'data'}
            className={`hi-tabs__btn${mobileTab === 'data' ? ' is-active' : ''}`}
            onClick={() => setMobileTab('data')}
          >
            数据
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === 'chat'}
            className={`hi-tabs__btn${mobileTab === 'chat' ? ' is-active' : ''}`}
            onClick={() => setMobileTab('chat')}
          >
            对话
          </button>
        </div>
      )}

      <div className="hi-layout" data-narrow={narrow ? 'true' : 'false'} data-tab={mobileTab}>
        {(!narrow || mobileTab === 'data') && (
          <aside className="hi-col hi-col--left">
            <DataPanel
              sessionId={run.sessionId}
              phase={run.phase}
              isBusy={run.isFormBusy}
              status={run.status}
              uploadMeta={run.uploadMeta}
              createSession={run.createSession}
              uploadFile={run.uploadFile}
              onNewChat={run.clearConversation}
            />
            <EventLog events={run.events} phase={run.phase} />
          </aside>
        )}

        {(!narrow || mobileTab === 'chat') && (
          <main className="hi-col hi-col--chat">
            <ChatContainer
              messages={run.messages}
              phase={run.phase}
              uploadReady={run.uploadReady}
              isBusy={run.isFormBusy}
              draft={draft}
              onDraftChange={setDraft}
              maxIter={run.maxIter}
              onMaxIterChange={run.setMaxIter}
              onSend={onSend}
              onExample={onExample}
            />
          </main>
        )}
      </div>
    </div>
  )
}
