import { ErrorBanner } from './components/ErrorBanner'
import { EventLog } from './components/EventLog'
import { FinalAnswerPanel } from './components/FinalAnswerPanel'
import { SessionStepper } from './components/SessionStepper'
import { useSessionRun } from './hooks/useSessionRun'
import './App.css'

export default function App() {
  const run = useSessionRun()

  return (
    <div className="app">
      <header className="header">
        <h1>HouseInsight Agent</h1>
        <p className="header__lede">上传 CSV，输入分析目标，通过 WebSocket 查看实时进度与最终回答。</p>
      </header>

      <ErrorBanner
        message={run.error}
        onDismiss={run.clearError}
        onRetry={run.uploadReady ? run.startRun : undefined}
        retryLabel="重试分析"
      />

      <SessionStepper
        hasSession={!!run.sessionId}
        hasUpload={run.uploadReady}
        hasResult={run.finalAnswer.trim().length > 0}
      />

      {(run.phase === 'creating' || run.phase === 'uploading') && (
        <div className="skeleton-block" aria-busy="true" aria-label="请求处理中">
          <div className="skeleton skeleton--line" />
          <div className="skeleton skeleton--line skeleton--short" />
        </div>
      )}

      <form
        id="analysis-workflow-form"
        className="workflow-form"
        aria-busy={run.isFormBusy}
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
        }}
      >
        <fieldset className="fieldset" disabled={run.isFormBusy}>
          <legend className="visually-hidden">分析工作流</legend>

          <section className="panel" aria-labelledby="step-create-heading">
            <h2 id="step-create-heading" className="panel__title">
              步骤 1：会话
            </h2>
            <div className="panel__row">
              <button type="button" onClick={() => void run.createSession()}>
                创建会话
              </button>
              {run.sessionId && (
                <p className="panel__meta" id="session-id-label">
                  当前会话 ID：<code>{run.sessionId}</code>
                </p>
              )}
            </div>
          </section>

          <section className="panel" aria-labelledby="step-upload-heading">
            <h2 id="step-upload-heading" className="panel__title">
              步骤 2：数据文件
            </h2>
            <div className="panel__row">
              <label htmlFor="csv-upload" className="label">
                选择 CSV 文件
              </label>
              <input
                id="csv-upload"
                type="file"
                accept=".csv,text/csv"
                disabled={!run.sessionId || run.isFormBusy}
                aria-describedby="session-id-label csv-upload-hint"
                onChange={(e) => void run.uploadFile(e.target.files?.[0] ?? null)}
              />
              <p id="csv-upload-hint" className="hint">
                需先创建会话；仅支持 .csv。
              </p>
            </div>
          </section>

          <section className="panel" aria-labelledby="step-run-heading">
            <h2 id="step-run-heading" className="panel__title">
              步骤 3：目标与运行
            </h2>
            <div className="panel__stack">
              <label htmlFor="analysis-goal" className="label">
                分析目标
              </label>
              <textarea
                id="analysis-goal"
                value={run.goal}
                onChange={(e) => run.setGoal(e.target.value)}
                rows={3}
                disabled={run.isFormBusy}
                aria-describedby="goal-hint"
              />
              <p id="goal-hint" className="hint">
                用自然语言描述你希望从数据中得到的信息。
              </p>

              <label htmlFor="analysis-max-iter" className="label">
                最大迭代次数
              </label>
              <input
                id="analysis-max-iter"
                type="number"
                min={1}
                max={50}
                value={run.maxIter}
                onChange={(e) => run.setMaxIter(Number(e.target.value) || 15)}
                disabled={run.isFormBusy}
                aria-describedby="iter-hint"
              />
              <p id="iter-hint" className="hint">
                限制 Agent 循环次数，防止过长运行（默认 15）。
              </p>

              <button
                type="button"
                disabled={!run.sessionId || run.isFormBusy}
                aria-busy={run.phase === 'running'}
                onClick={run.startRun}
              >
                开始分析（WebSocket）
              </button>
            </div>
          </section>
        </fieldset>
      </form>

      <p className={`status-line ${run.status ? 'status-line--visible' : ''}`} role="status">
        {run.status || '\u00a0'}
      </p>

      <div className="split">
        <EventLog events={run.events} />
        <FinalAnswerPanel text={run.finalAnswer} />
      </div>
    </div>
  )
}
