import { useEffect, useRef, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Brain,
  Briefcase,
  Car,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileText,
  GitBranch,
  Gavel,
  LayoutDashboard,
  LogOut,
  Moon,
  Plus,
  Settings,
  Shield,
  Sun,
  User,
  Users,
  Wrench,
} from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { notificationService } from '../../services'
import { formatRelativeTime } from '../../utils/helpers'

const moduleItems = [
  { label: 'Dashboard', to: '/dashboard', Icon: LayoutDashboard, roles: ['customer', 'employee', 'investigator', 'repair', 'admin'] },
  { label: 'Policies', to: '/policies', Icon: FileText, roles: ['customer', 'employee', 'admin'] },
  { label: 'Vehicles', to: '/vehicles', Icon: Car, roles: ['customer', 'employee', 'admin'] },
  { label: 'Claims', to: '/claims', Icon: Briefcase, roles: ['customer', 'employee', 'investigator', 'admin'] },
  { label: 'New Claim', to: '/claims/new', Icon: Plus, roles: ['customer', 'employee', 'admin'] },
  { label: 'AI Assessment', to: '/ai-assessment', Icon: Brain, roles: ['employee', 'investigator', 'admin'] },
  { label: 'Fraud Investigation', to: '/fraud', Icon: AlertTriangle, roles: ['employee', 'investigator', 'admin'] },
  { label: 'Investigators', to: '/investigators', Icon: Users, roles: ['employee', 'admin'] },
  { label: 'Repair Shops', to: '/repair-shops', Icon: Wrench, roles: ['employee', 'repair', 'admin'] },
  { label: 'Settlements', to: '/settlements', Icon: Gavel, roles: ['employee', 'admin'] },
  { label: 'AI Decision Center', to: '/ai-decision', Icon: GitBranch, roles: ['employee', 'admin', 'investigator'] },
  { label: 'Analytics', to: '/analytics', Icon: BarChart3, roles: ['employee', 'admin', 'investigator'] },
  { label: 'AI Operations', to: '/operations', Icon: Cpu, roles: ['employee', 'admin', 'investigator'] },
]

