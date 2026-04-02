import { useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'
import { useApi } from '../hooks/useApi'
import { regionsAPI } from '../services/api'
import { PageLoader } from '../components/shared/LoadingSpinner'
import RiskBadge from '../components/shared/RiskBadge'
import { formatCurrency, formatNumber } from '../services/api'
import { Map as MapIcon, X } from 'lucide-react'

// Ukraine ISO numeric code = 804
const UKRAINE_CODE = '804'
// World atlas topojson — reliable CDN, always available
const WORLD_TOPO = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

function scoreToCategory(score) {
  if (score == null) return null
  if (score >= 75) return 'critical'
  if (score >= 50) return 'high'
  if (score >= 25) return 'medium'
  return 'low'
}

function riskColor(category) {
  return {
    critical: '#ef4444',
    high:     '#f97316',
    medium:   '#eab308',
    low:      '#22c55e',
  }[category] || '#94a3b8'
}

export default function MapView() {
  const [selected, setSelected] = useState(null)
  const { data: regions, loading } = useApi(() => regionsAPI.list(), [])
  const { data: regionDetail, loading: detailLoading } = useApi(
    () => selected ? regionsAPI.get(selected.region) : Promise.resolve({ data: null }),
    [selected?.region]
  )

  if (loading) return <PageLoader />

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Карта ризиків</h1>
        <p className="text-gray-500 text-sm">Регіональний розподіл ризиків держзакупівель</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <div className="bg-sky-50 rounded-lg overflow-hidden border border-gray-100">
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 2800, center: [31, 49] }}
              width={600}
              height={360}
              style={{ width: '100%', height: 'auto' }}
            >
              <ZoomableGroup zoom={1}>
                {/* Ukraine country outline from world-atlas */}
                <Geographies geography={WORLD_TOPO}>
                  {({ geographies }) =>
                    geographies
                      .filter(geo => geo.id === UKRAINE_CODE)
                      .map(geo => (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          style={{
                            default: { fill: '#e2e8f0', stroke: '#94a3b8', strokeWidth: 0.5, outline: 'none' },
                            hover:   { fill: '#e2e8f0', stroke: '#94a3b8', strokeWidth: 0.5, outline: 'none' },
                            pressed: { outline: 'none' },
                          }}
                        />
                      ))
                  }
                </Geographies>

                {/* Region markers */}
                {(regions || []).filter(r => r.latitude && r.longitude).map(r => {
                  const cat = scoreToCategory(r.avg_risk_score)
                  const isSelected = selected?.region === r.region
                  return (
                    <Marker key={r.region} coordinates={[r.longitude, r.latitude]}>
                      <circle
                        r={isSelected ? 11 : 7}
                        fill={riskColor(cat)}
                        fillOpacity={0.85}
                        stroke={isSelected ? '#1e3a8a' : '#fff'}
                        strokeWidth={isSelected ? 2.5 : 1.5}
                        onClick={() => setSelected(r)}
                        style={{ cursor: 'pointer' }}
                      />
                    </Marker>
                  )
                })}
              </ZoomableGroup>
            </ComposableMap>
          </div>

          <p className="text-xs text-gray-400 text-center mt-2">
            Натисніть на кружечок, щоб побачити деталі регіону
          </p>

          {/* Legend */}
          <div className="flex items-center gap-5 mt-3 justify-center flex-wrap">
            {[
              { color: '#ef4444', label: 'Критичний (≥75)' },
              { color: '#f97316', label: 'Високий (≥50)' },
              { color: '#eab308', label: 'Середній (≥25)' },
              { color: '#22c55e', label: 'Низький (<25)' },
              { color: '#94a3b8', label: 'Немає даних' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* Region detail panel */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          {selected ? (
            <div>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="font-semibold text-gray-900">{selected.region}</h2>
                  <div className="mt-1">
                    <RiskBadge category={scoreToCategory(selected.avg_risk_score)} size="sm" />
                  </div>
                </div>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 ml-2">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {detailLoading ? (
                <div className="space-y-2 animate-pulse">
                  {[1, 2, 3].map(i => <div key={i} className="h-4 bg-gray-200 rounded" />)}
                </div>
              ) : regionDetail ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-xs text-gray-500">Тендери</p>
                      <p className="text-lg font-bold text-gray-800">{formatNumber(regionDetail.total_tenders)}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-xs text-gray-500">Ризикових</p>
                      <p className="text-lg font-bold text-gray-800">{formatNumber(regionDetail.high_risk_tenders)}</p>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded p-2 text-center">
                    <p className="text-xs text-gray-500">Загальна вартість</p>
                    <p className="text-base font-bold text-gray-800">{formatCurrency(regionDetail.total_value)}</p>
                  </div>

                  {regionDetail.avg_risk_score != null && (
                    <div className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-xs text-gray-500">Середній бал ризику</p>
                      <p className="text-base font-bold text-gray-800">
                        {regionDetail.avg_risk_score.toFixed(1)}
                        <span className="text-xs text-gray-400 ml-1">/ 100</span>
                      </p>
                    </div>
                  )}

                  {regionDetail.top_contractors?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-600 mb-2">Топ ризикові підрядники</p>
                      <div className="space-y-1.5">
                        {regionDetail.top_contractors.slice(0, 5).map(c => (
                          <div key={c.id} className="flex items-center justify-between text-xs">
                            <a
                              href={`/contractor/${c.id}`}
                              className="text-sentinel-600 hover:underline truncate flex-1 mr-2"
                            >
                              {c.name}
                            </a>
                            <RiskBadge category={c.risk_category} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <MapIcon className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Натисніть на кружечок для перегляду деталей регіону</p>
            </div>
          )}
        </div>
      </div>

      {/* Region table */}
      {regions && (
        <div className="mt-6 bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Всі регіони</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                  <th className="px-4 py-2 font-medium">Регіон</th>
                  <th className="px-4 py-2 font-medium">Ризик</th>
                  <th className="px-4 py-2 font-medium">Середній бал</th>
                  <th className="px-4 py-2 font-medium">Тендери</th>
                  <th className="px-4 py-2 font-medium">Загальна вартість</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {regions.map(r => (
                  <tr
                    key={r.region}
                    className={`hover:bg-gray-50 cursor-pointer transition-colors ${selected?.region === r.region ? 'bg-blue-50' : ''}`}
                    onClick={() => setSelected(r)}
                  >
                    <td className="px-4 py-2 font-medium text-gray-800">{r.region}</td>
                    <td className="px-4 py-2"><RiskBadge category={scoreToCategory(r.avg_risk_score)} /></td>
                    <td className="px-4 py-2 text-gray-600">{r.avg_risk_score != null ? r.avg_risk_score.toFixed(1) : '—'}</td>
                    <td className="px-4 py-2 text-gray-600">{formatNumber(r.total_tenders)}</td>
                    <td className="px-4 py-2 text-gray-600">{formatCurrency(r.total_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
