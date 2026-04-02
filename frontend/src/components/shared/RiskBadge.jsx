const STYLES = {
  critical: 'bg-red-100 text-red-800 border border-red-200',
  high:     'bg-orange-100 text-orange-800 border border-orange-200',
  medium:   'bg-yellow-100 text-yellow-800 border border-yellow-200',
  low:      'bg-green-100 text-green-800 border border-green-200',
}

const LABELS = {
  critical: 'Критичний',
  high:     'Високий',
  medium:   'Середній',
  low:      'Низький',
}

export default function RiskBadge({ category, score, showScore = false, size = 'sm' }) {
  const base = size === 'lg'
    ? 'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold'
    : 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium'

  const style = STYLES[category] || 'bg-gray-100 text-gray-600 border border-gray-200'
  const label = LABELS[category] || 'Невідомо'

  return (
    <span className={`${base} ${style}`}>
      {label}
      {showScore && score != null && (
        <span className="opacity-70 font-normal">·{Math.round(score)}</span>
      )}
    </span>
  )
}

/** Horizontal risk score meter bar */
export function RiskMeter({ score, category }) {
  const fill = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-green-500',
  }[category] || 'bg-gray-400'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${fill}`}
          style={{ width: `${Math.min(100, score || 0)}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-500 w-8 text-right">
        {score != null ? Math.round(score) : '—'}
      </span>
    </div>
  )
}
