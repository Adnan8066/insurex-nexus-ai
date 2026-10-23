import { useEffect, useState } from 'react'
import { ArrowLeft, Mail, Phone, ShieldCheck, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { authService } from '../../services/authService'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'

const roleLabel = (role) => role === 'admin' ? 'Administrator' : 'Customer support agent'

export function Support() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    authService.getSupportContacts()
      .then((results) => { if (active) setContacts(results) })
      .catch(() => { if (active) setError('We couldn’t load the support contacts. Please try again later.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-3">
            <Link to="/dashboard"><ArrowLeft className="mr-2 h-4 w-4" />Back to dashboard</Link>
          </Button>
          <h1 className="page-title">Contact support</h1>
          <p className="page-subtitle">Reach an InsureX administrator or customer support agent directly.</p>
        </div>
      </div>

      <Card className="mb-6 border-blue-100 bg-blue-50/60">
        <CardContent className="flex items-start gap-4 p-5">
          <div className="rounded-xl bg-white p-3 text-blue-700"><ShieldCheck className="h-6 w-6" /></div>
          <div>
            <h2 className="font-semibold text-slate-900">We’re here to help</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">For questions about a claim, include your claim number in your email so our team can help you faster.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader title="Your support team" subtitle="Choose a contact to email or call" />
        <CardContent>
          {loading ? <p className="py-8 text-center text-slate-500" role="status">Loading support contacts…</p> : null}
          {!loading && error ? <p className="py-8 text-center text-red-700" role="alert">{error}</p> : null}
          {!loading && !error && contacts.length === 0 ? (
            <div className="py-8 text-center">
              <Users className="mx-auto h-8 w-8 text-slate-400" />
              <p className="mt-3 font-medium text-slate-800">No support contacts are available right now.</p>
              <p className="mt-1 text-sm text-slate-500">Please check back later or contact us through your claim details.</p>
            </div>
          ) : null}
          {!loading && !error && contacts.length > 0 ? (
            <ul className="grid gap-4 sm:grid-cols-2">
              {contacts.map((contact) => (
                <li key={contact.id} className="rounded-xl border border-slate-200 p-5">
                  <p className="font-semibold text-slate-900">{contact.name}</p>
                  <p className="mt-1 text-sm text-slate-500">{roleLabel(contact.role)}{contact.department ? ` · ${contact.department}` : ''}</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <a className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-900" href={`mailto:${contact.email}?subject=${encodeURIComponent('InsureX customer support request')}`}>
                      <Mail className="h-4 w-4" />{contact.email}
                    </a>
                    {contact.phone ? <a className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-slate-900" href={`tel:${contact.phone}`}><Phone className="h-4 w-4" />{contact.phone}</a> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}

export default Support
