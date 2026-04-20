import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth, AuthProvider } from './hooks/useAuth'

// Lazy-load all pages for code-splitting
const LoginPage = lazy(() => import('./pages/LoginPage'))
const FirstLoginPage = lazy(() => import('./pages/FirstLoginPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ConfirmPage = lazy(() => import('./pages/ConfirmPage'))
const PortfolioPage = lazy(() => import('./pages/PortfolioPage'))
const ManualEntryPage = lazy(() => import('./pages/ManualEntryPage'))
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'))
const BacktestPage = lazy(() => import('./pages/BacktestPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const AdminUsersPage = lazy(() => import('./pages/admin/AdminUsersPage'))
const AdminUserDetailPage = lazy(() => import('./pages/admin/AdminUserDetailPage'))
const AdminSystemPage = lazy(() => import('./pages/admin/AdminSystemPage'))
const AdminProfilePage = lazy(() => import('./pages/admin/AdminProfilePage'))

function LoadingSpinner() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-4 border-brand border-t-transparent rounded-full animate-spin" />
        <p className="text-muted text-sm">Loading...</p>
      </div>
    </div>
  )
}

// Route guard: redirect to login if not authenticated
function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  if (!user) return <Navigate to="/login" replace />
  if (!user.first_login_complete) return <Navigate to="/first-login" replace />
  return children
}

// Admin-only route guard
function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<LoadingSpinner />}>
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
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
