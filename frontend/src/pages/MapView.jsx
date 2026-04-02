import { useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'
import { useApi } from '../hooks/useApi'
import { regionsAPI } from '../services/api'
import { PageLoader } from '../components/shared/LoadingSpinner'
import RiskBadge from '../components/shared/RiskBadge'
import { formatCurrency, formatNumber } from '../services/api'
import { Map as MapIcon, X } from 'lucide-react'

const UKRAINE_TOPO = 'https://cdn.jsdelivr.net/npm/ukraine-map-topojson@1.0.0/ukraine.json'

function riskColor(category) {
  return { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e' }[category] || '#94a3b8'
}

function riskFill(category) {
  return { critical: '#fee2e2', high: '#ffedd5', medium: '#fef9c3', low: '#dcfce7' }[category] || '#f3f4f6'
}

export default function MapView() {
  const [selected, setSelected] = useState(null)
  const { data: regions, loading } = useApi(() => regionsAPI.list(), [])
  const { data: regionDetail, loading: detailLoading } = useApi(
    () => selected ? regionsAPI.get(selected.name) : Promise.resolve({ data: null }),
    [selected?.name]
  )

  if (loading) return <PageLoader />

  const regionMap = {}
  regions?.forEach(r => { regionMap[r.name] = r })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Карта ризиків</h1>
        <p className="text-gray-500 text-sm">Регіональний розподіл ризиків держзакупівель</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          {regions ? (
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 2800, center: [31, 49] }}
              width={600}
              height={380}
            >
              <ZoomableGroup>
                <Geographies geography={UKRAINE_TOPO}>
                  {({ geographies }) =>
                    geographies.map(geo => {
                      const regionName = geo.properties.NAME_1 || geo.properties.name
                      const region = Object.values(regionMap).find(r =>
                        r.name.toLowerCase().includes((regionName || '').toLowerCase().slice(0, 5))
                      )
                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          onClick={() => region && setSelected(region)}
                          style={{
                            default: {
                              fill: region ? riskFill(region.dominant_risk_category) : '#f3f4f6',
                              stroke: '#d1d5db',
                              strokeWidth: 0.5,
                              outline: 'none',
                            },
                            hover: {
                              fill: region ? riskColor(region.dominant_risk_category) : '#e5e7eb',
                              stroke: '#6b7280',
                              strokeWidth: 0.8,
                              outline: 'none',
                              cursor: 'pointer',
                            },
                            pressed: { outline: 'none' },
                          }}
                        />
                      )
                    })
                  }
                </Geographies>

                {/* Markers for regions with coordinates */}
                {regions.filter(r => r.lat && r.lng).map(r => (
                  <Marker key={r.name} coordinates={[r.lng, r.lat]}>
                    <circle
                      r={Math.min(8, 3 + (r.high_risk_contractors || 0) * 0.1)}
                      fill={riskColor(r.dominant_risk_category)}
                      fillOpacity={0.7}
                      stroke="#fff"
                      strokeWidth={1}
                      onClick={() => setSelected(r)}
                      style={{ cursor: 'pointer' }}
                    />
                  </Marker>
                ))}
              </ZoomableGroup>
            </ComposableMap>
          ) : (
            <div className="flex items-center justify-center h-80 text-gray-400">
              <MapIcon className="w-12 h-12" />
            </div>
          )}

          {/* Legend */}
          <div className="flex items-center gap-4 mt-2 justify-center">
            {[
              { color: '#fee2e2', border: '#ef4444', label: 'Критичний' },
              { color: '#ffedd5', border: '#f97316', label: 'Високий' },
              { color: '#fef9c3', border: '#eab308', label: 'Середній' },
              { color: '#dcfce7', border: '#22c55e', label: 'Низький' },
            ].map(({ color, border, label }) => (
              <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="w-4 h-3 rounded border" style={{ background: color, borderColor: border }} />
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
                  <h2 className="font-semibold text-gray-900">{selected.name}</h2>
                  <RiskBadge category={selected.dominant_risk_category} size="sm" />
                </div>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {detailLoading ? (
                <div className="space-y-2 animate-pulse">
                  {[1,2,3].map(i => <div key={i} className="h-4 bg-gray-200 rounded" />)}
                </div>
              ) : regionDetail ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-xs text-gray-500">Підрядники</p>
                      <p className="text-lg font-bold text-gray-800">{formatNumber(regionDetail.total_contractors)}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-xs text-gray-500">Тендери</p>
                      <p className="text-lg font-bold text-gray-800">{formatNumber(regionDetail.total_tenders)}</p>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded p-2 text-center">
                    <p className="text-xs text-gray-500">Загальна вартість</p>
                    <p className="text-base font-bold text-gray-800">{formatCurrency(regionDetail.total_contract_value)}</p>
                  </div>

                  {regionDetail.top_contractors?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-600 mb-2">Топ ризикові підрядники</p>
                      <div className="space-y-1.5">
                        {regionDetail.top_contractors.slice(0, 5).map(c => (
                          <div key={c.id} className="flex items-center justify-between text-xs">
                            <a href={`/contractor/${c.id}`} className="text-sentinel-600 hover:underline truncate flex-1">
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
              <p className="text-sm text-gray-500">Натисніть на регіон для перегляду деталей</p>
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
                  <th className="px-4 py-2 font-medium">Домінуючий ризик</th>
                  <th className="px-4 py-2 font-medium">Підрядники</th>
                  <th className="px-4 py-2 font-medium">Тендери</th>
                  <th className="px-4 py-2 font-medium">Загальна вартість</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {regions.map(r => (
                  <tr key={r.name} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(r)}>
                    <td className="px-4 py-2 font-medium text-gray-800">{r.name}</td>
                    <td className="px-4 py-2"><RiskBadge category={r.dominant_risk_category} /></td>
                    <td className="px-4 py-2 text-gray-600">{formatNumber(r.total_contractors)}</td>
                    <td className="px-4 py-2 text-gray-600">{formatNumber(r.total_tenders)}</td>
                    <td className="px-4 py-2 text-gray-600">{formatCurrency(r.total_contract_value)}</td>
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
