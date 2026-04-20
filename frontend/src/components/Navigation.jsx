import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Search, LineChart, LogOut, User, Users, TrendingUp, LayoutDashboard, Settings, BarChart3, Sun, Moon } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'


const traderTabs = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Home' },
  { to: '/portfolio',  icon: LineChart, label: 'Portfolio' },
  { to: '/watchlist',  icon: Search, label: 'Watchlist' },
  { to: '/backtest',   icon: TrendingUp, label: 'Backtest' },
  { to: '/profile',    icon: User, label: 'Profile' },
]

const adminTabs = [
  { to: '/admin/users',   icon: Users, label: 'Users' },
  { to: '/admin/system',  icon: Settings, label: 'System' },
  { to: '/admin/profile', icon: User, label: 'Profile' },
]

// Bottom tab bar — mobile only
export function BottomTabBar() {
  const { user } = useAuth()
  const tabs = user?.role === 'admin' ? adminTabs : traderTabs
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-border z-50 pb-safe md:hidden">
      <div className="flex items-stretch">
        {tabs.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2 text-xs font-medium transition-colors gap-1 min-h-[56px]
               ${isActive ? 'text-brand' : 'text-muted'}`
            }
          >
            <span className="text-lg leading-none"><tab.icon className="w-5 h-5 mx-auto" strokeWidth={1.5} /></span>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

// Left sidebar — desktop only
export function Sidebar() {
  const { user, logout } = useAuth()
  const tabs = user?.role === 'admin' ? adminTabs : traderTabs
  return (
    <aside className="hidden md:flex flex-col w-60 min-h-screen bg-white border-r border-border fixed top-0 left-0 z-40">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-brand"><BarChart3 className="w-6 h-6" strokeWidth={2} /></span>
          <div>
            <div className="font-bold text-text text-sm leading-tight">Channel Breakout</div>
            <div className="text-muted text-xs">Courtney Smith</div>
          </div>
        </div>
      </div>
      {/* Nav items */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {tabs.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm font-medium transition-colors
               ${isActive ? 'bg-brand text-white' : 'text-muted hover:bg-gray-50 hover:text-text'}`
            }
          >
            <span className="w-5 text-center"><tab.icon className="w-5 h-5" strokeWidth={1.5} /></span>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {/* User + Logout */}
      <div className="px-3 py-4 border-t border-border">
        <div className="px-3 py-2 mb-2 flex items-center justify-between">
          <div className="overflow-hidden">
            <div className="text-sm font-medium text-text truncate">{user?.full_name}</div>
            <div className="text-xs text-muted truncate">{user?.email}</div>
          </div>
          <ThemeToggle />
        </div>
        <button onClick={logout} className="btn-ghost w-full text-left flex items-center gap-2">
          <LogOut className="w-4 h-4 ml-1" /> Logout
        </button>
      </div>
    </aside>
  )
}

function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <button onClick={toggleTheme} className="p-2 text-muted hover:text-text rounded-full hover:bg-gray-100 transition-colors">
      {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  )
}

// Layout wrapper combining sidebar + bottom tab bar
export function Layout({ children, title }) {
  return (
    <div className="min-h-screen bg-bg">
      <Sidebar />
      <main className="md:ml-60 pb-20 md:pb-0 page-enter">
        {children}
      </main>
      <BottomTabBar />
    </div>
  )
}
