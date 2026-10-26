import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell, CheckCircle2, Briefcase, Brain, AlertTriangle, DollarSign, FileText,
} from 'lucide-react'
import { clsx } from 'clsx'
import { notificationService } from '../../services'
import { formatRelativeTime } from '../../utils/helpers'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'

const filters = [
  ['all', 'All'], ['unread', 'Unread'], ['claim', 'Claims'],
  ['ai_assessment', 'AI'], ['fraud_alert', 'Fraud'], ['payment', 'Payments'],
  ['policy', 'Policies'],
]

const iconFor = (type) => {
  if (type === 'claim') return <Briefcase className="w-5 h-5 text-blue-600" />
  if (type === 'ai_assessment') return <Brain className="w-5 h-5 text-purple-600" />
  if (type === 'fraud_alert') return <AlertTriangle className="w-5 h-5 text-red-600" />
  if (type === 'payment') return <DollarSign className="w-5 h-5 text-emerald-600" />
  return <FileText className="w-5 h-5 text-gray-600" />
}

const fallbackLink = (notification) => {
  if (notification.link) return notification.link
  const type = notification.related_object_type?.toLowerCase()
  if (type?.includes('claim')) return `/claims/${notification.related_object_id}`
  if (type?.includes('policy')) return `/policies/${notification.related_object_id}`
  if (type?.includes('vehicle')) return `/vehicles/${notification.related_object_id}`
  return '/dashboard'
}

export function Notifications() {
  const [notifications, setNotifications] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')

  const loadNotifications = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await notificationService.getNotifications()
      setNotifications(Array.isArray(response) ? response : response.results || [])
    } catch (err) {
      setNotifications([])
      setError(err.response?.data?.detail || 'Could not load notifications. Check the backend connection and try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadNotifications() }, [loadNotifications])

  const markAllRead = async () => {
    setSavingId('all')
    setError('')
    try {
      await notificationService.markAllRead()
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })))
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not mark notifications as read.')
    } finally {
      setSavingId(null)
    }
  }

  const markRead = async (id) => {
    setSavingId(id)
    try {
      await notificationService.markRead(id)
      setNotifications((items) => items.map((item) => item.id === id ? { ...item, is_read: true } : item))
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update this notification.')
    } finally {
      setSavingId(null)
    }
  }

  const filtered = notifications.filter((notification) => {
    if (filter === 'unread') return !notification.is_read
    return filter === 'all' || notification.notification_type === filter
  })

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Notification Center</h1>
          <p className="page-subtitle">In-app updates for claims, policies, and assessments</p>
        </div>
        <Button variant="secondary" onClick={markAllRead} disabled={savingId === 'all' || !notifications.some((item) => !item.is_read)}>
          <CheckCircle2 className="w-4 h-4 mr-2" />
          Mark All as Read
        </Button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between"><span>{error}</span><Button variant="outline" size="sm" onClick={loadNotifications}>Retry</Button></div>}

      <Card>
        <CardHeader
          title="Your Notifications"
          action={<div className="flex gap-1 flex-wrap text-xs">{filters.map(([value, label]) => (
            <button key={value} type="button" onClick={() => setFilter(value)} className={clsx('px-2.5 py-1 rounded-md font-semibold transition', filter === value ? 'bg-primary text-white' : 'text-gray-500 hover:bg-gray-100')}>{label}</button>
          ))}</div>}
        />
        <CardContent className="p-0">
          {loading ? <div className="py-12 text-center text-gray-500">Loading notifications…</div> : filtered.length ? (
            <div className="divide-y divide-gray-100">
              {filtered.map((notification) => {
                const link = fallbackLink(notification)
                return <div key={notification.id} className={clsx('p-4 flex items-start justify-between gap-4 transition hover:bg-gray-50/80', !notification.is_read && 'bg-blue-50/40')}>
                  <div className="flex items-start gap-3.5">
                    <div className="w-10 h-10 rounded-xl bg-white border border-gray-200 shadow-sm flex items-center justify-center flex-shrink-0">{iconFor(notification.notification_type)}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <Link to={link} onClick={() => !notification.is_read && markRead(notification.id)} className="font-semibold text-gray-900 text-sm hover:text-primary hover:underline">{notification.title}</Link>
                        {!notification.is_read && <span className="w-2 h-2 rounded-full bg-blue-600" />}
                      </div>
                      <p className="text-sm text-gray-600 mt-0.5">{notification.message}</p>
                      <span className="text-xs text-gray-400 mt-1 block">{formatRelativeTime(notification.sent_at)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link to={link} onClick={() => !notification.is_read && markRead(notification.id)} className="btn btn-secondary btn-sm">View</Link>
                    {!notification.is_read && <Button variant="outline" size="sm" disabled={savingId === notification.id} onClick={() => markRead(notification.id)}>Mark read</Button>}
                  </div>
                </div>
              })}
            </div>
          ) : <div className="text-center py-12 text-gray-400 text-sm"><Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />No notifications in this category.</div>}
        </CardContent>
      </Card>
    </div>
  )
}

export default Notifications
