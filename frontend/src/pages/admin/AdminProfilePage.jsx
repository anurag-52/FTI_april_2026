import { useState } from 'react'
import { Layout } from '../../components/Navigation'
import { PageHeader, ErrorMsg, LoadingSpinner } from '../../components/UI'
import { updateAdminUser, changePassword } from '../../api/client'
import { useAuth } from '../../hooks/useAuth'

export default function AdminProfilePage() {
  const { user, refreshUser, logout } = useAuth()
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError]    = useState('')
  const [name, setName]      = useState(user?.full_name || '')
  const [mobile, setMobile]  = useState(user?.mobile || '')
  const [newPwd, setNewPwd]  = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')

  const showSuccess = (msg) => { setSuccess(msg); setTimeout(() => setSuccess(''), 3000) }

  const saveProfile = async () => {
    setError(''); setLoading(true)
    try {
      await updateAdminUser(user.id, { full_name: name, mobile })
      await refreshUser()
      showSuccess('Profile updated ✅')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  const handlePassword = async () => {
    setError('')
    if (!newPwd || newPwd.length < 8) return setError('Minimum 8 characters')
    if (newPwd !== confirmPwd) return setError('Passwords do not match')
    setLoading(true)
    try {
      await changePassword(newPwd, confirmPwd)
      setNewPwd(''); setConfirmPwd('')
      showSuccess('Password changed ✅')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <PageHeader title="Admin Profile" />
      <div className="px-4 py-4 space-y-6">
        {success && <div className="bg-green-50 border border-success rounded-btn px-3 py-2 text-sm text-success">{success}</div>}
        <ErrorMsg msg={error} />

        {/* Profile */}
        <div className="space-y-4">
          <h2 className="font-semibold text-text">Personal Details</h2>
          <div>
            <label className="label">Full Name</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input bg-gray-50" value={user?.email} disabled />
          </div>
          <div>
            <label className="label">Mobile</label>
            <input className="input" value={mobile} onChange={e => setMobile(e.target.value)} />
          </div>
          <button onClick={saveProfile} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
            {loading ? <LoadingSpinner size="sm" /> : null} Save
          </button>
        </div>

        {/* Password */}
        <div className="space-y-4">
          <h2 className="font-semibold text-text">Change Password</h2>
          <div>
            <label className="label">New Password</label>
            <input type="password" className="input" value={newPwd} onChange={e => setNewPwd(e.target.value)} />
          </div>
          <div>
            <label className="label">Confirm Password</label>
            <input type="password" className="input" value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)} />
          </div>
          <button onClick={handlePassword} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
            {loading ? <LoadingSpinner size="sm" /> : null} Change Password
          </button>
        </div>

        <button onClick={logout} className="btn-outline !border-danger !text-danger">
          🚪 Logout
        </button>
      </div>
    </Layout>
  )
}
