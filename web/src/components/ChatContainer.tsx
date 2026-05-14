import { useEffect, useRef } from 'react'

import type { ChatMessage, Phase } from '../hooks/useSessionRun'

import { ChatInput } from './ChatInput'
import { ChatMessageRow } from './ChatMessageRow'
import { EmptyState } from './EmptyState'

type Props = {
  messages: ChatMessage[]
  phase: Phase
  uploadReady: boolean
  cleaningDone: boolean
  isBusy: boolean
  draft: string
  onDraftChange: (v: string) => void
  maxIter: number
  onMaxIterChange: (v: number) => void
  onSend: (text: string) => void
  onExample: (text: string) => void
}

export function ChatContainer({
  messages,
  phase,
  uploadReady,
  cleaningDone,
  isBusy,
  draft,
  onDraftChange,
  maxIter,
  onMaxIterChange,
  onSend,
  onExample,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const showTyping =
    phase === 'running' &&
    cleaningDone &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === 'user'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, phase, showTyping])

  const empty = messages.length === 0
  const canChat = uploadReady && cleaningDone && !isBusy

  return (
    <section className="chat-container" aria-label="对话">
      <div className="chat-container__scroll" role="log" aria-live="polite" aria-relevant="additions">
        {empty ? (
          <EmptyState
            onExample={onExample}
            disabled={!canChat}
            uploadReady={uploadReady}
            cleaningDone={cleaningDone}
          />
        ) : (
          <ul className="chat-container__list">
            {messages.map((m) => (
              <li key={m.id} className="chat-container__item">
                <ChatMessageRow message={m} />
              </li>
            ))}
          </ul>
        )}
        {showTyping && (
          <div className="chat-typing" role="status" aria-label="AI 正在回复">
            <span className="chat-typing__dot" />
            <span className="chat-typing__dot" />
            <span className="chat-typing__dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput
        disabled={!canChat}
        busy={phase === 'running' && cleaningDone}
        uploadReady={uploadReady}
        cleaningDone={cleaningDone}
        value={draft}
        onChange={onDraftChange}
        maxIter={maxIter}
        onMaxIterChange={onMaxIterChange}
        onSend={(t) => {
          onSend(t)
          onDraftChange('')
        }}
      />
    </section>
  )
}
