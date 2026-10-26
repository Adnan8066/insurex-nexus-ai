import { Navigate, Link } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, BrainCircuit, CarFront, ClipboardCheck, FileText, Shield, Sparkles, UsersRound } from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { BrandArtwork } from '../../components/auth/BrandArtwork'

const capabilities = [
  { icon: FileText, title: 'Policy workspace', text: 'Keep coverage, vehicles, and policy documents together.' },
  { icon: CarFront, title: 'Claim lifecycle', text: 'Track a claim from first notice through assessment and review.' },
  { icon: BrainCircuit, title: 'AI advisory', text: 'See decision support and routing recommendations for human review.' },
]

export function LandingPage() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-slate-500" role="status">Loading your workspace…</div>
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return (
    <main className="min-h-screen overflow-hidden bg-[#f7faff] text-slate-900">
      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <Link to="/" className="flex items-center gap-3" aria-label="InsureX Nexus AI home">
          <img src="/insurex-nexus-ai-logo.jpg" alt="InsureX Nexus AI logo" className="h-11 w-11 rounded-2xl object-cover shadow-sm" />
          <span className="text-lg font-bold tracking-tight">InsureX <span className="text-blue-600">Nexus AI</span></span>
        </Link>
        <nav className="flex items-center gap-3" aria-label="Main navigation">
          <a href="#platform" className="hidden px-3 py-2 text-sm font-medium text-slate-600 hover:text-blue-700 sm:block">Platform</a>
          <Link to="/login" className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-white">Sign in</Link>
          <Link to="/register" className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700">Create account</Link>
        </nav>
      </header>

      <section className="relative mx-auto grid max-w-7xl items-center gap-8 px-5 pb-16 pt-8 sm:px-8 md:min-h-[610px] md:grid-cols-[1fr_1fr] md:gap-3 md:pb-20 lg:px-12">
        <div className="absolute -left-48 top-10 h-96 w-96 rounded-full bg-sky-200/50 blur-3xl" />
        <div className="absolute right-0 top-20 h-80 w-80 rounded-full bg-indigo-100/70 blur-3xl" />
        <div className="relative z-10">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-3.5 py-2 text-xs font-bold uppercase tracking-[.12em] text-blue-700 shadow-sm"><Sparkles className="h-4 w-4"/> Insurance operations, connected</div>
          <h1 className="max-w-2xl text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-[3.8rem]">A clearer path from <span className="text-blue-600">policy to claim review.</span></h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">Manage policies, submit and follow claims, and bring the right people into each review with one connected workspace.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/register" className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3.5 font-semibold text-white shadow-xl shadow-blue-600/20 transition hover:-translate-y-0.5 hover:bg-blue-700">Get started <ArrowRight className="h-4 w-4"/></Link>
            <Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-6 py-3.5 font-semibold text-slate-700 transition hover:border-blue-200 hover:text-blue-700">Sign in to your account <ArrowUpRight className="h-4 w-4"/></Link>
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-slate-500">
            <span className="inline-flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-600"/> Secure account access</span>
            <span className="inline-flex items-center gap-2"><UsersRound className="h-4 w-4 text-blue-600"/> Human-reviewed decisions</span>
          </div>
        </div>
        <div className="relative z-10 -mx-3 sm:mx-0"><BrandArtwork/></div>
      </section>

      <section id="platform" className="border-y border-slate-200/70 bg-white/75 px-5 py-16 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-xs font-bold uppercase tracking-[.16em] text-blue-600">One connected platform</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">The important steps, all in view.</h2>
            <p className="mt-3 leading-7 text-slate-600">Move through core insurance workflows with clear records and people in control of important decisions.</p>
          </div>
          <div className="mt-9 grid gap-4 md:grid-cols-3">
            {capabilities.map(({ icon: Icon, title, text }, index) => <article key={title} className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-900/5">
              <div className={`mb-5 grid h-12 w-12 place-items-center rounded-2xl ${index === 0 ? 'bg-blue-50 text-blue-700' : index === 1 ? 'bg-cyan-50 text-cyan-700' : 'bg-violet-50 text-violet-700'}`}><Icon className="h-6 w-6"/></div>
              <h3 className="text-lg font-bold">{title}</h3>
              <p className="mt-2 leading-6 text-slate-600">{text}</p>
            </article>)}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:px-12">
        <div className="flex flex-col justify-between gap-5 rounded-3xl bg-[#071b35] p-7 text-white sm:flex-row sm:items-center sm:p-10">
          <div><div className="flex items-center gap-2 text-sm font-semibold text-sky-300"><ClipboardCheck className="h-4 w-4"/> People stay in control</div><h2 className="mt-2 text-2xl font-bold">Start with a workspace built for clarity.</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">AI tools provide advisory support. Claim assignments and coverage decisions remain subject to human review.</p></div>
          <Link to="/register" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-semibold text-[#071b35] transition hover:bg-sky-50">Create your account <ArrowRight className="h-4 w-4"/></Link>
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-3 border-t border-slate-200 px-5 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
        <span>© 2026 InsureX Nexus AI</span><span>Policy, claims, and review workspace</span>
      </footer>
    </main>
  )
}

export default LandingPage
