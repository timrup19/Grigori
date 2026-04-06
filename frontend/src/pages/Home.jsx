import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  AlertTriangle, Building2, FileText, TrendingUp,
  GitBranch, Map, RefreshCw, Users
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { statsAPI, alertsAPI } from '../services/api'
import StatCard from '../components/shared/StatCard'
import { PageLoader } from '../components/shared/LoadingSpinner'
import AlertCard from '../components/alerts/AlertCard'
import RiskBadge from '../components/shared/RiskBadge'
import SearchBar from '../components/search/SearchBar'
import { formatNumber, formatCurrency } from '../services/api'
import { Link } from 'react-router-dom'
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts'

const RISK_COLORS = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-400',
  low: 'bg-green-500',
}
const RISK_LABELS = {
  critical: 'Критичний', high: 'Високий', medium: 'Середній', low: 'Низький',
}

function formatTrendDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('uk-UA', { day: 'numeric', month: 'short' })
}

function timeAgo(dateStr) {
  if (!dateStr) return null
  const diff = Date.now() - new Date(dateStr)
  const h = Math.floor(diff / 3600000)
  if (h < 1) return 'щойно'
  if (h < 24) return `${h}г тому`
  const d = Math.floor(h / 24)
  return `${d}д тому`
}

export default function Home() {
  const [searchQ, setSearchQ] = useState('')
  const navigate = useNavigate()

  const { data: overview, loading: overviewLoading } = useApi(() => statsAPI.overview(), [])
  const { data: latestAlerts, loading: alertsLoading } = useApi(() => alertsAPI.latest(8), [])
  const { data: trendsData } = useApi(() => statsAPI.trends('30d'), [])
  const { data: topRiskData } = useApi(() => statsAPI.topContractors('risk', 6), [])

  // Build risk distribution data
  const riskDist = (() => {
    if (!overview) return null
    const total = (overview.low_risk_count ?? 0) + (overview.medium_risk_count ?? 0) +
      (overview.high_risk_count ?? 0) + (overview.critical_risk_count ?? 0)
    if (!total) return null
    return [
      { category: 'critical', count: overview.critical_risk_count ?? 0, pct: ((overview.critical_risk_count ?? 0) / total) * 100 },
      { category: 'high',     count: overview.high_risk_count ?? 0,     pct: ((overview.high_risk_count ?? 0) / total) * 100 },
      { category: 'medium',   count: overview.medium_risk_count ?? 0,   pct: ((overview.medium_risk_count ?? 0) / total) * 100 },
      { category: 'low',      count: overview.low_risk_count ?? 0,      pct: ((overview.low_risk_count ?? 0) / total) * 100 },
    ]
  })()

  // Merge trend series into chart-ready rows
  const trendPoints = (() => {
    if (!trendsData?.tenders?.length) return []
    const map = {}
    trendsData.tenders.forEach(p => { map[p.date] = { date: p.date, total: p.count, high_risk: 0 } })
    trendsData.high_risk?.forEach(p => { if (map[p.date]) map[p.date].high_risk = p.count })
    return Object.values(map)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(p => ({ ...p, label: formatTrendDate(p.date) }))
  })()

  function handleSearch(q) {
    if (q?.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Grigori</h1>
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

      {/* Main stats */}
      {overviewLoading ? <PageLoader /> : overview && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
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
              sub={overview.tenders_last_24h > 0 ? `+${formatNumber(overview.tenders_last_24h)} сьогодні` : null}
            />
            <StatCard
              label="Загальна вартість"
              value={formatCurrency(overview.total_value)}
              icon={TrendingUp}
              accent="green"
            />
            <StatCard
              label="Активних сповіщень"
              value={formatNumber(overview.total_alerts)}
              icon={AlertTriangle}
              accent="red"
              sub={overview.alerts_last_24h > 0 ? `+${formatNumber(overview.alerts_last_24h)} сьогодні` : null}
              trend={overview.alerts_last_24h > 0 ? overview.alerts_last_24h : null}
              trendLabel={`+${overview.alerts_last_24h} за 24г`}
            />
          </div>

          {/* Secondary metrics */}
          <div className="flex flex-wrap items-center gap-4 mb-6 px-1">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700">
                {overview.single_bidder_rate != null
                  ? `${(overview.single_bidder_rate * 100).toFixed(1)}%`
                  : '—'}
              </span>
              однобідерних тендерів
            </div>
            <span className="text-gray-300">·</span>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700">
                {overview.avg_bids_per_tender != null
                  ? overview.avg_bids_per_tender.toFixed(1)
                  : '—'}
              </span>
              середня кількість учасників
            </div>
            {overview.last_sync && (
              <>
                <span className="text-gray-300">·</span>
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Оновлено {timeAgo(overview.last_sync)}
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* Risk distribution bar */}
      {riskDist && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Розподіл ризиків тендерів</h2>
          <div className="flex rounded-full overflow-hidden h-3 mb-2">
            {riskDist.map(({ category, pct }) => (
              <div
                key={category}
                className={`${RISK_COLORS[category]} transition-all`}
                style={{ width: `${pct}%` }}
                title={`${RISK_LABELS[category]}: ${pct.toFixed(1)}%`}
              />
            ))}
          </div>
          <div className="flex gap-4 flex-wrap">
            {riskDist.map(({ category, count, pct }) => (
              <div key={category} className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className={`w-2 h-2 rounded-full ${RISK_COLORS[category]}`} />
                {RISK_LABELS[category]} — {formatNumber(count)} ({pct.toFixed(0)}%)
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trends chart */}
      {trendPoints.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Динаміка тендерів за 30 днів</h2>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trendPoints} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradRisk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 6 }}
                formatter={(val, name) => [
                  formatNumber(val),
                  name === 'total' ? 'Всього тендерів' : 'Ризикових',
                ]}
                labelFormatter={l => l}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#gradTotal)"
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="high_risk"
                stroke="#ef4444"
                strokeWidth={2}
                fill="url(#gradRisk)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-1">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-3 h-0.5 bg-blue-500 inline-block" /> Всього тендерів
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-3 h-0.5 bg-red-500 inline-block" /> Ризикових (≥50)
            </div>
          </div>
        </div>
      )}

      {/* Bottom grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Recent alerts — 2 cols */}
        <div className="md:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-800">Останні червоні прапори</h2>
            <Link to="/alerts" className="text-sm text-sentinel-600 hover:underline">Всі →</Link>
          </div>
          {alertsLoading ? (
            <PageLoader />
          ) : latestAlerts?.alerts?.length ? (
            <div className="space-y-3">
              {latestAlerts.alerts.map(a => <AlertCard key={a.id} alert={a} />)}
            </div>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">Сповіщень немає</p>
          )}
        </div>

        {/* Right col */}
        <div className="space-y-5">
          {/* Top risky contractors */}
          {topRiskData?.contractors?.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-gray-800">Найризиковіші підрядники</h2>
                <Link to="/search?sort=risk" className="text-sm text-sentinel-600 hover:underline">Всі →</Link>
              </div>
              <div className="space-y-2">
                {topRiskData.contractors.slice(0, 5).map(c => (
                  <Link
                    key={c.id}
                    to={`/contractor/${c.id}`}
                    className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:shadow-sm hover:border-sentinel-200 transition-all"
                  >
                    <div className="min-w-0 flex-1 mr-3">
                      <p className="text-sm font-medium text-gray-800 truncate">{c.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{c.edrpou}</p>
                    </div>
                    <RiskBadge category={c.risk_category} score={c.risk_score} showScore />
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Quick links */}
          <div>
            <h2 className="text-base font-semibold text-gray-800 mb-3">Інструменти</h2>
            <div className="space-y-2">
              {[
                { to: '/alerts', icon: AlertTriangle, label: 'Червоні прапори', desc: 'Активні ризикові сигнали', color: 'text-red-500' },
                { to: '/network', icon: GitBranch, label: 'Мережа зв\'язків', desc: 'Аналіз спільних торгів', color: 'text-purple-500' },
                { to: '/map', icon: Map, label: 'Карта ризиків', desc: 'Регіональний розподіл', color: 'text-blue-500' },
              ].map(({ to, icon: Icon, label, desc, color }) => (
                <Link
                  key={to}
                  to={to}
                  className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:shadow-sm hover:border-sentinel-200 transition-all"
                >
                  <div className="p-2 bg-gray-50 rounded-lg flex-shrink-0">
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
      </div>
    </div>
  )
}
