import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { networkAPI } from '../services/api'
import { useApi } from '../hooks/useApi'
import { PageLoader } from '../components/shared/LoadingSpinner'
import EmptyState from '../components/shared/EmptyState'
import StatCard from '../components/shared/StatCard'
import { GitBranch, Users, Loader2 } from 'lucide-react'
import { formatNumber } from '../services/api'

// Lazy-load vis-network to keep initial bundle small
async function loadVisNetwork() {
  const { Network } = await import('vis-network/standalone')
  return Network
}

function buildVisData(networkData) {
  const nodes = networkData.nodes.map(n => ({
    id: n.id,
    label: n.name.length > 20 ? n.name.slice(0, 20) + '…' : n.name,
    title: `${n.name}\nРизик: ${n.risk_score?.toFixed(0) ?? '—'}\nТендерів: ${n.tender_count ?? 0}`,
    color: {
      background: { critical: '#fee2e2', high: '#ffedd5', medium: '#fef9c3', low: '#dcfce7' }[n.risk_category] || '#f3f4f6',
      border: { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e' }[n.risk_category] || '#9ca3af',
    },
    size: 12 + Math.min(30, (n.tender_count || 0) * 0.5),
    font: { size: 11, color: '#374151' },
  }))

  const edges = networkData.edges.map(e => ({
    from: e.source,
    to: e.target,
    value: e.co_bid_count || 1,
    title: `Спільних торгів: ${e.co_bid_count}`,
    color: { color: '#94a3b8', opacity: 0.7 },
    width: Math.min(5, 1 + (e.co_bid_count || 1) * 0.3),
  }))

  return { nodes, edges }
}

export default function Network() {
  const { contractorId } = useParams()
  const navigate = useNavigate()
  const graphRef = useRef(null)
  const networkRef = useRef(null)
  const [graphLoading, setGraphLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)

  const { data: stats } = useApi(() => networkAPI.stats(), [])
  const { data: networkData, loading: dataLoading } = useApi(
    () => contractorId
      ? networkAPI.getContractorNetwork(contractorId, { depth: 2 })
      : networkAPI.topPairs({ limit: 100 }),
    [contractorId]
  )

  useEffect(() => {
    if (!networkData || !graphRef.current) return

    const data = contractorId ? networkData : networkData.graph
    if (!data?.nodes?.length) return

    setGraphLoading(true)

    loadVisNetwork().then(VisNetwork => {
      if (networkRef.current) networkRef.current.destroy()

      const { nodes, edges } = buildVisData(data)

      networkRef.current = new VisNetwork(
        graphRef.current,
        { nodes, edges },
        {
          physics: {
            stabilization: { iterations: 150 },
            barnesHut: { gravitationalConstant: -8000, springLength: 120 },
          },
          interaction: { hover: true, tooltipDelay: 200 },
          layout: { improvedLayout: false },
        }
      )

      networkRef.current.on('click', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const node = data.nodes.find(n => n.id === nodeId)
          setSelectedNode(node || null)
        } else {
          setSelectedNode(null)
        }
      })

      networkRef.current.on('stabilizationIterationsDone', () => {
        setGraphLoading(false)
        networkRef.current.fit({ animation: true })
      })
    })

    return () => { networkRef.current?.destroy(); networkRef.current = null }
  }, [networkData, contractorId])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Мережа зв'язків</h1>
        <p className="text-gray-500 text-sm">Граф спільних торгів підрядників</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Підрядники в мережі" value={formatNumber(stats.total_nodes)} icon={Users} accent="blue" />
          <StatCard label="Зв'язки" value={formatNumber(stats.total_edges)} icon={GitBranch} accent="blue" />
          <StatCard label="Підозрілих спільнот" value={formatNumber(stats.suspicious_communities)} accent="red" />
          <StatCard label="Макс. ступінь" value={stats.max_degree} accent="orange" />
        </div>
      )}

      <div className="grid lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden" style={{ height: 520 }}>
            {dataLoading ? (
              <PageLoader />
            ) : (
              <>
                <div ref={graphRef} className="w-full h-full" />
                {graphLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white/70 pointer-events-none">
                    <Loader2 className="w-6 h-6 text-sentinel-600 animate-spin" />
                  </div>
                )}
                {networkData && !(contractorId ? networkData?.nodes?.length : networkData?.graph?.nodes?.length) && (
                  <EmptyState icon={GitBranch} title="Немає даних для відображення" />
                )}
              </>
            )}
          </div>
        </div>

        <div className="space-y-3">
          {selectedNode ? (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Обраний підрядник</h3>
              <p className="text-sm text-gray-700 mb-1">{selectedNode.name}</p>
              <p className="text-xs text-gray-500">Ризик: {selectedNode.risk_score?.toFixed(0) ?? '—'}</p>
              <p className="text-xs text-gray-500">Тендерів: {selectedNode.tender_count ?? 0}</p>
              <button
                onClick={() => navigate(`/contractor/${selectedNode.id}`)}
                className="mt-3 w-full text-xs px-3 py-1.5 bg-sentinel-600 text-white rounded-md hover:bg-sentinel-700"
              >
                Переглянути профіль
              </button>
              <button
                onClick={() => navigate(`/network/${selectedNode.id}`)}
                className="mt-1.5 w-full text-xs px-3 py-1.5 border border-gray-200 text-gray-600 rounded-md hover:bg-gray-50"
              >
                Мережа підрядника
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Підказка</h3>
              <p className="text-xs text-gray-500">Натисніть на вузол, щоб переглянути деталі підрядника</p>
              <div className="mt-3 space-y-1.5">
                {[
                  { color: 'bg-red-200 border-red-400', label: 'Критичний ризик' },
                  { color: 'bg-orange-200 border-orange-400', label: 'Високий ризик' },
                  { color: 'bg-yellow-200 border-yellow-400', label: 'Середній ризик' },
                  { color: 'bg-green-200 border-green-400', label: 'Низький ризик' },
                ].map(({ color, label }) => (
                  <div key={label} className="flex items-center gap-2 text-xs text-gray-600">
                    <span className={`w-3 h-3 rounded-full border ${color}`} />
                    {label}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
