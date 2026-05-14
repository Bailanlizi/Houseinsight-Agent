import { ExampleCard } from './ExampleCard'

const EXAMPLES = [
  '帮我找温江区 100 万以内的三居室',
  '哪些房源采光最好？',
  '分析各区域的平均房价',
]

type Props = {
  onExample: (text: string) => void
  disabled?: boolean
  uploadReady: boolean
  cleaningDone: boolean
}

export function EmptyState({ onExample, disabled, uploadReady, cleaningDone }: Props) {
  const lead = !uploadReady
    ? '请先上传您的房源 CSV 文件'
    : !cleaningDone
      ? '请在左侧点击「运行清洗」，完成数据预处理'
      : '上传您的房源数据，开始智能分析之旅'

  const hint = cleaningDone ? '试试以下示例问题：' : '完成清洗后即可使用示例或自行提问。'

  return (
    <div className="empty-state-chat" role="region" aria-label="开始引导">
      <p className="empty-state-chat__lead">{lead}</p>
      <p className="empty-state-chat__hint">{hint}</p>
      <div className="empty-state-chat__examples">
        {EXAMPLES.map((t) => (
          <ExampleCard key={t} text={t} onPick={onExample} disabled={disabled} />
        ))}
      </div>
    </div>
  )
}
