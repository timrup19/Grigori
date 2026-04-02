import { AlertTriangle, Clock, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import RiskBadge from '../shared/RiskBadge'
import { formatCurrency } from '../../services/api'

const ALERT_TYPE_LABELS = {
  single_bidder:      'Один учасник',
  price_anomaly:      'Цінова аномалія',
  co_bidding_network: 'Мережа спільних торгів',
  repeated_winner:    'Повторний переможець',
  split_procurement:  'Дроблення закупівлі',
}

const ALERT_TYPE_COLORS = {
  single_bidder:      'bg-orange-50 border-orange-200 text-orange-700',
  price_anomaly:      'bg-red-50 border-red-200 text-red-700',
  co_bidding_network: 'bg-purple-50 border-purple-200 text-purple-700',
  repeated_winner:    'bg-yellow-50 border-yellow-200 text-yellow-700',
  split_procurement:  'bg-blue-50 border-blue-200 text-blue-700',
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr)
  const h = Math.floor(diff / 3600000)
  if (h < 1) return 'Щойно'
  if (h < 24) return `${h}г тому`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}д тому`
  return new Date(dateStr).toLocaleDateString('uk-UA')
}

export default function AlertCard({ alert, compact = false }) {
  const typeStyle = ALERT_TYPE_COLORS[alert.alert_type] || 'bg-gray-50 border-gray-200 text-gray-700'
  const typeLabel = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type

  if (compact) {
    return (
      <div className="flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors">
        <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{alert.tender_title}</p>
          <p className="text-xs text-gray-500 mt-0.5">{alert.buyer_name}</p>
        </div>
        <RiskBadge category={alert.risk_category} />
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${typeStyle}`}>
              {typeLabel}
            </span>
            <RiskBadge category={alert.risk_category} score={alert.risk_score} showScore />
          </div>

          <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 mb-1">
            {alert.tender_title}
          </h3>

          <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            <span>{alert.buyer_name}</span>
            {alert.expected_value && (
              <span className="font-medium text-gray-700">{formatCurrency(alert.expected_value)}</span>
            )}
            {alert.contractor_name && (
              <Link
                to={`/contractor/${alert.contractor_id}`}
                className="text-sentinel-600 hover:underline"
              >
                {alert.contractor_name}
              </Link>
            )}
          </div>

          {alert.reasons?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {alert.reasons.map((r, i) => (
                <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-red-400 flex-shrink-0 mt-1.5" />
                  {r}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <Clock className="w-3 h-3" />
            {timeAgo(alert.created_at)}
          </div>
          {alert.tender_prozorro_id && (
            <a
              href={`https://prozorro.gov.ua/tender/${alert.tender_prozorro_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-sentinel-600 hover:underline flex items-center gap-1"
            >
              Prozorro <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
