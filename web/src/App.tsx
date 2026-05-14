import { useCallback, useEffect, useState } from 'react'

import { ChatContainer } from './components/ChatContainer'
import { ErrorBanner } from './components/ErrorBanner'
import { Header } from './components/Header'
import { PrepPanel } from './components/PrepPanel'
import { WorkflowSteps } from './components/WorkflowSteps'
import { useSessionRun } from './hooks/useSessionRun'
import './App.css'

export default function App() {
  const run = useSessionRun()
  const [draft, setDraft] = useState('')
  const [narrow, setNarrow] = useState(false)
  const [mobileTab, setMobileTab] = useState<'data' | 'chat'>('data')
  const [dismissChatTabHint, setDismissChatTabHint] = useState(false)

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

  useEffect(() => {
    if (!narrow || mobileTab !== 'data') setDismissChatTabHint(false)
  }, [narrow, mobileTab])

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

  const canRetry =
    !!run.error &&
    (!run.sessionId || (!run.cleaningDone && run.uploadReady) || !!lastUserForRetry)

  const showChatTabSnack =
    narrow &&
    mobileTab === 'data' &&
    run.uploadReady &&
    run.cleaningDone &&
    !dismissChatTabHint

  return (
    <div className="hi-app">
      <Header />

      <div className="hi-shell">
        <ErrorBanner
          message={run.error}
          onDismiss={run.clearError}
          onRetry={
            canRetry
              ? () => {
                  run.clearError()
                  if (!run.sessionId) void run.fetchNewSession()
                  else if (!run.cleaningDone && run.uploadReady) run.runCleaning()
                  else if (lastUserForRetry) run.retryLastQuery()
                }
              : undefined
          }
          retryLabel={
            !run.sessionId
              ? '重试创建会话'
              : !run.cleaningDone && run.uploadReady
                ? '重试清洗'
                : lastUserForRetry
                  ? '重试上次问题'
                  : '重试'
          }
        />

        <WorkflowSteps uploadReady={run.uploadReady} cleaningDone={run.cleaningDone} />

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

        {showChatTabSnack && (
          <div className="hi-chat-hint-snack" role="status">
            <span className="hi-chat-hint-snack__text">数据已就绪，可切换到「对话」提问</span>
            <button type="button" className="btn btn-ghost hi-chat-hint-snack__btn" onClick={() => setDismissChatTabHint(true)}>
              知道了
            </button>
          </div>
        )}

        <div className="hi-layout" data-narrow={narrow ? 'true' : 'false'} data-tab={mobileTab}>
          {(!narrow || mobileTab === 'data') && (
            <aside className="hi-col hi-col--left">
              <PrepPanel
                sessionId={run.sessionId}
                phase={run.phase}
                isBusy={run.isFormBusy}
                status={run.status}
                uploadMeta={run.uploadMeta}
                uploadReady={run.uploadReady}
                cleaningDone={run.cleaningDone}
                cleaningSummary={run.cleaningSummary}
                uploadFile={run.uploadFile}
                runCleaning={run.runCleaning}
                onNewChat={run.clearConversation}
                events={run.events}
              />
            </aside>
          )}

          {(!narrow || mobileTab === 'chat') && (
            <main className="hi-col hi-col--chat">
              <ChatContainer
                messages={run.messages}
                phase={run.phase}
                uploadReady={run.uploadReady}
                cleaningDone={run.cleaningDone}
                status={run.status}
                showSessionStatusBar={narrow}
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
    </div>
  )
}
