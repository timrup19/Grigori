import { useState, useMemo } from 'react'
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
  TrendingUp, ExternalLink, ChevronLeft, ShieldAlert, UserCheck,
  Users, Search as SearchIcon, Target, RotateCcw
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

const ROLE_LABELS = {
  director: 'Директор',
  founder: 'Засновник',
  signatory: 'Підписант',
  beneficial_owner: 'Бенефіціарний власник',
}

function roleLabel(role) {
  return ROLE_LABELS[role] || role || 'Посадова особа'
}

export default function ContractorDetail() {
  const { contractorId } = useParams()
  const [tab, setTab] = useState('overview')
  const [tenderPage, setTenderPage] = useState(1)

  const { data: contractor, loading } = useApi(() => contractorsAPI.get(contractorId), [contractorId])
  const { data: enrichment } = useApi(() => contractorsAPI.getEnrichment(contractorId), [contractorId])
  const { data: riskFactors } = useApi(() => contractorsAPI.getRiskFactors(contractorId), [contractorId])
  const { data: timeline } = useApi(() => contractorsAPI.getTimeline(contractorId), [contractorId])
  const { data: buyersData } = useApi(() => contractorsAPI.getBuyers(contractorId), [contractorId])
  const { data: captureData } = useApi(() => contractorsAPI.getCaptureAnalysis(contractorId), [contractorId])
  const { data: rotationData } = useApi(() => contractorsAPI.getBidRotation(contractorId), [contractorId])
  const { data: tendersData, loading: tendersLoading } = useApi(
    () => tab === 'tenders' ? contractorsAPI.getTenders(contractorId, { page: tenderPage, page_size: 15 }) : Promise.resolve({ data: null }),
    [contractorId, tab, tenderPage]
  )
  const { data: networkData } = useApi(
    () => tab === 'network' ? contractorsAPI.getNetwork(contractorId, { limit: 20 }) : Promise.resolve({ data: null }),
    [contractorId, tab]
  )

  // Transform timeline events → monthly point buckets for the chart
  const timelinePoints = useMemo(() => {
    if (!timeline?.events?.length) return []
    const counts = {}
    timeline.events.forEach(e => {
      if (!e.date) return
      const d = new Date(e.date)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      counts[key] = (counts[key] || 0) + 1
    })
    return Object.entries(counts).sort().map(([period, count]) => ({ period, count }))
  }, [timeline])

  // Transform risk factors object → sorted display array
  const RISK_FACTOR_LABELS = {
    price_anomaly: 'Цінова аномалія',
    bid_pattern: 'Патерн ставок',
    single_bidder: 'Єдиний учасник',
    network_risk: 'Мережевий ризик',
    high_value: 'Висока вартість',
    short_window: 'Короткий термін подачі',
    award_gap: 'Аномалія суми контракту',
  }
  const riskFactorItems = useMemo(() => {
    if (!riskFactors?.factors || typeof riskFactors.factors !== 'object') return []
    return Object.entries(riskFactors.factors)
      .filter(([, v]) => v?.occurrences > 0)
      .map(([key, v]) => ({
        key,
        label: RISK_FACTOR_LABELS[key] || key,
        avg_score: v.avg_score || 0,
        occurrences: v.occurrences || 0,
        severity: v.avg_score >= 0.75 ? 'critical' : v.avg_score >= 0.5 ? 'high' : v.avg_score >= 0.25 ? 'medium' : 'low',
      }))
      .sort((a, b) => b.avg_score - a.avg_score)
  }, [riskFactors])

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

      {/* Sanctions / PEP banners */}
      {enrichment?.is_sanctioned && (
        <div className="mb-4 flex items-start gap-3 bg-red-50 border border-red-300 rounded-lg px-4 py-3">
          <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">
              Підрядник фігурує у міжнародних санкційних списках
            </p>
            <ul className="mt-1 space-y-0.5">
              {enrichment.sanctions_hits.filter(h => !h.is_pep).map((hit, i) => (
                <li key={i} className="text-xs text-red-700">
                  {hit.name} — {hit.datasets.join(', ')} (збіг: {(hit.score * 100).toFixed(0)}%)
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {enrichment?.is_pep && (
        <div className="mb-4 flex items-start gap-3 bg-orange-50 border border-orange-300 rounded-lg px-4 py-3">
          <UserCheck className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-orange-800">
              Підрядник пов'язаний з публічною посадовою особою (PEP)
            </p>
            <ul className="mt-1 space-y-0.5">
              {enrichment.sanctions_hits.filter(h => h.is_pep).map((hit, i) => (
                <li key={i} className="text-xs text-orange-700">
                  {hit.name} — {hit.datasets.join(', ')} (збіг: {(hit.score * 100).toFixed(0)}%)
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

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

        {enrichment?.enriched_at && (
          <p className="mt-3 text-xs text-gray-400">
            Санкційна перевірка: {new Date(enrichment.enriched_at).toLocaleDateString('uk-UA')} · Джерело: OpenSanctions{enrichment.directors_fetched_at ? ', ЄДР' : ''}
          </p>
        )}
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
            {riskFactorItems.length ? (
              <ul className="space-y-2">
                {riskFactorItems.map((f) => (
                  <li key={f.key} className="flex items-start gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${
                      f.severity === 'critical' ? 'bg-red-500'
                      : f.severity === 'high' ? 'bg-orange-500'
                      : f.severity === 'medium' ? 'bg-yellow-400'
                      : 'bg-green-500'
                    }`} />
                    <div>
                      <p className="font-medium text-gray-800">{f.label}</p>
                      <p className="text-xs text-gray-500">{f.occurrences} тенд. · середній бал {(f.avg_score * 100).toFixed(0)}</p>
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
            {timelinePoints.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={timelinePoints}>
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
          {buyersData?.buyers?.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 md:col-span-2">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Основні замовники</h2>
              <div className="grid sm:grid-cols-2 gap-2">
                {buyersData.buyers.slice(0, 6).map(b => (
                  <div key={b.id} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                    <Link to={`/buyer/${b.id}`} className="text-sentinel-700 hover:underline truncate">{b.name}</Link>
                    <span className="text-xs text-gray-500 ml-2 flex-shrink-0">{formatNumber(b.tender_count)} тенд.</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Buyer-contractor capture analysis */}
          {captureData?.capture_score >= 30 && captureData.top_buyers?.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <Target className="w-4 h-4" /> Концентрація виграшів
                </h2>
                {captureData.is_flagged && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium bg-red-100 text-red-800 border border-red-300 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-3 h-3" /> Захоплення замовника
                  </span>
                )}
              </div>
              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Частка головного замовника</span>
                  <span className={`font-semibold ${captureData.capture_score >= 70 ? 'text-red-600' : captureData.capture_score >= 50 ? 'text-orange-600' : 'text-yellow-600'}`}>
                    {captureData.capture_score}%
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${captureData.capture_score >= 70 ? 'bg-red-500' : captureData.capture_score >= 50 ? 'bg-orange-400' : 'bg-yellow-400'}`}
                    style={{ width: `${captureData.capture_score}%` }}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                {captureData.top_buyers.slice(0, 5).map(b => (
                  <div key={b.id} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                    <Link to={`/buyer/${b.id}`} className="text-sentinel-700 hover:underline truncate flex-1">{b.name}</Link>
                    <div className="flex items-center gap-3 ml-2 flex-shrink-0">
                      <span className="text-xs text-gray-500">{b.wins} перемог</span>
                      <span className={`text-xs font-medium ${b.share_pct >= 50 ? 'text-red-600' : b.share_pct >= 30 ? 'text-orange-600' : 'text-gray-500'}`}>
                        {b.share_pct}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bid rotation detection */}
          {rotationData?.rotation_suspects?.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <RotateCcw className="w-4 h-4" /> Аналіз ротації торгів
                </h2>
                {rotationData.is_flagged && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium bg-orange-100 text-orange-800 border border-orange-300 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-3 h-3" /> Підозра на картель
                  </span>
                )}
              </div>
              <div className="space-y-2">
                {rotationData.rotation_suspects.map(s => (
                  <div key={s.partner_id} className={`p-3 rounded-lg border ${s.balance_score >= 0.5 ? 'border-orange-200 bg-orange-50' : 'border-gray-100 bg-gray-50'}`}>
                    <div className="flex items-center justify-between">
                      <Link to={`/contractor/${s.partner_id}`} className="text-sm font-medium text-sentinel-700 hover:underline truncate">
                        {s.partner_name}
                      </Link>
                      <RiskBadge category={s.risk_category} score={s.risk_score} />
                    </div>
                    <div className="mt-1.5 flex items-center gap-4 text-xs text-gray-500">
                      <span>Спільних виграшів: <strong>{s.shared_wins}</strong></span>
                      <span>Ми: <strong>{s.our_wins}</strong></span>
                      <span>Партнер: <strong>{s.partner_wins}</strong></span>
                      <span className={`font-medium ${s.balance_score >= 0.5 ? 'text-orange-700' : 'text-gray-500'}`}>
                        Баланс: {(s.balance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <span className="text-xs text-gray-400 font-mono">{s.partner_edrpou}</span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-400">Баланс &gt;50% між двома підрядниками вказує на можливу ротацію</p>
            </div>
          )}

          {/* Company Officers (EDR) */}
          {(enrichment?.directors?.length > 0 || enrichment?.edr_status === 'dissolved') && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <Users className="w-4 h-4" /> Посадові особи компанії
                </h2>
                {enrichment.edr_status === 'dissolved' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-800 border border-amber-300 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-3 h-3" /> Компанію ліквідовано
                  </span>
                )}
              </div>
              {enrichment.directors.length > 0 ? (
                <ul className="space-y-1.5">
                  {enrichment.directors.map((d, i) => (
                    <li key={i} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                      <Link
                        to={`/search?q=${encodeURIComponent(d.full_name)}`}
                        className="flex items-center gap-1.5 text-sentinel-700 hover:underline"
                      >
                        <SearchIcon className="w-3.5 h-3.5 flex-shrink-0" />
                        {d.full_name}
                      </Link>
                      <span className="text-xs text-gray-500 ml-2 flex-shrink-0">{roleLabel(d.role)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">Дані відсутні</p>
              )}
              {enrichment.directors_fetched_at && (
                <p className="mt-2 text-xs text-gray-400">
                  Джерело: ЄДР · Оновлено: {new Date(enrichment.directors_fetched_at).toLocaleDateString('uk-UA')}
                </p>
              )}
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
