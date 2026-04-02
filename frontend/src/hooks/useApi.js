import { useState, useEffect, useCallback } from 'react'

/**
 * Generic async data-fetching hook.
 * Re-runs whenever any value in `deps` changes.
 *
 * @param {Function} apiFn  - () => Promise (an axios call)
 * @param {Array}    deps   - dependency array (like useEffect)
 * @param {*}        initial - initial data value (default null)
 */
export function useApi(apiFn, deps = [], initial = null) {
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    apiFn()
      .then((res) => {
        if (!cancelled) {
          setData(res.data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Failed to load')
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const refetch = useCallback(() => {
    setLoading(true)
    setError(null)
    apiFn()
      .then((res) => { setData(res.data); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, refetch }
}
