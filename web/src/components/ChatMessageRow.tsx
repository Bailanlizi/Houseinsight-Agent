import { useCallback, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import type { ChatMessage } from '../hooks/useSessionRun'

const COLLAPSE_CHARS = 1400

type Props = {
  message: ChatMessage
}

export function ChatMessageRow({ message }: Props) {
  const isUser = message.role === 'user'
  const long = message.content.length > COLLAPSE_CHARS
  const [expanded, setExpanded] = useState(!long)

  const toggle = useCallback(() => setExpanded((e) => !e), [])

  return (
    <div className={`chat-msg chat-msg--${message.role}`}>
      {!isUser && (
        <div className="chat-msg__avatar" aria-hidden title="AI">
          AI
        </div>
      )}
      <div className="chat-msg__bubble-wrap">
        <div
          className={`chat-msg__bubble${long && !expanded ? ' chat-msg__bubble--clamped' : ''}`}
          role={isUser ? undefined : 'article'}
        >
          {isUser ? (
            <div className="chat-msg__text-user">{message.content}</div>
          ) : (
            <div className="chat-msg__md">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {long && (
          <button type="button" className="chat-msg__expand" onClick={toggle}>
            {expanded ? '收起' : '展开全文'}
          </button>
        )}
      </div>
    </div>
  )
}
