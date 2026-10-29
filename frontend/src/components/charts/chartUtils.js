// Tooltip callback showing "Label: count (pct%)" for pie/doughnut/bar charts.
export function countAndPercentLabel(context) {
  const values = context.dataset.data
  const total = values.reduce((sum, value) => sum + (Number(value) || 0), 0)
  const value = Number(context.raw) || 0
  const pct = total ? Math.round((value / total) * 100) : 0
  return `${context.label}: ${value} (${pct}%)`
}
