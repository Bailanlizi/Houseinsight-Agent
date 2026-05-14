import { useId, useState } from 'react'

import type { Phase, WsEvent } from '../hooks/useSessionRun'

type Props = {
  events: WsEvent[]
  phase: Phase
}

function eventTone(ev: string): 'node' | 'tool' | 'done' | 'error' | 'default' {
  if (ev === 'node_enter' || ev === 'node_exit') return 'node'
  if (ev === 'tool_call' || ev === 'tool_result') return 'tool'
  if (ev === 'final' || ev === 'done') return 'done'
  if (ev === 'error' || ev === 'parse_error') return 'error'
  return 'default'
}

export function EventLog({ events, phase }: Props) {
  const [open, setOpen] = useState(false)
  const headId = useId()
  const bodyId = useId()
  const live = phase === 'running'

  return (
    <section className="event-log-panel" aria-labelledby={headId}>
      <div className="event-log-panel__head">
        <h2 id={headId} className="event-log-panel__title">
          事件日志
        </h2>
        {live && (
          <span className="event-log-panel__live">
            <span className="event-log-panel__live-dot" aria-hidden />
            Live
          </span>
        )}
        <button
          type="button"
          className="event-log-panel__toggle"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={bodyId}
          aria-label={open ? '折叠日志' : '展开日志'}
        >
          <span className="event-log-panel__toggle-label">{open ? '收起' : '展开'}</span>
          <span className="event-log-panel__chevron" aria-hidden>
            {open ? '▼' : '▶'}
          </span>
        </button>
      </div>

      {open && (
        <div id={bodyId} className="event-log-panel__body">
          {events.length === 0 ? (
            <p className="event-log-panel__empty" role="status">
              分析开始后，此处显示节点与工具事件。
            </p>
          ) : (
            <div
              className="event-log-panel__scroll"
              role="region"
              aria-live="polite"
              aria-relevant="additions"
              aria-label="事件列表"
            >
              <ul className="event-log-panel__list">
                {events.map((e, i) => {
                  const ev = String(e.event ?? 'event')
                  const tone = eventTone(ev)
                  return (
                    <li key={i} className="event-log-panel__row" data-tone={tone}>
                      <span className="event-log-panel__ev">{ev}</span>
                      {e.node != null && <span className="event-log-panel__meta"> · {String(e.node)}</span>}
                      {e.tool != null && <span className="event-log-panel__meta"> · {String(e.tool)}</span>}
                      {e.ok != null && (
                        <span className={`event-log-panel__ok event-log-panel__ok--${e.ok ? 'y' : 'n'}`}>
                          {' '}
                          · {e.ok ? '成功' : '失败'}
                        </span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
