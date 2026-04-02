import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { alertsAPI } from '../services/api'
import AlertCard from '../components/alerts/AlertCard'
import StatCard from '../components/shared/StatCard'
import { PageLoader } from '../components/shared/LoadingSpinner'
import Pagination from '../components/shared/Pagination'
import EmptyState from '../components/shared/EmptyState'
import { AlertTriangle, Bell } from 'lucide-react'
import { formatNumber } from '../services/api'

const RISK_OPTIONS = ['', 'critical', 'high', 'medium', 'low']
const RISK_LABELS = { '': 'Всі', critical: 'Критичний', high: 'Високий', medium: 'Середній', low: 'Низький' }

const TYPE_OPTIONS = ['', 'single_bidder', 'price_anomaly', 'co_bidding_network', 'repeated_winner', 'split_procurement']
const TYPE_LABELS = {
  '': 'Всі типи',
  single_bidder: 'Один учасник',
  price_anomaly: 'Цінова аномалія',
  co_bidding_network: 'Мережа торгів',
  repeated_winner: 'Повторний переможець',
  split_procurement: 'Дроблення',
}

export default function Alerts() {
  const [page, setPage] = useState(1)
  const [riskFilter, setRiskFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const { data: stats } = useApi(() => alertsAPI.stats(7), [])
  const { data: alertsData, loading } = useApi(
    () => alertsAPI.list({ page, page_size: 20, risk_category: riskFilter || undefined, alert_type: typeFilter || undefined }),
    [page, riskFilter, typeFilter]
  )

  function handleFilterChange(setter) {
    return (e) => { setter(e.target.value); setPage(1) }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Червоні прапори</h1>
        <p className="text-gray-500 text-sm">Автоматично виявлені ризики в даних Prozorro</p>
      </div>

      {/* Stats strip */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Нові (7 днів)" value={formatNumber(stats.new_last_7_days)} icon={Bell} accent="red" />
          <StatCard label="Критичних" value={formatNumber(stats.by_category?.critical)} accent="red" />
          <StatCard label="Високих" value={formatNumber(stats.by_category?.high)} accent="orange" />
          <StatCard label="Всього активних" value={formatNumber(stats.total_active)} icon={AlertTriangle} accent="yellow" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={riskFilter}
          onChange={handleFilterChange(setRiskFilter)}
          className="text-sm border border-gray-200 rounded-md py-1.5 pl-3 pr-7 text-gray-600 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
        >
          {RISK_OPTIONS.map(r => <option key={r} value={r}>{RISK_LABELS[r]}</option>)}
        </select>
        <select
          value={typeFilter}
          onChange={handleFilterChange(setTypeFilter)}
          className="text-sm border border-gray-200 rounded-md py-1.5 pl-3 pr-7 text-gray-600 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
        >
          {TYPE_OPTIONS.map(t => <option key={t} value={t}>{TYPE_LABELS[t]}</option>)}
        </select>
        {alertsData && (
          <span className="text-sm text-gray-400 self-center">{formatNumber(alertsData.total)} сповіщень</span>
        )}
      </div>

      {/* List */}
      {loading ? (
        <PageLoader />
      ) : alertsData?.items?.length ? (
        <div className="space-y-3">
          {alertsData.items.map(a => <AlertCard key={a.id} alert={a} />)}
          <Pagination page={page} totalPages={alertsData.total_pages} onPageChange={setPage} />
        </div>
      ) : (
        <EmptyState
          icon={AlertTriangle}
          title="Сповіщень не знайдено"
          description="Спробуйте змінити фільтри"
        />
      )}
    </div>
  )
}
