import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell,
  CheckCircle2,
  Clock,
  Briefcase,
  Brain,
  AlertTriangle,
  DollarSign,
  FileText,
  Trash2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'

const initialNotifications = [
  {
    id: 1,
    title: 'New Claim Intake Registered',
    message: 'Claim #CLM-2024-001234 has been submitted and entered the intake queue.',
    time: '5 min ago',
    type: 'claim',
    unread: true,
    link: '/claims/CLM-2024-001234',
  },
  {
    id: 2,
    title: 'AI Assessment Inference Complete',
    message: 'ML assessment for claim #CLM-2024-001230 is ready. Predicted cost: $2,950.',
    time: '45 min ago',
    type: 'ai',
    unread: true,
    link: '/ai-assessment?claim=CLM-2024-001230',
  },
  {
    id: 3,
    title: 'High Fraud Risk Alert Flagged',
    message: 'Claim #CLM-2024-001235 triggered 87% fraud risk score. SIU investigation recommended.',
    time: '2 hours ago',
    type: 'fraud',
    unread: true,
    link: '/fraud',
  },
  {
    id: 4,
    title: 'Settlement Disbursement Executed',
    message: 'Disbursement of $44,500 for settlement #SET-2023-008542 confirmed via ACH.',
    time: '1 day ago',
    type: 'payment',
    unread: false,
    link: '/settlements',
  },
  {
    id: 5,
    title: 'Policy Renewal Approaching',
    message: 'Auto policy #POL-2024-005678 is scheduled for renewal in 30 days.',
    time: '3 days ago',
    type: 'policy',
    unread: false,
    link: '/policies/POL-2024-005678',
  },
]

export function Notifications() {
  const [notifications, setNotifications] = useState(initialNotifications)
  const [filter, setFilter] = useState('all')

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })))
  }

  const clearNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  const filtered = notifications.filter((n) => {
    if (filter === 'unread') return n.unread
    if (filter !== 'all') return n.type === filter
    return true
  })

  const getIcon = (type) => {
    switch (type) {
      case 'claim':
        return <Briefcase className="w-5 h-5 text-blue-600" />
      case 'ai':
        return <Brain className="w-5 h-5 text-purple-600" />
      case 'fraud':
        return <AlertTriangle className="w-5 h-5 text-red-600" />
      case 'payment':
        return <DollarSign className="w-5 h-5 text-emerald-600" />
      default:
        return <FileText className="w-5 h-5 text-gray-600" />
    }
  }

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Notification Center</h1>
          <p className="page-subtitle">Real-time alerts, claim status notifications, and AI decision updates</p>
        </div>

        <div className="flex gap-2">
          <Button variant="secondary" onClick={markAllRead}>
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Mark All as Read
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader
          title="Recent Activity Notifications"
          action={
            <div className="flex gap-1 text-xs">
              {['all', 'unread', 'claim', 'ai', 'fraud'].map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className={clsx(
                    'px-2.5 py-1 rounded-md uppercase font-semibold transition',
                    filter === f ? 'bg-primary text-white' : 'text-gray-500 hover:bg-gray-100'
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
          }
        />
        <CardContent className="p-0">
          <div className="divide-y divide-gray-100">
            {filtered.length > 0 ? (
              filtered.map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    'p-4 flex items-start justify-between gap-4 transition hover:bg-gray-50/80',
                    n.unread && 'bg-blue-50/40'
                  )}
                >
                  <div className="flex items-start gap-3.5">
                    <div className="w-10 h-10 rounded-xl bg-white border border-gray-200 shadow-sm flex items-center justify-center flex-shrink-0">
                      {getIcon(n.type)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <Link to={n.link} className="font-semibold text-gray-900 text-sm hover:text-primary hover:underline">
                          {n.title}
                        </Link>
                        {n.unread && (
                          <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-0.5">{n.message}</p>
                      <span className="text-xs text-gray-400 mt-1 block font-mono">{n.time}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link to={n.link} className="btn btn-secondary btn-sm">
                      View
                    </Link>
                    <button
                      type="button"
                      onClick={() => clearNotification(n.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg"
                      title="Dismiss"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-gray-400 text-sm">
                No notifications in this category.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default Notifications
