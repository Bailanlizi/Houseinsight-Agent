import { ExampleCard } from './ExampleCard'

const EXAMPLES = [
  '帮我找温江区 100 万以内的三居室',
  '哪些房源采光最好？',
  '分析各区域的平均房价',
]

type Props = {
  onExample: (text: string) => void
  disabled?: boolean
}

export function EmptyState({ onExample, disabled }: Props) {
  return (
    <div className="empty-state-chat" role="region" aria-label="开始引导">
      <p className="empty-state-chat__lead">上传您的房源数据，开始智能分析之旅</p>
      <p className="empty-state-chat__hint">试试以下示例问题：</p>
      <div className="empty-state-chat__examples">
        {EXAMPLES.map((t) => (
          <ExampleCard key={t} text={t} onPick={onExample} disabled={disabled} />
        ))}
      </div>
    </div>
  )
}
