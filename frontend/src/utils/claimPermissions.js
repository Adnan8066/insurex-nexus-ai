// Mirrors the backend claim delete rule: admins can delete any claim; other
// non-investigator roles can delete a claim only while it is still 'submitted'.
export function canDeleteClaim(role, status) {
  if (role === 'admin') return true
  return !!role && role !== 'investigator' && status === 'submitted'
}
