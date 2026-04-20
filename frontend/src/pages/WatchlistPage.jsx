import { useState, useEffect } from 'react'
import { Layout } from '../components/Navigation'
import { PageHeader, EmptyState, ErrorMsg, LoadingSpinner } from '../components/UI'
import { getWatchlist, addToWatchlist, updateWatchlistItem, searchStocks } from '../api/client'
import { Search } from 'lucide-react'


export default function WatchlistPage() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')
  const [query, setQuery]   = useState('')
  const [results, setResults] = useState([])
  const [addError, setAddError] = useState('')

  const load = () => {
    setLoading(true)
    getWatchlist().then(setData).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const t = setTimeout(() => {
      searchStocks(query).then(setResults).catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const handleAdd = async (stock) => {
    setAddError('')
    try {
      await addToWatchlist(stock.id)
      setQuery('')
      setResults([])
      load()
    } catch (e) {
      setAddError(e.response?.data?.detail || 'Failed to add stock')
    }
  }

  const handleToggle = async (stock_id, is_active) => {
    setError('')
    try {
      await updateWatchlistItem(stock_id, { is_active: !is_active })
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Cannot deactivate — open position exists')
    }
  }

  const active   = data?.active || []
  const inactive = data?.inactive || []
  const total    = active.length

  return (
    <Layout>
      <PageHeader title="Watchlist" subtitle={`${total}/30 active stocks`} />

      <div className="px-4 py-3">
        {/* Limit bar */}
        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-brand rounded-full transition-all" style={{ width: `${total / 30 * 100}%` }} />
          </div>
          <span className="text-xs text-muted font-medium">{total}/30</span>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <input className="input pl-9" placeholder="Search and add stocks..."
            value={query} onChange={e => setQuery(e.target.value)} />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"><Search className="w-4 h-4" /></span>
          {results.length > 0 && (
            <div className="absolute z-10 left-0 right-0 top-full mt-1 border border-border rounded-btn bg-white shadow-card overflow-hidden">
              {results.map(r => (
                <button key={r.id} onClick={() => handleAdd(r)}
                  className="w-full text-left px-3 py-2.5 hover:bg-gray-50 border-b border-border last:border-0 text-sm flex items-center justify-between">
                  <div>
                    <span className="font-medium">{r.ticker_nse}</span>
                    <span className="text-muted ml-2 text-xs">{r.company_name}</span>
                  </div>
                  <span className="text-brand text-xs font-medium">+ Add</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {addError && <ErrorMsg msg={addError} />}
        {error && <ErrorMsg msg={error} />}

        {loading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : (
          <>
            {/* Active stocks */}
            {active.length > 0 && (
              <div className="mb-4">
                <h2 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
                  Active ({active.length})
                </h2>
                <div className="space-y-2">
                  {active.map(item => (
                    <div key={item.stock_id} className="card px-4 py-3 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-sm">{item.ticker_nse}</div>
                        <div className="text-xs text-muted">{item.company_name}</div>
                      </div>
                      <button onClick={() => handleToggle(item.stock_id, true)}
                        className="text-xs text-danger border border-danger rounded-btn px-2 py-1 hover:bg-red-50 transition-colors">
                        Deactivate
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inactive stocks */}
            {inactive.length > 0 && (
              <div>
                <h2 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
                  Inactive ({inactive.length})
                </h2>
                <div className="space-y-2">
                  {inactive.map(item => (
                    <div key={item.stock_id} className="card px-4 py-3 flex items-center justify-between opacity-60">
                      <div>
                        <div className="font-semibold text-sm">{item.ticker_nse}</div>
                        <div className="text-xs text-muted">{item.company_name}</div>
                      </div>
                      <button onClick={() => handleToggle(item.stock_id, false)}
                        className="text-xs text-success border border-success rounded-btn px-2 py-1 hover:bg-green-50 transition-colors">
                        Reactivate
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {active.length === 0 && inactive.length === 0 && (
              <EmptyState icon={<Search className="w-10 h-10 text-muted" />} title="No stocks in watchlist"
                subtitle="Search and add NSE stocks above to start receiving signals"
              />
            )}
          </>
        )}
      </div>
    </Layout>
  )
}
