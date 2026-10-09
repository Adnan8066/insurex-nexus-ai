export const mockUser = {
  id: 1,
  name: 'John Anderson',
  email: 'john.anderson@email.com',
  role: 'customer',
  avatar: null,
  phone: '+1 (555) 123-4567',
  address: '123 Main Street, Springfield, IL 62701',
  dateJoined: '2023-01-15',
}

export const mockEmployees = [
  { id: 1, name: 'Sarah Mitchell', role: 'employee', email: 'sarah.mitchell@insurex.com', department: 'Claims' },
  { id: 2, name: 'Michael Chen', role: 'employee', email: 'michael.chen@insurex.com', department: 'Underwriting' },
  { id: 3, name: 'Emily Rodriguez', role: 'investigator', email: 'emily.rodriguez@insurex.com', department: 'Investigations' },
  { id: 4, name: 'David Park', role: 'investigator', email: 'david.park@insurex.com', department: 'Investigations' },
  { id: 5, name: 'Lisa Thompson', role: 'repair', email: 'lisa.thompson@autofix.com', department: 'AutoFix Repair' },
  { id: 6, name: 'James Wilson', role: 'admin', email: 'james.wilson@insurex.com', department: 'Administration' },
]

export const mockRoles = [
  { value: 'customer', label: 'Customer' },
  { value: 'employee', label: 'Insurance Employee' },
  { value: 'investigator', label: 'Investigator' },
  { value: 'repair', label: 'Repair Shop' },
  { value: 'admin', label: 'Administrator' },
]

export default { mockUser, mockEmployees, mockRoles }