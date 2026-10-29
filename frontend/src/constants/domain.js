// Single source of truth for backend choice values. Keep in sync with the Django TextChoices.

// apps/claims/models.py ClaimStatus, in lifecycle order
export const CLAIM_STATUSES = [
  { value: 'submitted', label: 'Submitted' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'ai_assessment', label: 'AI Assessment' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'repair_settlement', label: 'Repair / Settlement' },
  { value: 'closed', label: 'Closed' },
]

// Statuses still waiting for a decision.
export const PENDING_CLAIM_STATUSES = ['submitted', 'under_review', 'ai_assessment', 'investigation']

// apps/claims/models.py IncidentType
export const INCIDENT_TYPES = [
  { value: 'collision', label: 'Collision', hint: 'Hit another vehicle or an object' },
  { value: 'comprehensive', label: 'Other damage (comprehensive)', hint: 'Damage not caused by a collision' },
  { value: 'theft', label: 'Theft', hint: 'Vehicle or parts stolen' },
  { value: 'vandalism', label: 'Vandalism', hint: 'Deliberate damage by someone else' },
  { value: 'fire', label: 'Fire', hint: 'Fire or explosion' },
  { value: 'water_damage', label: 'Flood / water damage', hint: 'Flooding or water entering the vehicle' },
  { value: 'hail', label: 'Hail / storm', hint: 'Hail, falling branches or storm damage' },
  { value: 'animal', label: 'Animal strike', hint: 'Hit an animal' },
  { value: 'glass', label: 'Glass breakage', hint: 'Windscreen or windows only' },
  { value: 'other', label: 'Something else', hint: 'Describe it in your own words' },
]

// apps/claims/models.py IncidentSeverity
export const INCIDENT_SEVERITIES = [
  { value: 'minor', label: 'Minor', hint: 'Scratches or small dents; the car still drives normally' },
  { value: 'moderate', label: 'Moderate', hint: 'Body or bumper damage; the car may still drive' },
  { value: 'major', label: 'Major', hint: 'Serious damage, airbags deployed, or the car cannot be driven' },
  { value: 'total_loss', label: 'Total loss', hint: 'The car is likely beyond repair' },
]

// apps/claims/models.py ClaimPriority
export const CLAIM_PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

// apps/vehicles/models.py VehicleStatus
export const VEHICLE_STATUSES = [
  { value: 'active', label: 'Active' },
  { value: 'sold', label: 'Sold' },
  { value: 'total_loss', label: 'Total Loss' },
  { value: 'salvage', label: 'Salvage' },
  { value: 'inactive', label: 'Inactive' },
]

// apps/policies/models.py PolicyType
export const POLICY_TYPES = [
  { value: 'auto_comprehensive', label: 'Comprehensive Auto' },
  { value: 'auto_collision', label: 'Collision Auto' },
  { value: 'auto_liability', label: 'Liability Auto' },
  { value: 'homeowners', label: 'Homeowners' },
  { value: 'renters', label: 'Renters' },
  { value: 'umbrella', label: 'Umbrella' },
]

// apps/policies/models.py PolicyStatus
export const POLICY_STATUSES = [
  { value: 'active', label: 'Active' },
  { value: 'pending', label: 'Pending' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'expired', label: 'Expired' },
  { value: 'cancelled', label: 'Cancelled' },
]

// backend/django_backend/common/risk.py
export const FRAUD_MODERATE_THRESHOLD = 30
export const FRAUD_HIGH_THRESHOLD = 65

export function fraudRiskLevel(score) {
  const value = Number(score) || 0
  if (value > FRAUD_HIGH_THRESHOLD) return 'high'
  if (value >= FRAUD_MODERATE_THRESHOLD) return 'medium'
  return 'low'
}

export function labelFor(options, value, fallback = '—') {
  if (!value) return fallback
  return options.find((option) => option.value === value)?.label
    || String(value).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
