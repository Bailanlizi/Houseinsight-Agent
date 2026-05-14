export function Header() {
  return (
    <header className="hi-header">
      <div className="hi-header__inner">
        <span className="hi-header__mark" aria-hidden>
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="4" width="40" height="40" rx="12" fill="url(#hi-house-grad)" />
            <path
              d="M24 14L14 21.5V34h7v-6.5h6V34h7V21.5L24 14z"
              stroke="#FEFBF6"
              strokeWidth="2"
              strokeLinejoin="round"
              fill="none"
            />
            <rect x="20" y="27" width="8" height="7" rx="1" fill="#FEFBF6" fillOpacity="0.4" />
            <defs>
              <linearGradient id="hi-house-grad" x1="10" y1="8" x2="38" y2="42" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F5C77A" />
                <stop offset="1" stopColor="#D9914A" />
              </linearGradient>
            </defs>
          </svg>
        </span>
        <div>
          <h1 className="hi-header__title">HouseInsight Agent</h1>
          <p className="hi-header__subtitle">上传数据，用自然语言探索房源信息</p>
        </div>
      </div>
    </header>
  )
}
