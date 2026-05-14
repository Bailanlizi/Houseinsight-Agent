type Props = {
  text: string
  onPick: (text: string) => void
  disabled?: boolean
}

export function ExampleCard({ text, onPick, disabled }: Props) {
  return (
    <button
      type="button"
      className="example-card"
      disabled={disabled}
      onClick={() => onPick(text)}
    >
      <span className="example-card__icon" aria-hidden />
      {text}
    </button>
  )
}
