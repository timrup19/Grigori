import { Link } from 'react-router-dom'
import RiskBadge from '../shared/RiskBadge'
import { SkeletonRow } from '../shared/LoadingSpinner'
import Pagination from '../shared/Pagination'
import EmptyState from '../shared/EmptyState'
import { Search, FileText } from 'lucide-react'
import { formatCurrency } from '../../services/api'

const STATUS_LABELS = {
  active: 'Активний',
  complete: 'Завершений',
  cancelled: 'Скасований',
  unsuccessful: 'Невдалий',
}

const STATUS_STYLES = {
  active: 'text-green-700 bg-green-50',
  complete: 'text-blue-700 bg-blue-50',
  cancelled: 'text-gray-600 bg-gray-100',
  unsuccessful: 'text-red-700 bg-red-50',
}

export default function TenderResults({ data, loading, page, onPageChange }) {
  if (loading) {
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
            <th className="px-4 py-3 font-medium">Тендер</th>
            <th className="px-4 py-3 font-medium">Замовник</th>
            <th className="px-4 py-3 font-medium">Сума</th>
            <th className="px-4 py-3 font-medium">Ризик</th>
            <th className="px-4 py-3 font-medium">Статус</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={5} />)}
        </tbody>
      </table>
    )
  }

  if (!data?.results?.length) {
    return <EmptyState icon={Search} title="Тендерів не знайдено" description="Спробуйте змінити пошуковий запит або фільтри" />
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Тендер</th>
              <th className="px-4 py-3 font-medium">Замовник</th>
              <th className="px-4 py-3 font-medium">Сума</th>
              <th className="px-4 py-3 font-medium">Ризик</th>
              <th className="px-4 py-3 font-medium">Ставки</th>
              <th className="px-4 py-3 font-medium">Статус</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.results.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 max-w-xs">
                  <div className="flex items-start gap-2">
                    <FileText className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-800 line-clamp-2">{t.title}</div>
                      <div className="text-xs text-gray-400 font-mono mt-0.5">{t.prozorro_id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">{t.buyer_name}</td>
                <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{formatCurrency(t.expected_value)}</td>
                <td className="px-4 py-3">
                  <RiskBadge category={t.risk_category} score={t.risk_score} showScore />
                </td>
                <td className="px-4 py-3 text-center text-gray-600">{t.num_bids ?? '—'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[t.status] || 'text-gray-600 bg-gray-100'}`}>
                    {STATUS_LABELS[t.status] || t.status}
                  </span>
                </td>
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
