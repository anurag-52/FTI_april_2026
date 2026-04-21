import { useState, useEffect } from 'react'
import { Layout } from '../components/Navigation'
import { searchStocks, getImportedStocks, importStockData } from '../api/client'
import { Search, Database, CheckCircle2, Loader2, AlertCircle, RefreshCw, PlusCircle, ArrowRight } from 'lucide-react'


export default function ImportDataPage() {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [importedStocks, setImportedStocks] = useState([])
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [loadingImported, setLoadingImported] = useState(true)
  const [importingTickers, setImportingTickers] = useState(new Set()) // Track local UI state for button loading
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchImported()
    // Poll for status updates every 10 seconds if there are active imports
    const timer = setInterval(() => {
      fetchImported()
    }, 10000)
    return () => clearInterval(timer)
  }, [])

  const fetchImported = async () => {
    try {
      const data = await getImportedStocks()
      setImportedStocks(data)
    } catch (err) {
      console.error('Failed to fetch imported stocks:', err)
    } finally {
      setLoadingImported(false)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (query.length < 2) return
    setLoadingSearch(true)
    setError(null)
    try {
      const data = await searchStocks(query, false) // imported_only = false
      setSearchResults(data)
    } catch (err) {
      setError('Search failed. Please try again.')
    } finally {
      setLoadingSearch(false)
    }
  }

  const handleTriggerImport = async (stock) => {
    setImportingTickers(prev => new Set(prev).add(stock.id))
    try {
      await importStockData(stock.id)
      // Success - show a toast or alert if we had a system for it
      // For now, we rely on the polling to update the list
      setSearchResults(prev => prev.map(s => s.id === stock.id ? { ...s, history_fetched: 'pending' } : s))
    } catch (err) {
      alert(`Failed to trigger import for ${stock.ticker_nse || stock.company_name}`)
    } finally {
      // Don't remove from set immediately, let polling do its job? 
      // Actually removing keeps the UI honest about the REQUEST completion.
      setTimeout(() => {
        setImportingTickers(prev => {
          const next = new Set(prev)
          next.delete(stock.id)
          return next
        })
      }, 1000)
    }
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-6 py-10">
        <header className="mb-10 animate-slide-up">
          <div className="flex items-center gap-3 mb-2">
            <Database className="w-8 h-8 text-brand" />
            <h1 className="text-3xl font-bold text-text">Central Data Repository</h1>
          </div>
          <p className="text-muted text-lg max-w-2xl">
            Import 10 years of historical data for any stock. Only imported stocks can be used for backtesting and watchlists.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Search & Import Section */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white rounded-2xl border border-border p-6 shadow-sm shadow-black/5 animate-slide-up" style={{ animationDelay: '0.1s' }}>
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted mb-4 flex items-center gap-2">
                <PlusCircle className="w-4 h-4" /> Import New Stock
              </h2>
              <form onSubmit={handleSearch} className="mb-6">
                <div className="relative group">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted group-focus-within:text-brand transition-colors" />
                  <input
                    type="text"
                    placeholder="Search NSE/BSE ticker (e.g. RELIANCE)..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full pl-12 pr-4 h-14 bg-gray-50 border-border group-focus-within:bg-white transition-all text-base"
                  />
                  <button 
                    type="submit" 
                    disabled={loadingSearch || query.length < 2}
                    className="absolute right-2 top-2 bottom-2 px-4 bg-brand text-white text-sm font-bold rounded-xl hover:bg-brand-dark transition-all disabled:opacity-50"
                  >
                    {loadingSearch ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                  </button>
                </div>
              </form>

              {error && (
                <div className="p-4 bg-red-50 border border-red-100 rounded-xl flex items-center gap-3 text-red-600 text-sm mb-4">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-3">
                {searchResults.map((stock) => {
                  const isImported = importedStocks.some(i => i.ticker_nse === stock.ticker_nse) || stock.history_fetched === true
                  const isPending = importingTickers.has(stock.id) || stock.history_fetched === 'pending'
                  
                  return (
                    <div key={stock.id} className="group p-4 bg-gray-50 hover:bg-white hover:shadow-lg hover:shadow-black/5 border border-transparent hover:border-brand/20 rounded-xl transition-all flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${isImported ? 'bg-green-50 text-green-600' : 'bg-brand/5 text-brand'}`}>
                          {stock.ticker_nse?.[0] || stock.company_name?.[0]}
                        </div>
                        <div>
                          <div className="font-bold text-text flex items-center gap-2">
                            {stock.ticker_nse}
                            <span className="text-[10px] px-1.5 py-0.5 bg-gray-200 text-muted-foreground rounded uppercase font-bold tracking-tighter">{stock.exchange}</span>
                          </div>
                          <div className="text-[11px] text-muted truncate max-w-[150px]">{stock.company_name}</div>
                        </div>
                      </div>

                      {isImported ? (
                        <div className="flex items-center gap-1.5 text-green-600 text-[11px] font-bold px-3 py-1.5 bg-green-50 rounded-lg">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                        </div>
                      ) : isPending ? (
                        <div className="flex items-center gap-1.5 text-brand text-[11px] font-bold px-3 py-1.5 bg-brand/5 rounded-lg">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching...
                        </div>
                      ) : (
                        <button
                          onClick={() => handleTriggerImport(stock)}
                          className="flex items-center gap-1.5 text-brand hover:text-white px-3 py-1.5 bg-white group-hover:bg-brand border border-brand/20 group-hover:border-brand rounded-lg text-xs font-bold transition-all shadow-sm"
                        >
                          Import 10Y <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )
                })}
                {searchResults.length === 0 && !loadingSearch && query.length >= 2 && (
                  <div className="py-10 text-center">
                    <p className="text-muted text-sm">No new stocks found for "{query}"</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Imported List Section */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-white rounded-2xl border border-border shadow-sm shadow-black/5 animate-slide-up" style={{ animationDelay: '0.2s' }}>
              <div className="p-6 border-b border-border flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-text">Central Database Inventory</h2>
                  <p className="text-sm text-muted">{importedStocks.length} stocks available for analysis</p>
                </div>
                <button 
                  onClick={fetchImported} 
                  className="p-2 text-muted hover:text-brand hover:bg-brand/5 rounded-full transition-all"
                  title="Refresh Inventory"
                >
                  <RefreshCw className={`w-5 h-5 ${loadingImported ? 'animate-spin' : ''}`} />
                </button>
              </div>

              <div className="overflow-hidden overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50/50">
                      <th className="px-6 py-4 text-[11px] font-bold text-muted uppercase tracking-wider">Stock</th>
                      <th className="px-6 py-4 text-[11px] font-bold text-muted uppercase tracking-wider">Exchange</th>
                      <th className="px-6 py-4 text-[11px] font-bold text-muted uppercase tracking-wider">Industry</th>
                      <th className="px-6 py-4 text-[11px] font-bold text-muted uppercase tracking-wider text-right">Data Since</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {importedStocks.map((stock) => (
                      <tr key={stock.id} className="hover:bg-gray-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-green-50 text-green-600 flex items-center justify-center font-bold text-xs">
                              {stock.ticker_nse?.[0]}
                            </div>
                            <div>
                              <div className="font-bold text-text text-sm">{stock.ticker_nse}</div>
                              <div className="text-[11px] text-muted truncate max-w-[140px]">{stock.company_name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-[11px] px-2 py-1 bg-gray-100 text-muted-foreground rounded font-bold">{stock.exchange}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-muted max-w-[150px] truncate">
                          {stock.sector || 'N/A'}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="text-xs font-medium text-text">10 Years</div>
                          <div className="text-[10px] text-muted">Ready</div>
                        </td>
                      </tr>
                    ))}
                    {loadingImported && importedStocks.length === 0 && (
                      <tr className="bg-white">
                        <td colSpan="4" className="px-6 py-20 text-center">
                          <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto mb-3" />
                          <p className="text-muted text-sm">Synchronizing inventory...</p>
                        </td>
                      </tr>
                    )}
                    {!loadingImported && importedStocks.length === 0 && (
                      <tr className="bg-white">
                        <td colSpan="4" className="px-6 py-24 text-center">
                          <Database className="w-12 h-12 text-gray-200 mx-auto mb-4" />
                          <h3 className="text-lg font-bold text-text mb-2">Central Database is Empty</h3>
                          <p className="text-muted text-sm max-w-[300px] mx-auto">
                            No stock data has been imported yet. Use the search tool to start bringing stocks into the platform.
                          </p>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
