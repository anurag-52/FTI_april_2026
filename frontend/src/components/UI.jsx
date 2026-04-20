import { AlertTriangle } from 'lucide-react'
// Shared UI components

// Loading spinner
export function LoadingSpinner({ size = 'md' }) {
  const s = size === 'sm' ? 'w-4 h-4 border-2' : size === 'lg' ? 'w-12 h-12 border-4' : 'w-8 h-8 border-4'
  return (
    <div className={`${s} border-brand border-t-transparent rounded-full animate-spin`} />
  )
}

// Full-page loading state
export function PageLoader() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size="lg" />
        <p className="text-muted text-sm">Loading...</p>
      </div>
    </div>
  )
}

// Status badge
export function StatusBadge({ status }) {
  const cls = {
    active:    'badge-active',
    paused:    'badge-paused',
    suspended: 'badge-suspended',
  }[status] || 'badge-active'
  const dot = { active: <div className="w-2 h-2 rounded-full bg-success inline-block"/>, paused: <div className="w-2 h-2 rounded-full bg-warning inline-block"/>, suspended: <div className="w-2 h-2 rounded-full bg-danger inline-block"/> }[status] || <div className="w-2 h-2 rounded-full bg-gray-300 inline-block"/>
  return <span className={cls}>{dot} {status?.charAt(0).toUpperCase() + status?.slice(1)}</span>
}

// Circuit warning badge
export function CircuitBadge({ type }) {
  if (!type) return null
  return (
    <span className="badge-warning">
      <AlertTriangle className="w-5 h-5 inline-block" /> {type === 'UPPER' ? 'Upper Circuit' : 'Lower Circuit'}
    </span>
  )
}

// Gap risk warning badge
export function GapRiskBadge({ pct }) {
  if (!pct) return null
  return (
    <span className="badge-warning">
      <AlertTriangle className="w-5 h-5 inline-block" /> Gap Risk: {pct?.toFixed(1)}% gap down
    </span>
  )
}

// Rupee formatter
export function rupee(val) {
  if (val == null) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val)
}

// P&L display
export function PnL({ amount, percent }) {
  const pos = amount >= 0
  return (
    <span className={pos ? 'pnl-positive' : 'pnl-negative'}>
      {pos ? '+' : ''}{rupee(amount)} ({pos ? '+' : ''}{percent?.toFixed(2)}%)
    </span>
  )
}

// Page header with back button
export function PageHeader({ title, subtitle, right, showBack }) {
  return (
    <div className="bg-white border-b border-border px-4 py-4 flex items-center gap-3">
      {showBack && (
        <button onClick={() => window.history.back()} className="text-muted hover:text-text transition-colors">
          ← 
        </button>
      )}
      <div className="flex-1">
        <h1 className="text-base font-bold text-text">{title}</h1>
        {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
      </div>
      {right && <div>{right}</div>}
    </div>
  )
}

// Empty state
export function EmptyState({ icon, title, subtitle, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="font-semibold text-text mb-1">{title}</h3>
      {subtitle && <p className="text-sm text-muted mb-4">{subtitle}</p>}
      {action}
    </div>
  )
}

// Error message
export function ErrorMsg({ msg }) {
  if (!msg) return null
  return (
    <div className="bg-red-50 border border-red-200 rounded-btn px-3 py-2 text-sm text-danger">
      {msg}
    </div>
  )
}

// Capital summary card
export function StatCard({ label, value, sub, color }) {
  const border = { green: 'border-success', red: 'border-danger', blue: 'border-brand', amber: 'border-amber-500' }[color] || 'border-border'
  return (
    <div className={`card p-4 border-l-4 ${border}`}>
      <div className="text-xs text-muted font-medium mb-1">{label}</div>
      <div className="text-lg font-bold text-text">{value}</div>
      {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
    </div>
  )
}

// Toggle switch
export function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-sm text-text">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-12 h-6 rounded-full transition-colors ${checked ? 'bg-brand' : 'bg-gray-300'}`}
      >
        <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-0.5'}`} />
      </button>
    </label>
  )
}
