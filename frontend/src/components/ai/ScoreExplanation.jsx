import { AlertTriangle, IndianRupee, TrendingDown } from 'lucide-react'
import { Card, CardHeader, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'

const SOURCE_VARIANT = { 'claim history': 'warning', photos: 'danger', 'AI model': 'neutral' }

function Section({ icon: Icon, iconClass, title, summary, children }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${iconClass}`}>
        <Icon className="w-4 h-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">{title}</h4>
        <p className="text-sm text-gray-900 mt-0.5">{summary}</p>
        {children}
      </div>
    </div>
  )
}

function Details({ items }) {
  if (!items?.length) return null
  return (
    <ul className="mt-1.5 space-y-0.5 text-xs text-gray-600 list-disc pl-4">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  )
}

/**
 * Plain-language reasons behind a claim's AI scores (ClaimAssessment.explanation).
 * Renders nothing for assessments made before explanations existed.
 */
export function ScoreExplanation({ explanation, className }) {
  if (!explanation?.summary) return null
  const { fraud = {}, repair_cost: cost = {}, total_loss: loss = {} } = explanation
  const reasons = fraud.reasons || []

  return (
    <Card className={className}>
      <CardHeader title="Why these scores" subtitle="What the AI saw in this claim, in plain language" />
      <CardContent className="p-6 space-y-5">
        <Section icon={AlertTriangle} iconClass="bg-amber-100 text-amber-700" title="Fraud risk" summary={fraud.summary}>
          {reasons.length > 0 && (
            <ul className="mt-2 space-y-1.5">
              {reasons.map((reason) => (
                <li key={reason.text} className="flex flex-wrap items-center gap-2 text-xs text-gray-700">
                  <span className="font-mono font-semibold text-red-700">+{Math.round(reason.points)}</span>
                  <span>{reason.text}</span>
                  <Badge variant={SOURCE_VARIANT[reason.source] || 'neutral'}>{reason.source}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section icon={IndianRupee} iconClass="bg-blue-100 text-blue-700" title="Repair cost" summary={cost.summary}>
          <Details items={cost.details} />
        </Section>
        <Section icon={TrendingDown} iconClass="bg-purple-100 text-purple-700" title="Write-off chance" summary={loss.summary}>
          <Details items={loss.details} />
        </Section>
        <p className="text-xs text-gray-500 border-t border-gray-100 pt-3">
          These are review priorities, not proof. A person makes the final decision on every claim.
        </p>
      </CardContent>
    </Card>
  )
}
