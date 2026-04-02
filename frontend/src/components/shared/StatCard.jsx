import { TrendingUp, TrendingDown } from 'lucide-react'

export default function StatCard({ label, value, sub, icon: Icon, trend, trendLabel, accent }) {
  const accentColor = {
    red:    'border-t-red-500',
    orange: 'border-t-orange-500',
    yellow: 'border-t-yellow-500',
    green:  'border-t-green-500',
    blue:   'border-t-sentinel-500',
  }[accent] || 'border-t-transparent'

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm p-4 border-t-2 ${accentColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-500 truncate">{label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 truncate">{value ?? '—'}</p>
          {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
          {trend != null && (
            <div className={`mt-1 flex items-center gap-1 text-xs ${trend >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {trend >= 0
                ? <TrendingUp className="w-3 h-3" />
                : <TrendingDown className="w-3 h-3" />}
              <span>{trendLabel || `${Math.abs(trend)}%`}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="ml-3 flex-shrink-0 p-2 bg-gray-50 rounded-lg">
            <Icon className="w-5 h-5 text-gray-400" />
          </div>
        )}
      </div>
    </div>
  )
}
