import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { AlertTriangle, Building2, FileText, TrendingUp, GitBranch, Map } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { statsAPI, alertsAPI } from '../services/api'
import StatCard from '../components/shared/StatCard'
import { PageLoader } from '../components/shared/LoadingSpinner'
import AlertCard from '../components/alerts/AlertCard'
import SearchBar from '../components/search/SearchBar'
import { formatNumber, formatCurrency } from '../services/api'
import { Link } from 'react-router-dom'

export default function Home() {
  const [searchQ, setSearchQ] = useState('')
  const navigate = useNavigate()

  const { data: overview, loading: overviewLoading } = useApi(() => statsAPI.overview(), [])
  const { data: latestAlerts, loading: alertsLoading } = useApi(() => alertsAPI.latest(5), [])
  const { data: riskDist } = useApi(() => statsAPI.riskDistribution(), [])

  function handleSearch(q) {
    if (q?.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Prozorro Sentinel
        </h1>
        <p className="text-gray-500 mb-6 max-w-xl mx-auto">
          Аналіз ризиків державних закупівель України. Виявлення корупційних схем у даних Prozorro.
        </p>
        <div className="max-w-xl mx-auto">
          <SearchBar
            value={searchQ}
            onChange={setSearchQ}
            onSearch={handleSearch}
            placeholder="Пошук підрядника, тендера або замовника…"
            autoFocus
          />
        </div>
      </div>

      {/* Stats */}
      {overviewLoading ? (
        <PageLoader />
      ) : overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Підрядники"
            value={formatNumber(overview.total_contractors)}
            icon={Building2}
            accent="blue"
          />
          <StatCard
            label="Тендери"
            value={formatNumber(overview.total_tenders)}
            icon={FileText}
            accent="blue"
          />
          <StatCard
            label="Загальна вартість"
            value={formatCurrency(overview.total_value)}
            icon={TrendingUp}
            accent="green"
          />
          <StatCard
            label="Активних сповіщень"
            value={formatNumber(overview.active_alerts)}
            icon={AlertTriangle}
            accent="red"
          />
        </div>
      )}

      {/* Risk distribution bar */}
      {riskDist && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Розподіл ризиків підрядників</h2>
          <div className="flex rounded-full overflow-hidden h-3">
            {['critical', 'high', 'medium', 'low'].map((cat) => {
              const item = riskDist.find(r => r.category === cat)
              const pct = item ? item.percentage : 0
              const colors = { critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-400', low: 'bg-green-500' }
              return <div key={cat} className={`${colors[cat]} transition-all`} style={{ width: `${pct}%` }} title={`${cat}: ${pct.toFixed(1)}%`} />
            })}
          </div>
          <div className="flex gap-4 mt-2">
            {['critical', 'high', 'medium', 'low'].map((cat) => {
              const item = riskDist.find(r => r.category === cat)
              const labels = { critical: 'Критичний', high: 'Високий', medium: 'Середній', low: 'Низький' }
              const dots = { critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-400', low: 'bg-green-500' }
              return (
                <div key={cat} className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className={`w-2 h-2 rounded-full ${dots[cat]}`} />
                  {labels[cat]} {item ? `${item.percentage.toFixed(0)}%` : ''}
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        {/* Recent alerts */}
        <div className="md:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-800">Останні червоні прапори</h2>
            <Link to="/alerts" className="text-sm text-sentinel-600 hover:underline">Всі сповіщення →</Link>
          </div>
          {alertsLoading ? (
            <PageLoader />
          ) : latestAlerts?.length ? (
            <div className="space-y-3">
              {latestAlerts.map(a => <AlertCard key={a.id} alert={a} />)}
            </div>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">Сповіщень немає</p>
          )}
        </div>

        {/* Quick links */}
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Інструменти</h2>
          {[
            { to: '/alerts', icon: AlertTriangle, label: 'Червоні прапори', desc: 'Активні ризикові сигнали', color: 'text-red-500' },
            { to: '/network', icon: GitBranch, label: 'Мережа зв\'язків', desc: 'Аналіз спільних торгів', color: 'text-purple-500' },
            { to: '/map', icon: Map, label: 'Карта ризиків', desc: 'Регіональний розподіл', color: 'text-blue-500' },
          ].map(({ to, icon: Icon, label, desc, color }) => (
            <Link key={to} to={to} className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:shadow-sm hover:border-sentinel-200 transition-all">
              <div className="p-2 bg-gray-50 rounded-lg">
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">{label}</p>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
