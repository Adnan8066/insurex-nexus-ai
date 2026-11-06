import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckSquare, Square, Scale } from 'lucide-react'
import { policyService } from '../../services'
import { formatApiError } from '../../services/api'
import { formatCurrency } from '../../utils/helpers'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

const MAX_COMPARE = 3

const yesNo = (value) => (value ? 'Yes' : 'No')

export function PlanCompare() {
  const [plans, setPlans] = useState([])
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedIds, setSelectedIds] = useState([])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const data = await policyService.getPlans()
        if (!cancelled) {
          setPlans(data.plans || [])
          setNotice(data.notice || '')
        }
      } catch (err) {
        if (!cancelled) setError(formatApiError(err, 'Could not load the insurance plans.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const toggle = (planId) => {
    setSelectedIds((current) => {
      if (current.includes(planId)) return current.filter((id) => id !== planId)
      if (current.length >= MAX_COMPARE) return current
      return [...current, planId]
    })
  }

  const selected = plans.filter((plan) => selectedIds.includes(plan.id))

  const comparisonRows = [
    ['Estimated annual premium', (plan) => formatCurrency(plan.base_premium_estimate_inr, 'INR', 'en-IN')],
    ['Deductible', (plan) => (plan.deductible_inr ? formatCurrency(plan.deductible_inr, 'INR', 'en-IN') : 'Nil')],
    ['Maximum claim amount', (plan) => formatCurrency(plan.max_claim_inr, 'INR', 'en-IN')],
    ['Own damage cover', (plan) => yesNo(plan.own_damage_cover)],
    ['Roadside assistance', (plan) => yesNo(plan.roadside_assistance)],
    ['Coverage', (plan) => plan.coverage_sections.join('; ')],
    ['Mandatory covers', (plan) => plan.mandatory_covers.join('; ')],
    ['Add-ons available', (plan) => plan.addons.join(', ') || 'None'],
  ]

  return (
    <div className="page mx-auto max-w-6xl space-y-6">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-700"><Scale className="h-6 w-6" /></div>
          <div>
            <h1 className="page-title">Insurance plans</h1>
            <p className="page-subtitle">View the plans and compare up to {MAX_COMPARE} side by side.</p>
          </div>
        </div>
      </div>

      {notice && <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{notice}</p>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div>}

      {loading ? <LoadingSpinner /> : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {plans.map((plan) => {
              const isSelected = selectedIds.includes(plan.id)
              const isFull = !isSelected && selectedIds.length >= MAX_COMPARE
              return (
                <Card key={plan.id}>
                  <CardHeader title={plan.name} subtitle={plan.category} />
                  <CardContent className="space-y-3">
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(plan.base_premium_estimate_inr, 'INR', 'en-IN')}
                      <span className="text-sm font-normal text-gray-500"> / year (estimate)</span>
                    </p>
                    <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
                      {plan.coverage_sections.map((section) => <li key={section}>{section}</li>)}
                    </ul>
                    <button
                      type="button"
                      onClick={() => toggle(plan.id)}
                      disabled={isFull}
                      aria-pressed={isSelected}
                      className="flex items-center gap-2 text-sm font-medium text-primary disabled:text-gray-400"
                    >
                      {isSelected ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
                      {isSelected ? 'Selected for comparison' : isFull ? 'Comparison is full' : 'Add to comparison'}
                    </button>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {selected.length >= 2 && (
            <Card>
              <CardHeader title="Side-by-side comparison" subtitle="Figures are sample estimates for this demonstration." />
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-gray-500">
                        <th className="py-3 pr-4 font-medium">Feature</th>
                        {selected.map((plan) => <th key={plan.id} className="py-3 pr-4 font-medium text-gray-900">{plan.name}</th>)}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {comparisonRows.map(([label, render]) => (
                        <tr key={label}>
                          <th className="py-3 pr-4 font-medium text-gray-600">{label}</th>
                          {selected.map((plan) => <td key={plan.id} className="py-3 pr-4 text-gray-800">{render(plan)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-gray-600">To get a quote, choose the vehicle you want to insure. Staff review your request before a policy is issued.</p>
            <Button asChild><Link to="/vehicles">Choose a vehicle</Link></Button>
          </div>
        </>
      )}
    </div>
  )
}

export default PlanCompare
