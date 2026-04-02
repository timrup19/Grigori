import { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { searchAPI } from '../../services/api'
import { useNavigate } from 'react-router-dom'

export default function SearchBar({ value, onChange, onSearch, placeholder = 'Пошук підрядників, тендерів…', autoFocus = false }) {
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const debounceRef = useRef(null)
  const inputRef = useRef(null)
  const wrapperRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus()
  }, [autoFocus])

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleChange(e) {
    const q = e.target.value
    onChange(q)

    clearTimeout(debounceRef.current)
    if (q.trim().length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoadingSuggestions(true)
      try {
        const res = await searchAPI.unified(q, 6)
        setSuggestions(res.data.results || [])
        setShowSuggestions(true)
      } catch {
        setSuggestions([])
      } finally {
        setLoadingSuggestions(false)
      }
    }, 300)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      setShowSuggestions(false)
      onSearch?.(value)
    }
    if (e.key === 'Escape') setShowSuggestions(false)
  }

  function handleSuggestionClick(item) {
    setShowSuggestions(false)
    if (item.type === 'contractor') {
      navigate(`/contractor/${item.id}`)
    } else {
      navigate(`/search?q=${encodeURIComponent(item.name)}&type=${item.type}`)
    }
  }

  function clear() {
    onChange('')
    setSuggestions([])
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const typeLabel = { contractor: 'Підрядник', tender: 'Тендер', buyer: 'Замовник' }

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div className="relative flex items-center">
        <Search className="absolute left-3 w-4 h-4 text-gray-400 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          placeholder={placeholder}
          className="w-full pl-9 pr-9 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sentinel-500 focus:border-transparent bg-white"
        />
        {loadingSuggestions && (
          <Loader2 className="absolute right-3 w-4 h-4 text-gray-400 animate-spin" />
        )}
        {!loadingSuggestions && value && (
          <button onClick={clear} className="absolute right-3 text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 mt-1 w-full bg-white rounded-lg border border-gray-200 shadow-lg overflow-hidden">
          {suggestions.map((item, i) => (
            <button
              key={i}
              onMouseDown={() => handleSuggestionClick(item)}
              className="w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-gray-50 text-left"
            >
              <span className="text-gray-800 truncate">{item.name}</span>
              <span className="ml-3 text-xs text-gray-400 flex-shrink-0">
                {typeLabel[item.type] || item.type}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
