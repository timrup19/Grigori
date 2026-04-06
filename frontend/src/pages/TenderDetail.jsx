import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { tendersAPI } from '../services/api'
import { PageLoader } from '../components/shared/LoadingSpinner'
import RiskBadge from '../components/shared/RiskBadge'
import { formatCurrency } from '../services/api'
import {
  FileText, ChevronLeft, Building2, ExternalLink,
  AlertTriangle, Users, Clock, TrendingUp
} from 'lucide-react'

const STATUS_LABELS = {
  active: 'Активний', complete: 'Завершений',
  cancelled: 'Скасований', unsuccessful: 'Невдалий',
}
const STATUS_STYLES = {
  active: 'text-green-700 bg-green-50 border-green-200',
  complete: 'text-blue-700 bg-blue-50 border-blue-200',
  cancelled: 'text-gray-600 bg-gray-100 border-gray-200',
  unsuccessful: 'text-red-700 bg-red-50 border-red-200',
}

const FLAG_LABELS = {
  is_single_bidder: 'Єдиний учасник',
  is_price_anomaly: 'Цінова аномалія',
  is_bid_pattern_anomaly: 'Аномальний патерн ставок',
}

export default function TenderDetail() {
  const { tenderId } = useParams()
  const { data: tender, loading } = useApi(() => tendersAPI.get(tenderId), [tenderId])

  if (loading) return <PageLoader />
  if (!tender) return (
    <div className="max-w-4xl mx-auto px-4 py-16 text-center text-gray-500">
      Тендер не знайдено
    </div>
  )

  const activeFlags = ['is_single_bidder', 'is_price_anomaly', 'is_bid_pattern_anomaly']
    .filter(f => tender[f])

  const windowDays = tender.tender_start_date && tender.tender_end_date
    ? Math.round((new Date(tender.tender_end_date) - new Date(tender.tender_start_date)) / 86400000)
    : null

  const awardGapPct = tender.expected_value && tender.award_value
    ? ((parseFloat(tender.award_value) - parseFloat(tender.expected_value)) / parseFloat(tender.expected_value) * 100)
    : null

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/search?type=tenders" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ChevronLeft className="w-4 h-4" /> Назад до пошуку
        </Link>
      </div>

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 mb-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 bg-gray-100 rounded-lg flex-shrink-0">
              <FileText className="w-6 h-6 text-gray-500" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-snug">{tender.title}</h1>
              <div className="flex flex-wrap items-center gap-3 mt-1.5">
                <span className="text-xs font-mono text-gray-400">{tender.prozorro_id}</span>
                {tender.cpv_code && (
                  <span className="text-xs text-gray-500">CPV: {tender.cpv_code}</span>
                )}
                {tender.region && <span className="text-xs text-gray-500">{tender.region}</span>}
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_STYLES[tender.status] || 'text-gray-600 bg-gray-100 border-gray-200'}`}>
                  {STATUS_LABELS[tender.status] || tender.status}
                </span>
              </div>
            </div>
          </div>
          <a
            href={`https://prozorro.gov.ua/tender/${tender.prozorro_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-sentinel-600 hover:underline flex-shrink-0"
          >
            Prozorro <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Value row */}
        <div className="mt-4 flex flex-wrap gap-6">
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Очікувана вартість</p>
            <p className="text-lg font-semibold text-gray-900">{formatCurrency(tender.expected_value)}</p>
          </div>
          {tender.award_value && (
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Сума контракту</p>
              <p className={`text-lg font-semibold ${awardGapPct !== null && Math.abs(awardGapPct) > 20 ? 'text-orange-600' : 'text-gray-900'}`}>
                {formatCurrency(tender.award_value)}
                {awardGapPct !== null && (
                  <span className="ml-1.5 text-sm font-normal text-gray-400">
                    ({awardGapPct > 0 ? '+' : ''}{awardGapPct.toFixed(0)}%)
                  </span>
                )}
              </p>
            </div>
          )}
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Учасників</p>
            <p className="text-lg font-semibold text-gray-900">{tender.num_bids}</p>
          </div>
          {windowDays !== null && (
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Термін подачі</p>
              <p className={`text-lg font-semibold ${windowDays < 7 ? 'text-orange-600' : 'text-gray-900'}`}>
                {windowDays} дн.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-5">
        {/* Left col */}
        <div className="md:col-span-2 space-y-5">
          {/* Risk panel */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Оцінка ризику</h2>
              <RiskBadge category={tender.risk_category} score={tender.risk_score} showScore size="lg" />
            </div>

            {activeFlags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {activeFlags.map(f => (
                  <span key={f} className="inline-flex items-center gap-1 text-xs bg-red-50 text-red-700 border border-red-200 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-3 h-3" /> {FLAG_LABELS[f]}
                  </span>
                ))}
              </div>
            )}

            {tender.risk_reasons?.length > 0 ? (
              <ul className="space-y-1.5">
                {tender.risk_reasons.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0 mt-1.5" />
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400">Конкретних сигналів не виявлено</p>
            )}
          </div>

          {/* Bids table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-700">Учасники торгів</h2>
            </div>
            {tender.bids?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-2.5 text-left font-medium">Підрядник</th>
                    <th className="px-4 py-2.5 text-right font-medium">Пропозиція</th>
                    <th className="px-4 py-2.5 text-center font-medium">Результат</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tender.bids.map(b => (
                    <tr key={b.id} className={b.is_winner ? 'bg-green-50' : ''}>
                      <td className="px-4 py-2.5">
                        {b.contractor_id ? (
                          <Link to={`/contractor/${b.contractor_id}`} className="text-sentinel-700 hover:underline font-medium">
                            {b.contractor_name}
                          </Link>
                        ) : (
                          <span className="text-gray-700">{b.contractor_name || '—'}</span>
                        )}
                        {b.contractor_edrpou && (
                          <span className="ml-2 text-xs text-gray-400 font-mono">{b.contractor_edrpou}</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-700 font-mono text-xs">
                        {b.bid_value ? formatCurrency(b.bid_value) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {b.is_winner ? (
                          <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded-full font-medium">Переможець</span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-gray-400 px-4 py-6 text-center">Дані про учасників відсутні</p>
            )}
          </div>

          {/* Description */}
          {tender.description && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Опис</h2>
              <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line line-clamp-6">{tender.description}</p>
            </div>
          )}
        </div>

        {/* Right col */}
        <div className="space-y-5">
          {/* Buyer */}
          {tender.buyer && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                <Building2 className="w-4 h-4" /> Замовник
              </h2>
              <Link to={`/buyer/${tender.buyer_id}`} className="text-sm font-medium text-sentinel-700 hover:underline">
                {tender.buyer.name}
              </Link>
              {tender.buyer.region && <p className="text-xs text-gray-500 mt-0.5">{tender.buyer.region}</p>}
            </div>
          )}

          {/* Winner */}
          {tender.winner && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4" /> Переможець
              </h2>
              <Link to={`/contractor/${tender.winner.id}`} className="text-sm font-medium text-sentinel-700 hover:underline">
                {tender.winner.name}
              </Link>
              <p className="text-xs text-gray-400 font-mono mt-0.5">{tender.winner.edrpou}</p>
              {tender.winner.risk_category && (
                <div className="mt-2">
                  <RiskBadge category={tender.winner.risk_category} score={tender.winner.risk_score} showScore />
                </div>
              )}
            </div>
          )}

          {/* Dates */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
              <Clock className="w-4 h-4" /> Дати
            </h2>
            <dl className="space-y-1.5 text-sm">
              {tender.tender_start_date && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Початок</dt>
                  <dd className="text-gray-700">{new Date(tender.tender_start_date).toLocaleDateString('uk-UA')}</dd>
                </div>
              )}
              {tender.tender_end_date && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Кінець</dt>
                  <dd className={`${windowDays !== null && windowDays < 7 ? 'text-orange-600 font-medium' : 'text-gray-700'}`}>
                    {new Date(tender.tender_end_date).toLocaleDateString('uk-UA')}
                  </dd>
                </div>
              )}
              {tender.award_date && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Присудження</dt>
                  <dd className="text-gray-700">{new Date(tender.award_date).toLocaleDateString('uk-UA')}</dd>
                </div>
              )}
              {tender.date_modified && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Оновлено</dt>
                  <dd className="text-gray-400 text-xs">{new Date(tender.date_modified).toLocaleDateString('uk-UA')}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
