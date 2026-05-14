import type { WsEvent } from '../hooks/useSessionRun'

type Props = {
  events: WsEvent[]
}

export function EventLog({ events }: Props) {
  return (
    <section className="event-log" aria-labelledby="event-log-heading">
      <h2 id="event-log-heading">事件流</h2>
      {events.length === 0 ? (
        <p className="empty-state" role="status">
          尚无事件。创建会话、上传数据并开始分析后，此处将显示节点与工具调用进度。
        </p>
      ) : (
        <div
          className="event-log__live"
          role="region"
          aria-live="polite"
          aria-relevant="additions"
          aria-label="实时分析事件"
        >
          <ul className="event-log__list">
            {events.map((e, i) => (
              <li key={i} className="event-log__row">
                <span className="event-log__type">{String(e.event)}</span>
                {e.node != null && <span className="event-log__meta"> · 节点 {String(e.node)}</span>}
                {e.tool != null && <span className="event-log__meta"> · 工具 {String(e.tool)}</span>}
                {e.ok != null && (
                  <span className="event-log__meta"> · {e.ok ? '成功' : '失败'}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
