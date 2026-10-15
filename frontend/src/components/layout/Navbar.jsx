import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Menu,
  X,
  Bell,
  ChevronDown,
  LogOut,
  User,
  Settings,
  Shield,
  Moon,
  Sun,
} from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { notificationService } from '../../services'
import { formatRelativeTime } from '../../utils/helpers'

export function Navbar({ sidebarCollapsed, onToggleSidebar }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [notificationError, setNotificationError] = useState('')
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = window.localStorage.getItem('theme')
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const userMenuRef = useRef(null)
  const notificationsRef = useRef(null)

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
    if (darkMode) {
      document.documentElement.classList.add('dark')
      window.localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      window.localStorage.setItem('theme', 'light')
    }
  }, [darkMode])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) setShowUserMenu(false)
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) setShowNotifications(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
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

  return (
    <header
      className={clsx(
        'fixed top-0 right-0 z-30 h-16 bg-white border-b border-gray-200 transition-all duration-300 flex items-center',
        sidebarCollapsed ? 'left-20' : 'left-72'
      )}
      role="banner"
    >
      <div className="flex items-center justify-between w-full px-4 sm:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100"
            aria-label="Toggle menu"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 flex items-center justify-end gap-4">
          <button
            onClick={() => setDarkMode((current) => !current)}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100"
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>

          <div className="relative" ref={notificationsRef}>
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className={clsx(
                'relative p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors',
                showNotifications && 'bg-gray-100 text-gray-700'
              )}
              aria-label="Notifications"
              aria-expanded={showNotifications}
              aria-haspopup="true"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-gray-200 rounded-lg shadow-lg py-2 z-50">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">Notifications</h3>
                  {unreadCount > 0 && (
                    <button className="text-sm text-primary hover:underline" onClick={markAllNotificationsRead}>Mark all read</button>
                  )}
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notificationError && <p className="px-4 py-3 text-sm text-red-600">{notificationError}</p>}
                  {!notificationError && notifications.length === 0 && <p className="px-4 py-6 text-center text-sm text-gray-500">No notifications yet.</p>}
                  {notifications.map((notification) => (
                    <Link
                      key={notification.id}
                      to={notification.link || '/notifications'}
                      onClick={() => { markNotificationRead(notification); setShowNotifications(false) }}
                      className={clsx(
                        'block px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0 transition-colors',
                        !notification.is_read && 'bg-blue-50'
                      )}
                    >
                      <p className={clsx('text-sm font-medium text-gray-900', !notification.is_read && 'font-semibold')}>
                        {notification.title}
                      </p>
                      <p className="text-sm text-gray-500 mt-0.5">{notification.message}</p>
                      <p className="text-xs text-gray-400 mt-1">{formatRelativeTime(notification.sent_at)}</p>
                    </Link>
                  ))}
                </div>
                <div className="px-4 py-3 border-t border-gray-200">
                  <Link
                    to="/notifications"
                    className="block text-center text-sm font-medium text-primary hover:underline"
                    onClick={() => setShowNotifications(false)}
                  >
                    View all notifications
                  </Link>
                </div>
              </div>
            )}
          </div>

          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className={clsx(
                'flex items-center gap-2 p-1.5 rounded-lg hover:bg-gray-100 transition-colors',
                showUserMenu && 'bg-gray-100'
              )}
              aria-label="User menu"
              aria-expanded={showUserMenu}
              aria-haspopup="true"
            >
              <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary" />
              </div>
              <span className="hidden sm:block text-sm font-medium text-gray-700">{user?.name}</span>
              <ChevronDown className="w-4 h-4 text-gray-500" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
                <div className="px-4 py-3 border-b border-gray-200">
                  <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                  <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
                </div>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  onClick={() => setShowUserMenu(false)}
                >
                  <User className="w-4 h-4" />
                  Profile
                </Link>
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  onClick={() => setShowUserMenu(false)}
                >
                  <Settings className="w-4 h-4" />
                  Settings
                </Link>
                <hr className="my-1 border-gray-200" />
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Navbar
