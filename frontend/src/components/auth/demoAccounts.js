// Demo logins created by `python manage.py load_demo` (backend/django_backend).
// Shown on the sign-in pages only when VITE_SHOW_DEMO_LOGINS=true.
export const SHOW_DEMO_LOGINS = import.meta.env.VITE_SHOW_DEMO_LOGINS === 'true'

// load_demo's default password; set VITE_DEMO_PASSWORD if you ran it with --password.
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'InsureX@Demo2026'

export const DEMO_ACCOUNTS = [
  {
    key: 'customer',
    label: 'Customer',
    page: '/login',
    form: { email: 'customer@demo.insurex.test', license_plate: 'KA 01 MJ 4521', mobile_number: '+91 90000 00001' },
  },
  { key: 'employee', label: 'Employee', page: '/staff-login', form: { email: 'employee@demo.insurex.test', password: DEMO_PASSWORD } },
  { key: 'investigator', label: 'Investigator', page: '/staff-login', form: { email: 'investigator@demo.insurex.test', password: DEMO_PASSWORD } },
  { key: 'admin', label: 'Admin', page: '/staff-login', form: { email: 'admin@demo.insurex.test', password: DEMO_PASSWORD } },
]

export function demoForm(key) {
  return DEMO_ACCOUNTS.find((account) => account.key === key)?.form || null
}
