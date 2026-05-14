type Props = {
  hasSession: boolean
  hasUpload: boolean
  hasResult: boolean
}

/** 纯展示：三步进度说明，配合 aria-current 标出当前步 */
export function SessionStepper({ hasSession, hasUpload, hasResult }: Props) {
  const step = !hasSession ? 1 : !hasUpload ? 2 : 3

  return (
    <nav className="stepper" aria-label="分析流程步骤">
      <ol className="stepper__list">
        <li className="stepper__item" aria-current={step === 1 ? 'step' : undefined}>
          <span className="stepper__num" aria-hidden>
            1
          </span>
          创建会话
        </li>
        <li className="stepper__item" aria-current={step === 2 ? 'step' : undefined}>
          <span className="stepper__num" aria-hidden>
            2
          </span>
          上传 CSV
        </li>
        <li className="stepper__item" aria-current={step === 3 ? 'step' : undefined}>
          <span className="stepper__num" aria-hidden>
            3
          </span>
          开始分析
        </li>
      </ol>
      {hasResult && (
        <p className="stepper__hint" role="status">
          已有分析结果，可再次运行以更新。
        </p>
      )}
    </nav>
  )
}
