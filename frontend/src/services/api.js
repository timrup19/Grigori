import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// ============================================================================
// Search API
// ============================================================================

export const searchAPI = {
  contractors: (params) => api.get('/search/contractors', { params }),
  tenders: (params) => api.get('/search/tenders', { params }),
  buyers: (params) => api.get('/search/buyers', { params }),
  unified: (q, limit = 10) => api.get('/search/unified', { params: { q, limit } }),
  autocomplete: (q, type, limit = 5) => api.get('/search/autocomplete', { params: { q, type, limit } }),
}

// ============================================================================
// Contractors API
// ============================================================================

export const contractorsAPI = {
  get: (id) => api.get(`/contractors/${id}`),
  getTenders: (id, params) => api.get(`/contractors/${id}/tenders`, { params }),
  getNetwork: (id, params) => api.get(`/contractors/${id}/network`, { params }),
  getRiskFactors: (id) => api.get(`/contractors/${id}/risk-factors`),
  getEnrichment: (id) => api.get(`/contractors/${id}/enrichment`),
  getBuyers: (id, limit = 20) => api.get(`/contractors/${id}/buyers`, { params: { limit } }),
  getCaptureAnalysis: (id) => api.get(`/contractors/${id}/capture-analysis`),
  getBidRotation: (id) => api.get(`/contractors/${id}/bid-rotation`),
  getTimeline: (id, period = '1y') => api.get(`/contractors/${id}/timeline`, { params: { period } }),
  byEdrpou: (edrpou) => api.get(`/contractors/by-edrpou/${edrpou}`),
  highRisk: (params) => api.get('/contractors/high-risk', { params }),
}

// ============================================================================
// Tenders API
// ============================================================================

export const tendersAPI = {
  get: (id) => api.get(`/tenders/${id}`),
}

// ============================================================================
// Buyers API
// ============================================================================

export const buyersAPI = {
  get: (id) => api.get(`/buyers/${id}`),
  getTenders: (id, params) => api.get(`/buyers/${id}/tenders`, { params }),
  getContractors: (id, params) => api.get(`/buyers/${id}/contractors`, { params }),
}

// ============================================================================
// Alerts API
// ============================================================================

export const alertsAPI = {
  list: (params) => api.get('/alerts', { params }),
  latest: (limit = 10) => api.get('/alerts/latest', { params: { limit } }),
  stats: (days = 7) => api.get('/alerts/stats', { params: { days } }),
  trending: () => api.get('/alerts/trending'),
  get: (id) => api.get(`/alerts/${id}`),
}

// ============================================================================
// Network API
// ============================================================================

export const networkAPI = {
  getContractorNetwork: (contractorId, params) => api.get(`/network/${contractorId}`, { params }),
  getConnections: (contractorId, params) => api.get(`/network/${contractorId}/connections`, { params }),
  suspiciousCommunities: (params) => api.get('/network/communities/suspicious', { params }),
  topPairs: (params) => api.get('/network/pairs/top', { params }),
  stats: () => api.get('/network/stats'),
}

// ============================================================================
// Regions API
// ============================================================================

export const regionsAPI = {
  list: () => api.get('/regions'),
  summary: () => api.get('/regions/summary'),
  get: (name) => api.get(`/regions/${encodeURIComponent(name)}`),
  getTenders: (name, params) => api.get(`/regions/${encodeURIComponent(name)}/tenders`, { params }),
  getContractors: (name, params) => api.get(`/regions/${encodeURIComponent(name)}/contractors`, { params }),
  getTrends: (name, period = '30d') => api.get(`/regions/${encodeURIComponent(name)}/trends`, { params: { period } }),
}

// ============================================================================
// Stats API
// ============================================================================

export const statsAPI = {
  overview: () => api.get('/stats/overview'),
  riskDistribution: () => api.get('/stats/risk-distribution'),
  trends: (period = '30d') => api.get('/stats/trends', { params: { period } }),
  cpvBreakdown: (limit = 20) => api.get('/stats/cpv-breakdown', { params: { limit } }),
  topBuyers: (by = 'value', limit = 20) => api.get('/stats/top-buyers', { params: { by, limit } }),
  topContractors: (by = 'value', limit = 20) => api.get('/stats/top-contractors', { params: { by, limit } }),
  syncStatus: () => api.get('/stats/sync-status'),
}

// ============================================================================
// Utility functions
// ============================================================================

export const formatCurrency = (value, currency = 'UAH') => {
  if (!value) return '—'
  return new Intl.NumberFormat('uk-UA', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export const formatNumber = (value) => {
  if (!value) return '0'
  return new Intl.NumberFormat('uk-UA').format(value)
}

export const formatPercent = (value) => {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export const getRiskColor = (category) => {
  switch (category) {
    case 'critical': return 'risk-critical'
    case 'high': return 'risk-high'
    case 'medium': return 'risk-medium'
    case 'low': return 'risk-low'
    default: return 'gray-400'
  }
}

export const getRiskLabel = (category) => {
  switch (category) {
    case 'critical': return 'Critical'
    case 'high': return 'High'
    case 'medium': return 'Medium'
    case 'low': return 'Low'
    default: return 'Unknown'
  }
}

export default api
