import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/useAuth'

const allRoles = ['customer', 'employee', 'investigator', 'repair', 'admin']
const reviewRoles = ['employee', 'investigator', 'admin']
const staffRoles = ['employee', 'admin']

const moduleGroups = [
  {
    title: 'Insurance & Claims',
    badge: 'CUSTOMER WORKFLOWS',
    links: [
      { label: 'Claims workspace', to: '/claims', roles: allRoles },
      { label: 'Policies', to: '/policies', roles: ['customer', 'employee', 'admin'] },
      { label: 'Vehicles', to: '/vehicles', roles: ['customer', 'employee', 'admin'] },
    ],
    secondBadge: '',
    secondLinks: [],
  },
  {
    title: 'Review & Investigation',
    badge: 'AI & RISK REVIEW',
    links: [
      { label: 'AI Assessment', to: '/ai-assessment', roles: reviewRoles },
      { label: 'Fraud Investigation', to: '/fraud', roles: reviewRoles },
      { label: 'AI Decision Center', to: '/ai-decision', roles: reviewRoles },
      { label: 'Analytics', to: '/analytics', roles: reviewRoles },
    ],
    secondBadge: 'CLAIM SUPPORT',
    secondLinks: [
      { label: 'Investigator Workspace', to: '/investigators', roles: ['employee', 'investigator', 'admin'] },
      { label: 'Repair Shops', to: '/repair-shops', roles: ['employee', 'repair', 'admin'] },
    ],
  },
  {
    title: 'Operations & Account',
    badge: 'CLAIM OPERATIONS',
    links: [
      { label: 'Settlements', to: '/settlements', roles: staffRoles },
      { label: 'User Management', to: '/admin/users', roles: ['admin'] },
      { label: 'AI Operations', to: '/operations', roles: reviewRoles },
    ],
    secondBadge: '',
    secondLinks: [],
  },
]

function FooterLink({ link }) {
  const className = 'text-sm text-slate-300 transition hover:text-white focus:text-white focus:outline-none'
  return <Link className={className} to={link.to}>{link.label}</Link>
}

export function Footer() {
  const { user } = useAuth()
  const columns = moduleGroups.map((group) => ({
    ...group,
    links: group.links.filter((link) => link.roles.includes(user?.role)),
    secondLinks: group.secondLinks.filter((link) => link.roles.includes(user?.role)),
  })).filter((group) => group.links.length > 0 || group.secondLinks.length > 0)
  return (
    <footer className="bg-[#06172e] text-slate-200" role="contentinfo">
      <div className="mx-auto max-w-[1600px] px-4 pb-8 pt-12 sm:px-6 lg:px-8 lg:pt-16">
        <div className="footer-module-grid gap-10 lg:gap-12" style={{ '--footer-group-count': columns.length }}>
          <section className="flex flex-col items-start gap-6">
            <div className="rounded-3xl bg-white p-7 text-slate-950 shadow-2xl shadow-black/20 sm:max-w-sm">
              <p className="text-2xl font-extrabold leading-tight tracking-tight">Built around your claims workflow.</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">Manage coverage, vehicle details, assessment, investigation, repair, and settlement in one workspace.</p>
              <a href="#footer-contact" className="mt-6 inline-flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                Contact Support <ArrowRight className="h-4 w-4" />
              </a>
            </div>
            <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-white" aria-label="InsureX dashboard">
              <img src="/insurex-nexus-ai-logo.jpg" alt="" className="h-8 w-8 rounded-lg object-cover" />
              InsureX Nexus AI
            </Link>
          </section>

          {columns.map((column) => (
            <section key={column.title}>
              <h2 className="text-sm font-bold text-white">{column.title}</h2>
              {column.links.length > 0 && <>
                <h3 className="mt-6 text-[10px] font-extrabold uppercase tracking-[0.18em] text-blue-300">{column.badge}</h3>
                <ul className="mt-3 space-y-2.5">{column.links.map((link) => <li key={link.label}><FooterLink link={link} /></li>)}</ul>
              </>}
              {column.secondBadge && column.secondLinks.length > 0 && <>
                <h3 className="mt-7 text-[10px] font-extrabold uppercase tracking-[0.18em] text-blue-300">{column.secondBadge}</h3>
                <ul className="mt-3 space-y-2.5">{column.secondLinks.map((link) => <li key={link.label}><FooterLink link={link} /></li>)}</ul>
              </>}
            </section>
          ))}
        </div>

        <div className="mt-12 grid gap-6 border-t border-white/10 pt-7 md:grid-cols-[1fr_auto] md:items-end">
          <div className="max-w-2xl space-y-3">
            <div id="footer-contact" className="scroll-mt-24">
              <h2 className="text-sm font-bold text-white">Workspace support</h2>
              <p className="mt-1 text-sm leading-6 text-slate-400">For help with account access or a claim, contact your InsureX administrator or claims team.</p>
            </div>
            <p className="text-xs leading-5 text-slate-500">InsureX Nexus AI connects the policy, vehicle, claim, AI review, investigation, repair, and settlement modules.</p>
            <p className="text-xs text-slate-500">© {new Date().getFullYear()} InsureX Nexus AI</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
