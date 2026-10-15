import { useCallback, useEffect, useState } from 'react'
import { Bell, Brain, CheckCircle2, Save, Server } from 'lucide-react'
import { notificationService, assessmentService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'

const preferenceGroups = [
  {
    title: 'Email preferences',
    fields: [
      ['email_claim_updates', 'Claim updates'], ['email_policy_updates', 'Policy updates'],
      ['email_payment_updates', 'Payment updates'], ['email_document_requests', 'Document requests'],
      ['email_ai_assessments', 'AI assessments'], ['email_fraud_alerts', 'Fraud alerts'],
      ['email_settlements', 'Settlement updates'], ['email_marketing', 'Product announcements'],
    ],
  },
  {
    title: 'Push preferences',
    fields: [
      ['push_claim_updates', 'Claim updates'], ['push_policy_updates', 'Policy updates'],
      ['push_payment_updates', 'Payment updates'], ['push_document_requests', 'Document requests'],
      ['push_ai_assessments', 'AI assessments'], ['push_fraud_alerts', 'Fraud alerts'],
      ['push_settlements', 'Settlement updates'],
    ],
  },
]

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

export function Settings() {
  const { user } = useAuth()
  const isStaff = ['employee', 'admin', 'investigator'].includes(user?.role)
  const [preferences, setPreferences] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [preferenceResult, statusResult] = await Promise.allSettled([
        notificationService.getPreferences(),
        isStaff ? assessmentService.getModelStatus() : Promise.resolve(null),
      ])
      if (preferenceResult.status === 'fulfilled') setPreferences(preferenceResult.value)
      else throw preferenceResult.reason
      setModelStatus(statusResult.status === 'fulfilled' ? statusResult.value : null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load your settings. Check the backend connection and try again.')
    } finally {
      setLoading(false)
    }
  }, [isStaff])

  useEffect(() => { load() }, [load])

  const updatePreference = (name, value) => {
    setSaved(false)
    setPreferences((current) => ({ ...current, [name]: value }))
  }

  const handleSave = async (event) => {
    event.preventDefault()
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const updated = await notificationService.updatePreferences(preferences)
      setPreferences(updated)
      setSaved(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save your notification preferences.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Saved notification preferences and live backend/model status</p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>Refresh</Button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl text-sm">{error}</div>}
      {saved && <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm font-medium flex items-center gap-2"><CheckCircle2 className="w-5 h-5" />Preferences saved to your account.</div>}

      <Card>
        <CardHeader title="Backend connection" subtitle="The API URL is supplied by the app environment and cannot be changed from this screen." />
        <CardContent className="p-6">
          <div className="flex items-center gap-3 rounded-xl bg-gray-50 p-4">
            <Server className="w-5 h-5 text-primary" />
            <div className="min-w-0">
              <div className="text-xs text-gray-500">Configured API base URL</div>
              <code className="text-sm text-gray-900 break-all">{apiBase}</code>
            </div>
          </div>
        </CardContent>
      </Card>

      {isStaff && <Card>
        <CardHeader title="Trained model availability" subtitle="Read from the backend model files and training report." />
        <CardContent className="p-6 space-y-4">
          {!modelStatus ? <p className="text-sm text-gray-500">Model status is unavailable. Refresh after the backend is running.</p> : <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(modelStatus.models || {}).map(([name, available]) => (
                <div key={name} className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
                  <span className="text-sm text-gray-700">{name.replaceAll('_', ' ')}</span>
                  <span className={available ? 'text-xs font-semibold text-emerald-700' : 'text-xs font-semibold text-red-700'}>{available ? 'Available' : 'Unavailable'}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500">Last trained: {modelStatus.trained_at ? new Date(modelStatus.trained_at).toLocaleString() : 'No training report found.'}</p>
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900 flex gap-2"><Brain className="w-4 h-4 flex-shrink-0 mt-0.5" />Training data and label caveats apply; predictions are review aids and do not make claim decisions.</div>
          </>}
        </CardContent>
      </Card>}

      <form onSubmit={handleSave}>
        <Card>
          <CardHeader title="Notification preferences" subtitle="These choices are stored on your account. Email and push delivery require those channels to be configured by the service." />
          <CardContent className="p-6 space-y-6">
            {loading || !preferences ? <p className="text-sm text-gray-500">Loading preferences…</p> : <>
              {preferenceGroups.map((group) => <section key={group.title}>
                <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2"><Bell className="w-4 h-4 text-primary" />{group.title}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {group.fields.map(([name, label]) => <label key={name} className="flex items-center justify-between rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
                    {label}<input type="checkbox" checked={Boolean(preferences[name])} onChange={(event) => updatePreference(name, event.target.checked)} className="w-4 h-4 text-primary rounded" />
                  </label>)}
                </div>
              </section>)}
              <label className="flex items-center justify-between rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
                SMS urgent notifications only<input type="checkbox" checked={Boolean(preferences.sms_urgent_only)} onChange={(event) => updatePreference('sms_urgent_only', event.target.checked)} className="w-4 h-4 text-primary rounded" />
              </label>
              <Button type="submit" variant="primary" loading={saving} disabled={saving}><Save className="w-4 h-4 mr-2" />Save Preferences</Button>
            </>}
          </CardContent>
        </Card>
      </form>
    </div>
  )
}

export default Settings
