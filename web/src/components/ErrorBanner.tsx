type Props = {
  message: string | null
  onDismiss: () => void
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorBanner({ message, onDismiss, onRetry, retryLabel = '重试分析' }: Props) {
  if (!message) return null

  return (
    <div className="error-banner" role="alert">
      <p className="error-banner__text">{message}</p>
      <div className="error-banner__actions">
        {onRetry && (
          <button type="button" className="btn btn--secondary" onClick={onRetry}>
            {retryLabel}
          </button>
        )}
        <button type="button" className="btn btn--ghost" onClick={onDismiss}>
          关闭
        </button>
      </div>
    </div>
  )
}
