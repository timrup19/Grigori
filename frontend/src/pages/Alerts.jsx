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

const DAYS_OPTIONS = [
  { value: 7,  label: '7 днів' },
  { value: 30, label: '30 днів' },
  { value: 90, label: '90 днів' },
]

export default function Alerts() {
  const [page, setPage] = useState(1)
  const [riskFilter, setRiskFilter] = useState('')
  const [days, setDays] = useState(90)

  const { data: stats } = useApi(() => alertsAPI.stats(days), [days])
  const { data: alertsData, loading } = useApi(
    () => alertsAPI.list({
      page,
      page_size: 20,
      days,
      min_risk_score: 0,
      risk_category: riskFilter || undefined,
    }),
    [page, riskFilter, days]
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
          <StatCard label={`Всього (${days}д)`} value={formatNumber(stats.total_alerts)} icon={Bell} accent="red" />
          <StatCard label="Критичних" value={formatNumber(stats.critical_count)} accent="red" />
          <StatCard label="Високих" value={formatNumber(stats.high_count)} accent="orange" />
          <StatCard label="Середніх" value={formatNumber(stats.medium_count)} icon={AlertTriangle} accent="yellow" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={days}
          onChange={e => { setDays(Number(e.target.value)); setPage(1) }}
          className="text-sm border border-gray-200 rounded-md py-1.5 pl-3 pr-7 text-gray-600 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
        >
          {DAYS_OPTIONS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>
        <select
          value={riskFilter}
          onChange={handleFilterChange(setRiskFilter)}
          className="text-sm border border-gray-200 rounded-md py-1.5 pl-3 pr-7 text-gray-600 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
        >
          {RISK_OPTIONS.map(r => <option key={r} value={r}>{RISK_LABELS[r]}</option>)}
        </select>
        {alertsData && (
          <span className="text-sm text-gray-400 self-center">{formatNumber(alertsData.total)} сповіщень</span>
        )}
      </div>

      {/* List */}
      {loading ? (
        <PageLoader />
      ) : alertsData?.results?.length ? (
        <div className="space-y-3">
          {alertsData.results.map(a => <AlertCard key={a.id} alert={a} />)}
          <Pagination page={page} totalPages={alertsData.total_pages} onPageChange={setPage} />
        </div>
      ) : (
        <EmptyState
          icon={AlertTriangle}
          title="Сповіщень не знайдено"
          description="Спробуйте збільшити часовий діапазон або змінити фільтри"
        />
      )}
    </div>
  )
}
