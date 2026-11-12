import { useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import { DEMO_ACCOUNTS, SHOW_DEMO_LOGINS } from './demoAccounts'

/**
 * One button per demo role. A role that signs in on this page fills the form;
 * the others open their sign-in page with the form already filled.
 */
export function DemoLogins({ page, onFill }) {
  const navigate = useNavigate()
  if (!SHOW_DEMO_LOGINS) return null

  const pick = (account) => {
    if (account.page === page) onFill(account.form)
    else navigate(account.page, { state: { demoAccount: account.key } })
  }

  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4">
      <p className="text-sm font-semibold text-gray-900">Demo accounts</p>
      <p className="mt-1 text-xs text-gray-600">Fills the sign-in form with a demo login. Click Sign in to continue.</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {DEMO_ACCOUNTS.map((account) => (
          <Button key={account.key} variant="outline" size="sm" onClick={() => pick(account)}>
            {account.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

export default DemoLogins
