import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { contractorsAPI } from '../services/api'
import { PageLoader } from '../components/shared/LoadingSpinner'
import RiskBadge, { RiskMeter } from '../components/shared/RiskBadge'
import StatCard from '../components/shared/StatCard'
import AlertCard from '../components/alerts/AlertCard'
import TenderResults from '../components/search/TenderResults'
import EmptyState from '../components/shared/EmptyState'
import { formatCurrency, formatNumber } from '../services/api'
import {
  Building2, AlertTriangle, FileText, GitBranch,
  TrendingUp, ExternalLink, ChevronLeft
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid
} from 'recharts'

const TABS = [
  { key: 'overview', label: 'Огляд', icon: Building2 },
  { key: 'tenders', label: 'Тендери', icon: FileText },
  { key: 'network', label: 'Мережа', icon: GitBranch },
  { key: 'alerts', label: 'Сповіщення', icon: AlertTriangle },
]

export default function ContractorDetail() {
  const { contractorId } = useParams()
  const [tab, setTab] = useState('overview')
  const [tenderPage, setTenderPage] = useState(1)

  const { data: contractor, loading } = useApi(() => contractorsAPI.get(contractorId), [contractorId])
  const { data: riskFactors } = useApi(() => contractorsAPI.getRiskFactors(contractorId), [contractorId])
  const { data: timeline } = useApi(() => contractorsAPI.getTimeline(contractorId), [contractorId])
  const { data: tendersData, loading: tendersLoading } = useApi(
    () => tab === 'tenders' ? contractorsAPI.getTenders(contractorId, { page: tenderPage, page_size: 15 }) : Promise.resolve({ data: null }),
    [contractorId, tab, tenderPage]
  )
  const { data: networkData } = useApi(
    () => tab === 'network' ? contractorsAPI.getNetwork(contractorId, { limit: 20 }) : Promise.resolve({ data: null }),
    [contractorId, tab]
  )

  if (loading) return <PageLoader />
  if (!contractor) return (
    <div className="max-w-4xl mx-auto px-4 py-16 text-center text-gray-500">
      Підрядника не знайдено
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/search" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ChevronLeft className="w-4 h-4" /> Назад до пошуку
        </Link>
      </div>

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-gray-100 rounded-lg">
              <Building2 className="w-7 h-7 text-gray-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{contractor.name}</h1>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                <span className="text-sm font-mono text-gray-500">ЄДРПОУ: {contractor.edrpou}</span>
                {contractor.region && <span className="text-sm text-gray-500">{contractor.region}</span>}
                <RiskBadge category={contractor.risk_category} score={contractor.risk_score} showScore size="lg" />
              </div>
            </div>
          </div>
          <a
            href={`https://prozorro.gov.ua/search/tenders?edrpou=${contractor.edrpou}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm text-sentinel-600 hover:underline flex-shrink-0"
          >
            Prozorro <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Risk meter */}
        <div className="mt-4 max-w-xs">
          <p className="text-xs text-gray-500 mb-1">Рівень ризику</p>
          <RiskMeter score={contractor.risk_score} category={contractor.risk_category} />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Виграних тендерів" value={formatNumber(contractor.total_tenders_won)} icon={FileText} accent="blue" />
        <StatCard label="Всього контрактів" value={formatCurrency(contractor.total_contract_value)} icon={TrendingUp} accent="green" />
        <StatCard label="Частка однобідерних" value={contractor.single_bid_rate != null ? `${(contractor.single_bid_rate * 100).toFixed(0)}%` : '—'} accent={contractor.single_bid_rate > 0.5 ? 'red' : 'yellow'} />
        <StatCard label="Рівень ризику" value={contractor.risk_score?.toFixed(0) ?? '—'} accent={contractor.risk_category === 'critical' ? 'red' : contractor.risk_category === 'high' ? 'orange' : 'green'} />
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

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Risk factors */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Фактори ризику</h2>
            {riskFactors?.factors?.length ? (
              <ul className="space-y-2">
                {riskFactors.factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${
                      f.severity === 'critical' ? 'bg-red-500'
                      : f.severity === 'high' ? 'bg-orange-500'
                      : f.severity === 'medium' ? 'bg-yellow-400'
                      : 'bg-green-500'
                    }`} />
                    <div>
                      <p className="font-medium text-gray-800">{f.label}</p>
                      {f.description && <p className="text-xs text-gray-500">{f.description}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400">Факторів ризику не виявлено</p>
            )}
          </div>

          {/* Timeline chart */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Динаміка тендерів</h2>
            {timeline?.points?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={timeline.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={false}
                    name="Тендери"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={TrendingUp} title="Немає даних" />
            )}
          </div>

          {/* Buyers */}
          {contractor.top_buyers?.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 md:col-span-2">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Основні замовники</h2>
              <div className="grid sm:grid-cols-2 gap-2">
                {contractor.top_buyers.slice(0, 6).map(b => (
                  <div key={b.id} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                    <span className="text-gray-700 truncate">{b.name}</span>
                    <span className="text-xs text-gray-500 ml-2 flex-shrink-0">{formatNumber(b.tender_count)} тенд.</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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

      {tab === 'network' && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Пов'язані підрядники (спільні торги)</h2>
          {networkData?.connections?.length ? (
            <div className="space-y-2">
              {networkData.connections.map(c => (
                <div key={c.contractor_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <Link to={`/contractor/${c.contractor_id}`} className="text-sm font-medium text-sentinel-700 hover:underline">
                      {c.contractor_name}
                    </Link>
                    <p className="text-xs text-gray-500 mt-0.5">Спільних торгів: {c.co_bid_count}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <RiskBadge category={c.risk_category} />
                    <Link
                      to={`/network/${c.contractor_id}`}
                      className="text-xs text-gray-400 hover:text-sentinel-600"
                    >
                      <GitBranch className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={GitBranch} title="Пов'язаних підрядників не знайдено" />
          )}
        </div>
      )}

      {tab === 'alerts' && (
        <div>
          {contractor.alerts?.length ? (
            <div className="space-y-3">
              {contractor.alerts.map(a => <AlertCard key={a.id} alert={a} />)}
            </div>
          ) : (
            <EmptyState icon={AlertTriangle} title="Сповіщень не знайдено" description="Активних ризикових сигналів немає" />
          )}
        </div>
      )}
    </div>
  )
}
