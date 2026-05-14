type Props = {
  uploadReady: boolean
  cleaningDone: boolean
}

/** 三步：上传 CSV → 运行清洗 → 可提问（仅用边框/字重区分） */
export function WorkflowSteps({ uploadReady, cleaningDone }: Props) {
  return (
    <nav className="hi-workflow" aria-label="使用步骤">
      <ol className="hi-workflow__list">
        <li
          className={`hi-workflow__step${uploadReady ? ' hi-workflow__step--done' : ''}${!uploadReady ? ' hi-workflow__step--current' : ''}`}
        >
          <span className="hi-workflow__idx" aria-hidden>
            1
          </span>
          <span className="hi-workflow__label">上传 CSV</span>
        </li>
        <li
          className={`hi-workflow__step${cleaningDone ? ' hi-workflow__step--done' : ''}${uploadReady && !cleaningDone ? ' hi-workflow__step--current' : ''}`}
        >
          <span className="hi-workflow__idx" aria-hidden>
            2
          </span>
          <span className="hi-workflow__label">运行清洗</span>
        </li>
        <li
          className={`hi-workflow__step${cleaningDone ? ' hi-workflow__step--done hi-workflow__step--current' : ''}`}
        >
          <span className="hi-workflow__idx" aria-hidden>
            3
          </span>
          <span className="hi-workflow__label">自然语言分析</span>
        </li>
      </ol>
    </nav>
  )
}
