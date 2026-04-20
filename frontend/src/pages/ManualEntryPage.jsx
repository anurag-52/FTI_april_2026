import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Navigation'
import { PageHeader, ErrorMsg, LoadingSpinner, rupee } from '../components/UI'
import { addManualBuy, addManualSell, getPositions, searchStocks } from '../api/client'

export default function ManualEntryPage() {
  const navigate = useNavigate()
  const [type, setType] = useState('BUY') // BUY or SELL
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [openPositions, setOpenPositions] = useState([])

  // BUY fields
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [price, setPrice] = useState('')
  const [qty, setQty] = useState('')
  const [notes, setNotes] = useState('')

  // SELL fields
  const [sellPositionId, setSellPositionId] = useState('')
  const [sellQty, setSellQty] = useState('')
  const [sellPrice, setSellPrice] = useState('')

  useEffect(() => {
    getPositions().then(d => setOpenPositions(d.open || [])).catch(console.error)
  }, [])

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const t = setTimeout(() => {
      searchStocks(query).then(setResults).catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const handleBuy = async () => {
    if (!selected) return setError('Select a stock')
    if (!price || !qty) return setError('Enter price and quantity')
    setError('')
    setLoading(true)
    try {
      await addManualBuy({ stock_id: selected.id, entry_date: date, entry_price: parseFloat(price), quantity: parseInt(qty), notes })
      navigate('/portfolio')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to add position')
    } finally {
      setLoading(false)
    }
  }

  const handleSell = async () => {
    if (!sellPositionId) return setError('Select a position')
    if (!sellPrice || !sellQty) return setError('Enter sell price and quantity')
    setError('')
    setLoading(true)
    try {
      await addManualSell({ position_id: sellPositionId, exit_price: parseFloat(sellPrice), quantity: parseInt(sellQty) })
      navigate('/portfolio')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to record sale')
    } finally {
      setLoading(false)
    }
  }

  const totalCost = price && qty ? (parseFloat(price) * parseInt(qty)) : 0

  return (
    <Layout>
      <PageHeader title="Manual Entry" showBack />

      {/* BUY/SELL toggle */}
      <div className="px-4 py-3 flex gap-2">
        {['BUY', 'SELL'].map(t => (
          <button key={t} onClick={() => { setType(t); setError('') }}
            className={`flex-1 py-2 rounded-btn text-sm font-semibold transition-colors
              ${type === t ? (t === 'BUY' ? 'bg-success text-white' : 'bg-danger text-white') : 'bg-white border border-border text-muted'}`}>
            {t === 'BUY' ? '📈 Manual Buy' : '📉 Manual Sell'}
          </button>
        ))}
      </div>

      <div className="px-4 space-y-4">
        {type === 'BUY' ? (
          <>
            {/* Stock search */}
            <div>
              <label className="label">Stock</label>
              {selected ? (
                <div className="input flex items-center justify-between">
                  <span className="font-medium">{selected.ticker_nse} · {selected.company_name}</span>
                  <button onClick={() => { setSelected(null); setQuery('') }} className="text-muted text-xs">✕ Clear</button>
                </div>
              ) : (
                <>
                  <input className="input" placeholder="Search by ticker or name..."
                    value={query} onChange={e => setQuery(e.target.value)} />
                  {results.length > 0 && (
                    <div className="border border-border rounded-btn mt-1 overflow-hidden shadow-card">
                      {results.map(r => (
                        <button key={r.id} onClick={() => { setSelected(r); setQuery('') }}
                          className="w-full text-left px-3 py-2.5 hover:bg-gray-50 border-b border-border last:border-0 text-sm">
                          <span className="font-medium">{r.ticker_nse}</span>
                          <span className="text-muted ml-2">{r.company_name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
            <div>
              <label className="label">Date</label>
              <input type="date" className="input" value={date} onChange={e => setDate(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Price (₹)</label>
                <input type="number" inputMode="decimal" className="input" placeholder="0.00"
                  value={price} onChange={e => setPrice(e.target.value)} />
              </div>
              <div>
                <label className="label">Quantity</label>
                <input type="number" inputMode="numeric" className="input" placeholder="0"
                  value={qty} onChange={e => setQty(e.target.value)} />
              </div>
            </div>
            {totalCost > 0 && (
              <div className="bg-blue-50 rounded-btn px-3 py-2 text-sm text-brand font-medium">
                Total Cost: {rupee(totalCost)}
              </div>
            )}
            <div>
              <label className="label">Notes (optional)</label>
              <input className="input" placeholder="Reason for manual entry..." value={notes} onChange={e => setNotes(e.target.value)} />
            </div>
            <ErrorMsg msg={error} />
            <button onClick={handleBuy} disabled={loading} className="btn-success flex items-center justify-center gap-2">
              {loading ? <LoadingSpinner size="sm" /> : null}
              Record Buy
            </button>
          </>
        ) : (
          <>
            <div>
              <label className="label">Select Open Position</label>
              <select className="input" value={sellPositionId} onChange={e => setSellPositionId(e.target.value)}>
                <option value="">Choose position...</option>
                {openPositions.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.stock?.ticker_nse} · {p.quantity} shares @ ₹{p.entry_price?.toFixed(2)}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Sell Price (₹)</label>
                <input type="number" inputMode="decimal" className="input" placeholder="0.00"
                  value={sellPrice} onChange={e => setSellPrice(e.target.value)} />
              </div>
              <div>
                <label className="label">Quantity</label>
                <input type="number" inputMode="numeric" className="input" placeholder="0"
                  value={sellQty} onChange={e => setSellQty(e.target.value)} />
              </div>
            </div>
            <ErrorMsg msg={error} />
            <button onClick={handleSell} disabled={loading} className="btn-danger flex items-center justify-center gap-2">
              {loading ? <LoadingSpinner size="sm" /> : null}
              Record Sale
            </button>
          </>
        )}
      </div>
    </Layout>
  )
}