export function Navbar() {
  const { user, logout } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [notificationError, setNotificationError] = useState('')
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = window.localStorage.getItem('theme')
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const moduleNavRef = useRef(null)
  const userMenuRef = useRef(null)
  const notificationsRef = useRef(null)
  const visibleModules = moduleItems.filter((item) => item.roles.includes(user?.role))

  useEffect(() => {
    if (!user?.id) return undefined
    let cancelled = false
    const loadNotifications = async () => {
      try {
        const [listResult, countResult] = await Promise.all([
          notificationService.getNotifications({ page_size: 5 }),
          notificationService.getUnreadCount(),
        ])
        if (cancelled) return
        const rows = Array.isArray(listResult) ? listResult : (listResult.results || [])
        setNotifications(rows.slice(0, 5))
        setUnreadCount(Number(countResult.unread_count) || 0)
        setNotificationError('')
      } catch {
        if (!cancelled) setNotificationError('Could not load notifications.')
      }
    }
    loadNotifications()
    const interval = window.setInterval(loadNotifications, 30000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [user?.id])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    window.localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) setShowUserMenu(false)
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) setShowNotifications(false)
    }
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setShowUserMenu(false)
        setShowNotifications(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const handleLogout = async () => {
    await logout()
  }

  const markAllNotificationsRead = async () => {
    try {
      await notificationService.markAllRead()
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })))
      setUnreadCount(0)
    } catch {
      setNotificationError('Could not mark notifications as read.')
    }
  }

  const markNotificationRead = async (notification) => {
    if (notification.is_read) return
    try {
      await notificationService.markRead(notification.id)
      setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item))
      setUnreadCount((count) => Math.max(0, count - 1))
    } catch {
      setNotificationError('Could not update this notification.')
    }
  }

  const scrollModules = (direction) => {
    moduleNavRef.current?.scrollBy({ left: direction * 300, behavior: 'smooth' })
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 shadow-sm shadow-slate-900/[0.03] backdrop-blur" role="banner">
      <div className="mx-auto flex min-h-16 max-w-[1600px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <Link to="/dashboard" className="flex shrink-0 items-center gap-2.5" aria-label="InsureX dashboard">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm shadow-blue-600/20"><Shield className="h-5 w-5" /></span>
          <span className="text-base font-extrabold tracking-tight text-slate-950 sm:text-lg">InsureX <span className="text-blue-600">Nexus AI</span></span>
        </Link>

        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <button onClick={() => setDarkMode((current) => !current)} className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900" aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          <div className="relative" ref={notificationsRef}>
            <button onClick={() => setShowNotifications((current) => !current)} className={`relative rounded-full p-2 transition ${showNotifications ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`} aria-label="Notifications" aria-expanded={showNotifications} aria-haspopup="true">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">{unreadCount > 9 ? '9+' : unreadCount}</span>}
            </button>
            {showNotifications && (
              <div className="absolute right-0 z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10">
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <h2 className="font-bold text-slate-900">Notifications</h2>
                  {unreadCount > 0 && <button className="text-xs font-semibold text-blue-700 hover:underline" onClick={markAllNotificationsRead}>Mark all read</button>}
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notificationError && <p className="px-4 py-3 text-sm text-rose-600">{notificationError}</p>}
                  {!notificationError && notifications.length === 0 && <p className="px-4 py-6 text-center text-sm text-slate-500">No notifications yet.</p>}
                  {notifications.map((notification) => (
                    <Link key={notification.id} to={notification.link || '/notifications'} onClick={() => { markNotificationRead(notification); setShowNotifications(false) }} className={`block border-b border-slate-100 px-4 py-3 transition last:border-0 hover:bg-slate-50 ${!notification.is_read ? 'bg-blue-50/70' : ''}`}>
                      <p className="text-sm font-semibold text-slate-900">{notification.title}</p>
                      <p className="mt-0.5 text-sm text-slate-600">{notification.message}</p>
                      <p className="mt-1 text-xs text-slate-400">{formatRelativeTime(notification.sent_at)}</p>
                    </Link>
                  ))}
                </div>
                <Link to="/notifications" className="block border-t border-slate-100 px-4 py-3 text-center text-sm font-bold text-blue-700 hover:bg-slate-50" onClick={() => setShowNotifications(false)}>View all notifications</Link>
              </div>
            )}
          </div>

          <div className="relative" ref={userMenuRef}>
            <button onClick={() => setShowUserMenu((current) => !current)} className="flex items-center gap-1 rounded-full py-1 pl-1 pr-1.5 transition hover:bg-slate-100 sm:gap-2 sm:pr-2" aria-label="User menu" aria-expanded={showUserMenu} aria-haspopup="true">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700"><User className="h-4 w-4" /></span>
              <span className="hidden max-w-32 truncate text-sm font-semibold text-slate-700 sm:block">{user?.name}</span>
              <ChevronDown className="hidden h-4 w-4 text-slate-500 sm:block" />
            </button>
            {showUserMenu && <div className="absolute right-0 z-50 mt-3 w-52 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-900/10">
              <div className="border-b border-slate-100 px-3 py-2"><p className="truncate text-sm font-bold text-slate-900">{user?.name}</p><p className="text-xs capitalize text-slate-500">{user?.role}</p></div>
              <Link to="/profile" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setShowUserMenu(false)}><User className="h-4 w-4" />Profile</Link>
              {user?.role === 'admin' && <Link to="/settings" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setShowUserMenu(false)}><Settings className="h-4 w-4" />Settings</Link>}
              <button onClick={handleLogout} className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-rose-600 hover:bg-rose-50"><LogOut className="h-4 w-4" />Sign out</button>
            </div>}
          </div>
        </div>
      </div>

      <div className="border-t border-slate-100">
        <div className="mx-auto flex max-w-[1600px] items-center px-1 sm:px-4 lg:px-6">
          <button onClick={() => scrollModules(-1)} className="shrink-0 rounded-full p-1.5 text-slate-500 hover:bg-slate-100 hover:text-blue-700" aria-label="Scroll modules left"><ChevronLeft className="h-4 w-4" /></button>
          <nav ref={moduleNavRef} className="module-nav-scroll flex min-w-0 flex-1 items-center gap-1 overflow-x-auto overscroll-x-contain scroll-smooth px-2 py-2" aria-label="Dashboard modules">
            {visibleModules.map(({ label, to, Icon }) => (
              <NavLink
                key={label}
                to={to}
                end={to === '/dashboard'}
                title={label}
                className={({ isActive }) => `flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-bold transition sm:px-3.5 sm:text-sm ${isActive ? 'bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-100' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'}`}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <button onClick={() => scrollModules(1)} className="shrink-0 rounded-full p-1.5 text-slate-500 hover:bg-slate-100 hover:text-blue-700" aria-label="Scroll modules right"><ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>
    </header>
  )
}

export default Navbar
