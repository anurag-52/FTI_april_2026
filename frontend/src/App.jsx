import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth, AuthProvider } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import FirstLoginPage from './pages/FirstLoginPage'
import DashboardPage from './pages/DashboardPage'
import ConfirmPage from './pages/ConfirmPage'
import PortfolioPage from './pages/PortfolioPage'
import ManualEntryPage from './pages/ManualEntryPage'
import WatchlistPage from './pages/WatchlistPage'
import BacktestPage from './pages/BacktestPage'
import ProfilePage from './pages/ProfilePage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AdminUserDetailPage from './pages/admin/AdminUserDetailPage'
import AdminSystemPage from './pages/admin/AdminSystemPage'
import AdminProfilePage from './pages/admin/AdminProfilePage'

// Route guard: redirect to login if not authenticated
function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen bg-bg flex items-center justify-center"><LoadingSpinner /></div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.first_login_complete) return <Navigate to="/first-login" replace />
  return children
}

// Admin-only route guard
function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen bg-bg flex items-center justify-center"><LoadingSpinner /></div>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}

function LoadingSpinner() {
  return (
    <div className="w-8 h-8 border-4 border-brand border-t-transparent rounded-full animate-spin" />
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/confirm/:token" element={<ConfirmPage />} />

        {/* First login (forced) */}
        <Route path="/first-login" element={<FirstLoginPage />} />

        {/* Trader routes */}
        <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
        <Route path="/portfolio" element={<PrivateRoute><PortfolioPage /></PrivateRoute>} />
        <Route path="/portfolio/manual-entry" element={<PrivateRoute><ManualEntryPage /></PrivateRoute>} />
        <Route path="/watchlist" element={<PrivateRoute><WatchlistPage /></PrivateRoute>} />
        <Route path="/backtest" element={<PrivateRoute><BacktestPage /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><ProfilePage /></PrivateRoute>} />

        {/* Admin routes */}
        <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="/admin/users/:id" element={<AdminRoute><AdminUserDetailPage /></AdminRoute>} />
        <Route path="/admin/system" element={<AdminRoute><AdminSystemPage /></AdminRoute>} />
        <Route path="/admin/profile" element={<AdminRoute><AdminProfilePage /></AdminRoute>} />

        {/* Default redirects */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
