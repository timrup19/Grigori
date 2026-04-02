import { Link } from 'react-router-dom'
import RiskBadge from '../shared/RiskBadge'
import { SkeletonRow } from '../shared/LoadingSpinner'
import Pagination from '../shared/Pagination'
import EmptyState from '../shared/EmptyState'
import { Search, Building2 } from 'lucide-react'
import { formatCurrency, formatNumber } from '../../services/api'

export default function ContractorResults({ data, loading, page, onPageChange }) {
  if (loading) {
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
            <th className="px-4 py-3 font-medium">Підрядник</th>
            <th className="px-4 py-3 font-medium">ЄДРПОУ</th>
            <th className="px-4 py-3 font-medium">Ризик</th>
            <th className="px-4 py-3 font-medium">Тендери</th>
            <th className="px-4 py-3 font-medium">Загальна сума</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={5} />)}
        </tbody>
      </table>
    )
  }

  if (!data?.items?.length) {
    return <EmptyState icon={Search} title="Підрядників не знайдено" description="Спробуйте змінити пошуковий запит або фільтри" />
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Підрядник</th>
              <th className="px-4 py-3 font-medium">ЄДРПОУ</th>
              <th className="px-4 py-3 font-medium">Ризик</th>
              <th className="px-4 py-3 font-medium">Тендери</th>
              <th className="px-4 py-3 font-medium">Загальна сума</th>
              <th className="px-4 py-3 font-medium">Регіон</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.items.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <Link to={`/contractor/${c.id}`} className="font-medium text-sentinel-700 hover:underline line-clamp-2">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      {c.name}
                    </div>
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-gray-500">{c.edrpou}</td>
                <td className="px-4 py-3">
                  <RiskBadge category={c.risk_category} score={c.risk_score} showScore />
                </td>
                <td className="px-4 py-3 text-gray-700">{formatNumber(c.total_tenders_won)}</td>
                <td className="px-4 py-3 text-gray-700">{formatCurrency(c.total_contract_value)}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{c.region || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="border-t border-gray-100 pt-2">
        <Pagination page={page} totalPages={data.total_pages} onPageChange={onPageChange} />
      </div>
    </div>
  )
}
