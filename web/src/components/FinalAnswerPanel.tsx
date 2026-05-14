type Props = {
  text: string
}

export function FinalAnswerPanel({ text }: Props) {
  const empty = !text.trim()

  return (
    <section className="answer-panel" aria-labelledby="answer-heading">
      <h2 id="answer-heading">最终回答</h2>
      {empty ? (
        <p className="empty-state" role="status">
          分析完成后，模型生成的结论文本将显示在此处。
        </p>
      ) : (
        <pre className="answer-panel__body">{text}</pre>
      )}
    </section>
  )
}
