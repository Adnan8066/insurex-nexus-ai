import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, MinusCircle, Circle } from 'lucide-react'
import { investigationService } from '../../services'
import { formatApiError } from '../../services/api'
import { Card, CardHeader, CardContent } from '../ui/Card'
import { Alert } from '../ui/Alert'
import { formatRelativeTime } from '../../utils/helpers'

const RESULT_DISPLAY = {
  pass: { icon: CheckCircle2, className: 'text-emerald-600', label: 'Pass' },
  fail: { icon: XCircle, className: 'text-red-600', label: 'Fail' },
  na: { icon: MinusCircle, className: 'text-gray-400', label: 'Not applicable' },
}

// Read-only view of the investigator's fixed vehicle checklist for one claim.
// Shown to admins and employees (and the investigator) on the claim page.
// Renders nothing when the claim has no investigation.
export function VehicleChecksPanel({ claimId }) {
  const [state, setState] = useState({ loading: true, error: null, investigation: null, data: null })

  useEffect(() => {
    let active = true
    const load = async () => {
      setState({ loading: true, error: null, investigation: null, data: null })
      try {
        const list = await investigationService.getInvestigations({ claim: claimId })
        const rows = Array.isArray(list) ? list : (list.results || [])
        const investigation = rows[0]
        if (!investigation) {
          if (active) setState({ loading: false, error: null, investigation: null, data: null })
          return
        }
        const data = await investigationService.getVehicleChecks(investigation.id)
        if (active) setState({ loading: false, error: null, investigation, data })
      } catch (err) {
        if (active) setState({ loading: false, error: formatApiError(err, 'Could not load the vehicle checks.'), investigation: null, data: null })
      }
    }
    load()
    return () => { active = false }
  }, [claimId])

  if (state.loading || (!state.investigation && !state.error)) return null

  const { investigation, data } = state
  return (
    <Card className="mb-6">
      <CardHeader
        title="Vehicle checks by investigator"
        subtitle={investigation
          ? `${investigation.case_number} • ${investigation.investigator_name || 'Unassigned'}${data ? ` • ${data.completed} of ${data.total} checked` : ''}`
          : undefined}
      />
      <CardContent className="p-6">
        {state.error && <Alert>{state.error}</Alert>}
        {data && (
          <ul className="divide-y divide-gray-100">
            {data.checks.map((check) => {
              const display = check.result ? RESULT_DISPLAY[check.result] : null
              const Icon = display ? display.icon : Circle
              return (
                <li key={check.check_code} className="flex items-start gap-3 py-3">
                  <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${display ? display.className : 'text-gray-300'}`} aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900">{check.check_label}</p>
                    {check.note && <p className="mt-0.5 text-sm text-gray-600">{check.note}</p>}
                    <p className="mt-0.5 text-xs text-gray-500">
                      {display ? (
                        <>
                          <span className="font-semibold">{display.label}</span>
                          {check.checked_by_name && <> • by {check.checked_by_name}</>}
                          {check.checked_at && <> • {formatRelativeTime(check.checked_at)}</>}
                        </>
                      ) : 'Not checked yet'}
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

export default VehicleChecksPanel
