import { useState, useEffect } from 'react'
import { Layout } from '../components/Navigation'
import { PageHeader, ErrorMsg, LoadingSpinner, StatCard, rupee } from '../components/UI'
import { runBacktest, getBacktestResult, getBacktestDailyLog, searchStocks } from '../api/client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export default function BacktestPage() {
  const [step, setStep]     = useState('setup') // setup | loading | results
  const [error, setError]   = useState('')
  const [result, setResult] = useState(null)
  const [dailyLog, setDailyLog] = useState([])

  // Form state
  const [stocks, setStocks] = useState([])   // selected stocks (max 7)
  const [fromDate, setFromDate] = useState('2020-01-01')
  const [toDate, setToDate]     = useState(new Date().toISOString().split('T')[0])
  const [capital, setCapital]   = useState('200000')
  const [risk, setRisk]         = useState('1.0')
  const [query, setQuery]       = useState('')
  const [searchResults, setSearchResults] = useState([])

  useEffect(() => {
    if (query.length < 2) { setSearchResults([]); return }
    const t = setTimeout(() => {
      searchStocks(query).then(setSearchResults).catch(() => setSearchResults([]))
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const addStock = (stock) => {
    if (stocks.length >= 7) return setError('Maximum 7 stocks per backtest')
    if (stocks.find(s => s.id === stock.id)) return
    setStocks([...stocks, stock])
    setQuery('')
    setSearchResults([])
    setError('')
  }

  const removeStock = (id) => setStocks(stocks.filter(s => s.id !== id))

  const handleRun = async () => {
    if (stocks.length === 0) return setError('Select at least 1 stock')
    setError('')
    setStep('loading')
    try {
      const res = await runBacktest({
        stock_ids: stocks.map(s => s.id),
        from_date: fromDate,
        to_date: toDate,
        starting_capital: parseFloat(capital),
        risk_percent: parseFloat(risk),
        position_size_type: 'PERCENT_CAPITAL',
        position_size_value: 10,
      })
      // Poll for result if async
      if (res.id) {
        let r; let attempts = 0
        do {
          await new Promise(ok => setTimeout(ok, 2000))
          r = await getBacktestResult(res.id)
          attempts++
        } while (r.status === 'running' && attempts < 30)
        setResult(r)
        if (r.status === 'completed') {
          const log = await getBacktestDailyLog(res.id)
          setDailyLog(log)
        }
      } else {
        setResult(res)
      }
      setStep('results')
    } catch (e) {
      setError(e.response?.data?.detail || 'Backtest failed')
      setStep('setup')
    }
  }

  const exportCSV = () => {
    if (!dailyLog || dailyLog.length === 0) return
    const headers = ['Date', 'Stock', 'Close Price', '55D High', '20D Low', 'ADX', 'Flat Days', 'Action']
    const rows = dailyLog.map(r => [
      r.date, r.stock, r.close_price, r.ch55_high, r.ch20_low, r.adx_value, r.flat_days, r.action
    ])
    const csvContent = [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'backtest_day_by_day.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Layout>
      <PageHeader title="Backtest" subtitle="Simulate the strategy on historical data" />

      <div className="px-4 py-4">
        {step === 'setup' && (
          <div className="space-y-4">
            {/* Stock selector */}
            <div>
              <label className="label">Stocks (max 7) — {stocks.length}/7</label>
              {stocks.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {stocks.map(s => (
                    <span key={s.id} className="inline-flex items-center gap-1 bg-brand/10 text-brand text-xs rounded-full px-2 py-1">
                      {s.ticker_nse}
                      <button onClick={() => removeStock(s.id)} className="hover:text-danger">✕</button>
                    </span>
                  ))}
                </div>
              )}
              <div className="relative">
                <input className="input" placeholder="Search stocks..." value={query}
                  onChange={e => setQuery(e.target.value)} />
                {searchResults.length > 0 && (
                  <div className="absolute z-10 left-0 right-0 top-full mt-1 border border-border rounded-btn bg-white shadow-card overflow-hidden">
                    {searchResults.slice(0, 5).map(r => (
                      <button key={r.id} onClick={() => addStock(r)}
                        className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-border last:border-0 text-sm">
                        <span className="font-medium">{r.ticker_nse}</span>
                        <span className="text-muted ml-2 text-xs">{r.company_name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Date range */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">From Date</label>
                <input type="date" className="input" value={fromDate} onChange={e => setFromDate(e.target.value)} />
              </div>
              <div>
                <label className="label">To Date</label>
                <input type="date" className="input" value={toDate} onChange={e => setToDate(e.target.value)} />
              </div>
            </div>

            {/* Capital + Risk */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Capital (₹)</label>
                <input type="number" inputMode="numeric" className="input" value={capital} onChange={e => setCapital(e.target.value)} />
              </div>
              <div>
                <label className="label">Risk %</label>
                <input type="number" inputMode="decimal" step="0.5" min="0.5" max="5" className="input" value={risk} onChange={e => setRisk(e.target.value)} />
              </div>
            </div>

            <ErrorMsg msg={error} />
            <button onClick={handleRun} className="btn-primary">🚀 Run Backtest</button>
          </div>
        )}

        {step === 'loading' && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <LoadingSpinner size="lg" />
            <p className="text-muted text-sm">Running backtest... this may take a moment</p>
          </div>
        )}

        {step === 'results' && result && (
          <div className="space-y-4">
            <div className="flex justify-between items-end mb-2">
              <button onClick={() => { setStep('setup'); setResult(null) }} className="btn-ghost !w-auto !px-0 flex items-center gap-1">
                ← Run Another
              </button>
              {stocks.length > 0 && (
                <div className="text-right">
                  <h3 className="font-semibold text-lg">{stocks.map(s => s.ticker_nse).join(', ')}</h3>
                  <p className="text-muted text-xs">Simulated {fromDate} to {toDate}</p>
                </div>
              )}
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-3">
              <StatCard label="Total Return" value={`${result.total_return_percent >= 0 ? '+' : ''}${result.total_return_percent?.toFixed(2)}%`} color={result.total_return_percent >= 0 ? 'green' : 'red'} />
              <StatCard label="Win Rate" value={`${result.win_rate_percent?.toFixed(1)}%`} color="blue" />
              <StatCard label="Total Trades" value={result.total_trades} />
              <StatCard label="Max Drawdown" value={`${result.max_drawdown_percent?.toFixed(2)}%`} color="red" />
              <StatCard label="Avg Profit" value={`+${result.avg_profit_percent?.toFixed(2)}%`} color="green" />
              <StatCard label="Avg Loss" value={`${result.avg_loss_percent?.toFixed(2)}%`} color="red" />
            </div>

            {/* Equity curve */}
            {result.equity_curve?.length > 0 && (
              <div className="card p-4">
                <div className="font-semibold text-text mb-3">Equity Curve</div>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={result.equity_curve}>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d?.slice(5)} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
                    <Tooltip formatter={(v) => rupee(v)} labelFormatter={d => `Date: ${d}`} />
                    <ReferenceLine y={parseFloat(capital)} stroke="#64748B" strokeDasharray="3 3" />
                    <Line type="monotone" dataKey="capital" stroke="#0F4C81" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Day-by-Day Log */}
            {dailyLog.length > 0 && (
              <div className="card p-4 mt-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-text">Day-by-Day Simulation Logs</h3>
                  <button onClick={exportCSV} className="btn-secondary text-xs px-3 py-1">
                    [Export CSV]
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-border">
                        <th className="p-2">Date</th>
                        <th className="p-2">Stock</th>
                        <th className="p-2">Close</th>
                        <th className="p-2">55D High</th>
                        <th className="p-2">20D Low</th>
                        <th className="p-2">ADX</th>
                        <th className="p-2">Flat Days</th>
                        <th className="p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dailyLog.slice(0, 100).map((row, i) => (
                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="p-2">{row.date}</td>
                          <td className="p-2">{row.stock}</td>
                          <td className="p-2">{rupee(row.close_price)}</td>
                          <td className="p-2">{rupee(row.ch55_high)}</td>
                          <td className="p-2">{rupee(row.ch20_low)}</td>
                          <td className="p-2">{row.adx_value?.toFixed(1) || '-'}</td>
                          <td className="p-2">{row.flat_days}</td>
                          <td className={`p-2 font-medium 
                            ${row.action === 'BUY' ? 'text-green-600' : 
                              row.action === 'SELL' ? 'text-red-600' : 
                              row.action === 'SKIPPED_CAPITAL' ? 'text-amber-500' : 
                              'text-muted'}
                          `}>
                            {row.action}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {dailyLog.length > 100 && (
                  <div className="text-center text-xs text-muted mt-3 italic">
                    Showing first 100 days. Export CSV to view all {dailyLog.length} rows.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}
