import { useCallback, useId } from 'react'
import type { KeyboardEvent } from 'react'

type Props = {
  disabled: boolean
  busy: boolean
  uploadReady: boolean
  onSend: (text: string) => void
  value: string
  onChange: (v: string) => void
  maxIter: number
  onMaxIterChange: (v: number) => void
}

export function ChatInput({
  disabled,
  busy,
  uploadReady,
  onSend,
  value,
  onChange,
  maxIter,
  onMaxIterChange,
}: Props) {
  const hintId = useId()

  const submit = useCallback(() => {
    const t = value.trim()
    if (t && !disabled) onSend(t)
  }, [value, disabled, onSend])

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        submit()
      }
    },
    [submit],
  )

  return (
    <div className="chat-input">
      <details className="chat-input__advanced">
        <summary className="chat-input__advanced-sum">高级 · 最大迭代</summary>
        <div className="chat-input__advanced-row">
          <label htmlFor="chat-input-max-iter" className="chat-input__label">
            次数
          </label>
          <input
            id="chat-input-max-iter"
            type="number"
            min={1}
            max={50}
            value={maxIter}
            onChange={(e) => onMaxIterChange(Number(e.target.value) || 15)}
            disabled={disabled || busy}
            className="chat-input__num"
          />
        </div>
      </details>
      <div className="chat-input__row">
        <label htmlFor="chat-input-field" className="visually-hidden">
          分析问题
        </label>
        <textarea
          id="chat-input-field"
          className="chat-input__textarea"
          rows={2}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled || busy}
          placeholder={uploadReady ? '输入您的分析问题…' : '请先上传房源 CSV 后再提问'}
          aria-describedby={hintId}
        />
        <button
          type="button"
          className="chat-input__send btn-send"
          disabled={disabled || busy || !value.trim()}
          aria-busy={busy}
          onClick={submit}
          aria-label="发送"
        >
          <span className="btn-send__icon" aria-hidden />
        </button>
      </div>
      <p id={hintId} className="chat-input__hint">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  )
}
