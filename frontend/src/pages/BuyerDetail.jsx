import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { buyersAPI } from '../services/api'
import { PageLoader } from '../components/shared/LoadingSpinner'
import RiskBadge from '../components/shared/RiskBadge'
import StatCard from '../components/shared/StatCard'
import TenderResults from '../components/search/TenderResults'
import EmptyState from '../components/shared/EmptyState'
import { formatCurrency, formatNumber } from '../services/api'
import {
  Building2, ChevronLeft, ExternalLink, FileText,
  Users, AlertTriangle, Target, TrendingUp
} from 'lucide-react'

const TABS = [
  { key: 'contractors', label: 'Підрядники', icon: Users },
  { key: 'tenders', label: 'Тендери', icon: FileText },
]

export default function BuyerDetail() {
  const { buyerId } = useParams()
  const [tab, setTab] = useState('contractors')
  const [tenderPage, setTenderPage] = useState(1)

  const { data: buyer, loading } = useApi(() => buyersAPI.get(buyerId), [buyerId])
  const { data: contractorsData } = useApi(
    () => buyersAPI.getContractors(buyerId, { limit: 20 }),
    [buyerId]
  )
  const { data: tendersData, loading: tendersLoading } = useApi(
    () => tab === 'tenders'
      ? buyersAPI.getTenders(buyerId, { page: tenderPage, page_size: 15 })
      : Promise.resolve({ data: null }),
    [buyerId, tab, tenderPage]
  )

  if (loading) return <PageLoader />
  if (!buyer) return (
    <div className="max-w-4xl mx-auto px-4 py-16 text-center text-gray-500">
      Замовника не знайдено
    </div>
  )

  const captureScore = contractorsData?.capture_score ?? 0
  const isCaptured = contractorsData?.is_captured

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/search?type=tenders" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ChevronLeft className="w-4 h-4" /> Назад до пошуку
        </Link>
      </div>

      {/* Capture warning banner */}
      {isCaptured && (
        <div className="mb-4 flex items-start gap-3 bg-orange-50 border border-orange-300 rounded-lg px-4 py-3">
          <Target className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-orange-800">
              Підозра на захоплення замовника
            </p>
            <p className="text-xs text-orange-700 mt-0.5">
              {captureScore}% виграшів концентровано в одного підрядника
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Building2 className="w-7 h-7 text-blue-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{buyer.name}</h1>
              <div className="flex flex-wrap items-center gap-3 mt-1">
                {buyer.edrpou && (
                  <span className="text-sm font-mono text-gray-500">ЄДРПОУ: {buyer.edrpou}</span>
                )}
                {buyer.region && <span className="text-sm text-gray-500">{buyer.region}</span>}
                {buyer.buyer_type && (
                  <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full border border-blue-200">
                    {buyer.buyer_type}
                  </span>
                )}
              </div>
            </div>
          </div>
          {buyer.prozorro_id && (
            <a
              href={`https://prozorro.gov.ua/search/tenders?edrpou=${buyer.prozorro_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-sentinel-600 hover:underline flex-shrink-0"
            >
              Prozorro <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Всього тендерів"
          value={formatNumber(buyer.total_tenders)}
          icon={FileText}
          accent="blue"
        />
        <StatCard
          label="Загальна вартість"
          value={formatCurrency(buyer.total_value)}
          icon={TrendingUp}
          accent="green"
        />
        <StatCard
          label="Ризикових тендерів"
          value={`${buyer.high_risk_rate}%`}
          accent={buyer.high_risk_rate >= 30 ? 'red' : buyer.high_risk_rate >= 15 ? 'orange' : 'green'}
        />
        <StatCard
          label="Однобідерних"
          value={`${buyer.single_bidder_rate}%`}
          accent={buyer.single_bidder_rate >= 40 ? 'red' : buyer.single_bidder_rate >= 20 ? 'yellow' : 'green'}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-5">
        <nav className="flex gap-0">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? 'border-sentinel-600 text-sentinel-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Contractors tab */}
      {tab === 'contractors' && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          {/* Capture score bar */}
          {captureScore > 0 && (
            <div className="px-4 pt-4 pb-2 border-b border-gray-100">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span className="flex items-center gap-1">
                  <Target className="w-3.5 h-3.5" /> Концентрація виграшів
                </span>
                <span className={`font-semibold ${captureScore >= 70 ? 'text-red-600' : captureScore >= 50 ? 'text-orange-600' : 'text-gray-600'}`}>
                  {captureScore}%
                </span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${captureScore >= 70 ? 'bg-red-500' : captureScore >= 50 ? 'bg-orange-400' : 'bg-yellow-400'}`}
                  style={{ width: `${captureScore}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Частка виграшів провідного підрядника від загальної кількості виданих контрактів
              </p>
            </div>
          )}

          {contractorsData?.contractors?.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2.5 text-left font-medium">Підрядник</th>
                  <th className="px-4 py-2.5 text-right font-medium">Перемог</th>
                  <th className="px-4 py-2.5 text-right font-medium">Частка</th>
                  <th className="px-4 py-2.5 text-right font-medium">Сума</th>
                  <th className="px-4 py-2.5 text-center font-medium">Ризик</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {contractorsData.contractors.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5">
                      <Link to={`/contractor/${c.id}`} className="font-medium text-sentinel-700 hover:underline">
                        {c.name}
                      </Link>
                      <div className="text-xs text-gray-400 font-mono">{c.edrpou}</div>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{c.wins}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={`text-xs font-medium ${c.share_pct >= 50 ? 'text-red-600' : c.share_pct >= 30 ? 'text-orange-600' : 'text-gray-500'}`}>
                        {c.share_pct}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600 text-xs font-mono whitespace-nowrap">
                      {formatCurrency(c.total_value)}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <RiskBadge category={c.risk_category} score={c.risk_score} showScore />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState icon={Users} title="Підрядників не знайдено" />
          )}
        </div>
      )}

      {/* Tenders tab */}
      {tab === 'tenders' && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <TenderResults
            data={tendersData}
            loading={tendersLoading}
            page={tenderPage}
            onPageChange={setTenderPage}
          />
        </div>
      )}
    </div>
  )
}
