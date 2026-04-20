import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layout } from '../components/Navigation'
import { PageHeader, rupee, PnL, LoadingSpinner, StatCard, EmptyState } from '../components/UI'
import { getPositions } from '../api/client'
import { LineChart } from 'lucide-react'


export default function PortfolioPage() {
  const [data, setData] = useState(null)
  const [tab, setTab]   = useState('open')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPositions().then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  const summary  = data?.summary  || {}
  const open     = data?.open     || []
  const closed   = data?.closed   || []
  const withExit = open.filter(p => p.exit_signal_active)

  return (
    <Layout>
      <PageHeader
        title="Portfolio"
        subtitle={`${open.length} open positions`}
        right={
          <Link to="/portfolio/manual-entry" className="text-brand text-sm font-medium">✏️ Manual</Link>
        }
      />

      {/* Summary sticky card */}
      <div className="px-4 py-3 grid grid-cols-2 gap-3">
        <StatCard label="Invested" value={rupee(summary.total_invested)} color="amber" />
        <StatCard label="Current Value" value={rupee(summary.total_current_value)} color="blue" />
        <StatCard label="Total P&L"
          value={<PnL amount={summary.total_pnl} percent={summary.total_pnl_percent} />}
          color={summary.total_pnl >= 0 ? 'green' : 'red'}
        />
        <StatCard label="Available" value={rupee(summary.available_capital)} color="blue" />
      </div>

      {/* Exit alert banner */}
      {withExit.length > 0 && (
        <div className="mx-4 mb-2">
          <Link to={`/confirm/${data?.session_token}`}>
            <div className="bg-red-50 border border-danger rounded-card px-4 py-3 flex items-center justify-between">
              <div>
                <div className="font-semibold text-danger text-sm">🚨 {withExit.length} Exit Alert{withExit.length > 1 ? 's' : ''}</div>
                <div className="text-xs text-muted">Tap to confirm → {withExit.map(p => p.stock?.ticker_nse).join(', ')}</div>
              </div>
              <span className="text-danger">→</span>
            </div>
          </Link>
        </div>
      )}

      {/* Tabs */}
      <div className="px-4 flex gap-2 mb-3">
        {['open', 'closed'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 rounded-btn text-sm font-medium transition-colors
              ${tab === t ? 'bg-brand text-white' : 'bg-white border border-border text-muted'}`}>
            {t === 'open' ? `Open (${open.length})` : `Closed (${closed.length})`}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-8"><LoadingSpinner /></div>
      )}

      {/* Open positions */}
      {!loading && tab === 'open' && (
        <div className="px-4 space-y-3">
          {open.length === 0 && (
            <EmptyState icon={<LineChart className="w-10 h-10 text-muted" />} title="No open positions"
              subtitle="Buy signals will appear here once confirmed"
              action={<Link to="/watchlist" className="btn-outline !w-auto px-6">Manage Watchlist</Link>}
            />
          )}
          {open.map(pos => (
            <div key={pos.id} className={`card p-4 border-l-4 ${pos.exit_signal_active ? 'border-danger' : 'border-brand'}`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-bold text-text">{pos.stock?.ticker_nse}</div>
                  <div className="text-xs text-muted">{pos.stock?.company_name}</div>
                  {pos.exit_signal_active && (
                    <span className="badge-danger mt-1">🚨 Exit Signal Active</span>
                  )}
                </div>
                <PnL amount={pos.pnl_amount} percent={pos.pnl_percent} />
              </div>
              <div className="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
                <div><span className="text-xs text-muted">Qty</span><br /><span className="font-medium">{pos.quantity}</span></div>
                <div><span className="text-xs text-muted">Entry</span><br /><span className="font-medium">₹{pos.entry_price?.toFixed(2)}</span></div>
                <div><span className="text-xs text-muted">Current</span><br /><span className="font-medium">₹{pos.current_price?.toFixed(2)}</span></div>
                <div><span className="text-xs text-muted">Invested</span><br /><span className="font-medium">{rupee(pos.total_invested)}</span></div>
                <div><span className="text-xs text-muted">Stop Loss</span><br /><span className="font-medium text-danger">₹{pos.trailing_stop?.toFixed(2)}</span></div>
                <div><span className="text-xs text-muted">Days Held</span><br /><span className="font-medium">{pos.days_held}d</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Closed positions */}
      {!loading && tab === 'closed' && (
        <div className="px-4 space-y-3">
          {closed.length === 0 && (
            <EmptyState icon="📋" title="No closed trades yet" />
          )}
          {closed.map(pos => (
            <div key={pos.id} className="card p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-bold text-text">{pos.stock?.ticker_nse}</div>
                  <div className="text-xs text-muted">{pos.exit_date} · {pos.days_held}d held</div>
                </div>
                <PnL amount={pos.pnl_amount} percent={pos.pnl_percent} />
              </div>
              <div className="grid grid-cols-3 gap-x-4 text-sm">
                <div><span className="text-xs text-muted">Entry</span><br /><span className="font-medium">₹{pos.entry_price?.toFixed(2)}</span></div>
                <div><span className="text-xs text-muted">Exit</span><br /><span className="font-medium">₹{pos.exit_price?.toFixed(2)}</span></div>
                <div><span className="text-xs text-muted">Reason</span><br /><span className="font-medium text-xs">{pos.exit_reason?.replace('_', ' ')}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
