import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { searchAPI } from '../services/api'
import SearchBar from '../components/search/SearchBar'
import ContractorResults from '../components/search/ContractorResults'
import TenderResults from '../components/search/TenderResults'
import { SlidersHorizontal } from 'lucide-react'

const TABS = [
  { key: 'contractors', label: 'Підрядники' },
  { key: 'tenders', label: 'Тендери' },
]

const RISK_OPTIONS = ['', 'critical', 'high', 'medium', 'low']
const RISK_LABELS = { '': 'Всі', critical: 'Критичний', high: 'Високий', medium: 'Середній', low: 'Низький' }

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState(searchParams.get('type') === 'tenders' ? 'tenders' : 'contractors')
  const [q, setQ] = useState(searchParams.get('q') || '')
  const [riskFilter, setRiskFilter] = useState('')
  const [page, setPage] = useState(1)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const doSearch = useCallback(async (query, activeTab, riskCat, pg) => {
    if (!query.trim()) { setResults(null); return }
    setLoading(true)
    try {
      const params = { q: query, page: pg, page_size: 20 }
      if (riskCat) params.risk_category = riskCat
      const fn = activeTab === 'tenders' ? searchAPI.tenders : searchAPI.contractors
      const res = await fn(params)
      setResults(res.data)
    } catch (e) {
      setResults(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    doSearch(q, tab, riskFilter, page)
  }, [q, tab, riskFilter, page, doSearch])

  function handleSearch(newQ) {
    setQ(newQ)
    setPage(1)
    setSearchParams(newQ ? { q: newQ, type: tab } : {})
  }

  function handleTabChange(newTab) {
    setTab(newTab)
    setPage(1)
    setResults(null)
  }

  function handleRiskChange(val) {
    setRiskFilter(val)
    setPage(1)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Пошук</h1>
        <SearchBar value={q} onChange={setQ} onSearch={handleSearch} autoFocus />
      </div>

      {/* Tabs + filters */}
      <div className="flex items-center justify-between border-b border-gray-200 mb-4">
        <div className="flex gap-0">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => handleTabChange(t.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-sentinel-600 text-sentinel-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
              {results && tab === t.key && (
                <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
                  {results.total}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Risk filter */}
        <div className="flex items-center gap-2 pb-2">
          <SlidersHorizontal className="w-4 h-4 text-gray-400" />
          <select
            value={riskFilter}
            onChange={e => handleRiskChange(e.target.value)}
            className="text-sm border border-gray-200 rounded-md py-1 pl-2 pr-6 text-gray-600 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
          >
            {RISK_OPTIONS.map(r => (
              <option key={r} value={r}>{RISK_LABELS[r]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        {tab === 'contractors' ? (
          <ContractorResults data={results} loading={loading} page={page} onPageChange={setPage} />
        ) : (
          <TenderResults data={results} loading={loading} page={page} onPageChange={setPage} />
        )}
      </div>

      {!q.trim() && (
        <p className="text-center text-gray-400 text-sm mt-8">
          Введіть пошуковий запит для початку
        </p>
      )}
    </div>
  )
}
