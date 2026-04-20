import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Layout } from '../../components/Navigation'
import { PageHeader, StatusBadge, ErrorMsg, LoadingSpinner, rupee } from '../../components/UI'
import { getAdminUsers, createUser } from '../../api/client'
import { Search, AlertTriangle } from 'lucide-react'


export default function AdminUsersPage() {
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [search, setSearch]   = useState('')
  const [error, setError]     = useState('')
  const [creating, setCreating] = useState(false)
  const [createdCreds, setCreatedCreds] = useState(null)

  // New user form
  const [form, setForm] = useState({ full_name: '', email: '', mobile: '', starting_capital: '', risk_percent: '1.0' })

  const load = () => {
    setLoading(true)
    getAdminUsers().then(setUsers).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = users.filter(u =>
    u.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreate = async () => {
    setError('')
    if (!form.full_name || !form.email) return setError('Name and email are required')
    setCreating(true)
    try {
      const resp = await createUser({
        full_name: form.full_name,
        email: form.email,
        mobile: form.mobile,
        starting_capital: parseFloat(form.starting_capital) || 0,
        risk_percent: parseFloat(form.risk_percent) || 1.0,
      })
      setCreatedCreds({ email: form.email, tempPassword: resp.temp_password })
      setForm({ full_name: '', email: '', mobile: '', starting_capital: '', risk_percent: '1.0' })
      setShowForm(false)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create user')
    } finally {
      setCreating(false)
    }
  }

  const statusCounts = {
    active: users.filter(u => u.status === 'active').length,
    paused: users.filter(u => u.status === 'paused').length,
    suspended: users.filter(u => u.status === 'suspended').length,
  }

  return (
    <Layout>
      <PageHeader
        title="Traders"
        subtitle={`${users.length} total`}
        right={
          <button onClick={() => { setShowForm(!showForm); setCreatedCreds(null) }} className="btn-primary !w-auto px-4 py-2 text-sm">
            + New Trader
          </button>
        }
      />

      {/* Stats strip */}
      <div className="px-4 py-2 flex gap-3">
        <div className="badge-active">{statusCounts.active} Active</div>
        <div className="badge-paused">{statusCounts.paused} Paused</div>
        <div className="badge-suspended">{statusCounts.suspended} Suspended</div>
      </div>

      {/* Success alert for new user */}
      {createdCreds && (
        <div className="mx-4 mb-4 p-4 rounded-xl border border-brand bg-brand/5 text-sm">
          <h3 className="font-bold text-brand mb-1">User Created Successfully!</h3>
          <p className="text-text mb-2">The system has generated a temporary password. The user will be forced to change it upon first login.</p>
          <div className="bg-white/80 dark:bg-black/20 p-3 rounded-lg flex flex-col gap-1 border border-border mt-3">
            <div><span className="text-muted w-24 inline-block">Email:</span> <span className="font-medium text-text select-all">{createdCreds.email}</span></div>
            <div><span className="text-muted w-24 inline-block">Password:</span> <span className="font-mono text-brand font-bold bg-brand/10 px-2 py-0.5 rounded select-all">{createdCreds.tempPassword}</span></div>
          </div>
          <button onClick={() => setCreatedCreds(null)} className="btn-ghost mt-3 text-xs w-auto px-3 py-1">Dismiss</button>
        </div>
      )}

      {/* Create user form */}
      {showForm && (
        <div className="mx-4 mb-4 card p-4 space-y-3">
          <h3 className="font-semibold text-text">Create New Trader</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="label">Full Name *</label>
              <input className="input" placeholder="Rajesh Kumar"
                value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="label">Email *</label>
              <input type="email" className="input" placeholder="trader@email.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="label">Mobile</label>
              <input className="input" placeholder="+91..."
                value={form.mobile} onChange={e => setForm({ ...form, mobile: e.target.value })} />
            </div>
            <div>
              <label className="label">Starting Capital (₹)</label>
              <input type="number" inputMode="numeric" className="input" placeholder="200000"
                value={form.starting_capital} onChange={e => setForm({ ...form, starting_capital: e.target.value })} />
            </div>
          </div>
          <ErrorMsg msg={error} />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={creating} className="btn-primary flex items-center justify-center gap-2">
              {creating ? <LoadingSpinner size="sm" /> : null} Create
            </button>
            <button onClick={() => { setShowForm(false); setError('') }} className="btn-ghost flex-1">Cancel</button>
          </div>
          <p className="text-xs text-muted">A temporary password will be emailed to the trader. They must change it on first login.</p>
        </div>
      )}

      {/* Search */}
      <div className="px-4 mb-3">
        <input className="input" placeholder="Search traders..."
          value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      {/* Traders list */}
      {loading ? (
        <div className="flex justify-center py-8"><LoadingSpinner /></div>
      ) : (
        <div className="px-4 space-y-2">
          {filtered.map(u => (
            <Link key={u.id} to={`/admin/users/${u.id}`}>
              <div className="card px-4 py-3 flex items-center justify-between hover:border-brand/30 transition-colors">
                <div>
                  <div className="font-semibold text-text text-sm">{u.full_name}</div>
                  <div className="text-xs text-muted">{u.email}</div>
                  <div className="mt-1"><StatusBadge status={u.status} /></div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">{rupee(u.available_capital)}</div>
                  <div className="text-xs text-muted">Available</div>
                  {u.inactivity_days > 0 ? (
                    <div className="text-xs text-danger mt-1 flex items-center gap-0.5"><AlertTriangle className="w-3 h-3" /> {u.inactivity_days}d inactive</div>
                  ) : null}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  )
}
