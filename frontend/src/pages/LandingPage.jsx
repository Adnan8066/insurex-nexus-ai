import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, BadgeCheck, CarFront, Check, ChevronRight, ClipboardCheck,
  FileText, LoaderCircle, Moon, ShieldCheck, Sparkles, Sun, UserRound, Wrench, X,
} from 'lucide-react'
import { callbackService } from '../services'
import { policyTiers } from '../data/policyTiers'
import { SegmentedTabs } from '../components/ui/SegmentedTabs'

const benefits = [
  {
    icon: ShieldCheck,
    number: '01',
    label: 'POLICY DETAILS',
    title: 'Know what your cover includes',
    text: 'Keep policy details, vehicle information, and important documents together in one place.',
  },
  {
    icon: ClipboardCheck,
    number: '02',
    label: 'CLAIM PROGRESS',
    title: 'Follow every claim step',
    text: 'Submit a claim and keep track of its progress as it moves through review and resolution.',
  },
  {
    icon: Sparkles,
    number: '03',
    label: 'HUMAN OVERSIGHT',
    title: 'AI assisted, people reviewed',
    text: 'Assessment tools help organize claim information. Insurance decisions stay with the claims team.',
  },
]

const coverItems = [
  ['Accidental damage', 'Record vehicle damage and share supporting photos with your claim.'],
  ['Theft and loss', 'Keep the policy and claim information you need close at hand.'],
  ['Third party incidents', 'Submit incident details for the appropriate team to review.'],
  ['Repair coordination', 'Track claim progress and repair updates through the claims workspace.'],
]

const policyFilters = [
  { value: 'comprehensive', label: 'Comprehensive' },
  { value: 'third-party', label: 'Third party' },
  { value: 'own-damage', label: 'Own damage' },
  { value: 'electric', label: 'Electric vehicle' },
  { value: 'two-wheeler', label: 'Two-wheeler' },
]

export function LandingPage() {
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = window.localStorage.getItem('theme')
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const [callbackOpen, setCallbackOpen] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', vehicle_type: '', consent: false })
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [policiesOpen, setPoliciesOpen] = useState(false)
  const [policyFilter, setPolicyFilter] = useState('comprehensive')

  const visiblePolicies = policyTiers.filter((policy) => {
    if (policyFilter === 'comprehensive') return policy.type === 'auto_comprehensive'
    if (policyFilter === 'third-party') return policy.type === 'auto_liability'
    if (policyFilter === 'own-damage') return policy.type === 'auto_collision'
    if (policyFilter === 'electric') return policy.category.includes('(EV)')
    return policy.category === 'Two-Wheeler'
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    window.localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const openCallback = () => {
    setCallbackOpen(true)
    setSubmitError('')
    setSubmitted(false)
  }

  const submitCallback = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setSubmitError('')
    try {
      await callbackService.request({ ...form, phone: `+91 ${form.phone.trim()}` })
      setSubmitted(true)
      setForm({ name: '', phone: '', vehicle_type: '', consent: false })
    } catch (error) {
      setSubmitError(error.response?.data?.detail || 'We could not send your request. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="landing-page min-h-screen overflow-hidden bg-white font-sans text-slate-900 transition-colors duration-300 dark:!bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mx-auto flex h-[76px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label="InsureX Nexus AI home">
            <img src="/insurex-nexus-ai-logo.jpg" alt="" className="h-11 w-11 rounded-xl object-cover shadow-sm" />
            <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-xl">InsureX <span className="text-blue-600 dark:text-blue-400">Nexus AI</span></span>
          </Link>
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 dark:text-slate-300 md:flex" aria-label="Main navigation">
            <a href="#coverage" className="transition hover:text-blue-700">Coverage</a>
            <a href="#how-it-works" className="transition hover:text-blue-700">How it works</a>
            <a href="#support" className="transition hover:text-blue-700">Support</a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <button type="button" onClick={() => setDarkMode((current) => !current)} className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-4 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white dark:focus:ring-blue-900" aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <Link to="/login" className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-200">
              Login <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="landing-hero relative isolate">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,rgba(219,234,254,0.65),rgba(248,250,252,0.92)_48%,#ffffff_78%)] dark:bg-[radial-gradient(ellipse_at_top_right,rgba(30,58,138,0.28),rgba(15,23,42,0.96)_48%,#020617_78%)]" />
          <div className="landing-hero-grid pointer-events-none absolute inset-0 -z-10" />
          <div className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-16 pt-14 sm:px-8 sm:pb-24 sm:pt-20 lg:grid-cols-[1.02fr_0.98fr] lg:gap-8 lg:pb-28 lg:pt-24">
            <div className="max-w-2xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-3.5 py-2 text-sm font-semibold text-blue-800 shadow-sm dark:border-blue-900 dark:bg-slate-900/80 dark:text-blue-300">
                <BadgeCheck className="h-4 w-4" /> Your vehicle cover, claims, and updates in one place
              </div>
              <h1 className="text-4xl font-extrabold leading-[1.08] tracking-[-0.02em] text-slate-950 dark:text-white sm:text-5xl lg:text-6xl">
                A clearer way to manage <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">motor insurance.</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600 dark:text-slate-300 sm:text-xl">
                Keep your vehicle and policy details organized, submit claims, and follow progress with a straightforward online experience.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <button type="button" onClick={openCallback} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3.5 font-bold text-white shadow-lg shadow-blue-500/25 transition duration-200 hover:-translate-y-0.5 hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200">
                  Request a callback <ArrowRight className="h-5 w-5" />
                </button>
                <Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3.5 font-bold text-slate-700 transition hover:border-blue-300 hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-blue-100 dark:border-slate-700 dark:!bg-slate-900 dark:text-slate-100 dark:hover:border-blue-700 dark:hover:bg-slate-800 dark:focus:ring-blue-900">
                  Sign in to your account <ChevronRight className="h-5 w-5" />
                </Link>
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-slate-600 dark:text-slate-300">
                <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-emerald-600" /> Manage policy details</span>
                <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-emerald-600" /> Track claim updates</span>
                <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-emerald-600" /> Share claim documents</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl lg:pl-5">
              <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-blue-200/60 blur-3xl" />
              <div className="absolute -bottom-6 -left-8 h-40 w-40 rounded-full bg-emerald-100/80 blur-3xl" />
              <div className="relative rounded-[2rem] border border-white/70 bg-gradient-to-br from-blue-950 via-blue-900 to-blue-700 p-6 shadow-2xl shadow-blue-900/10 sm:p-8">
                <div className="absolute right-8 top-8 h-24 w-24 rounded-full border border-white/10" />
                <div className="absolute right-14 top-14 h-12 w-12 rounded-full border border-white/10" />
                <div className="relative flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-200">Customer workspace</p>
                    <p className="mt-2 text-xl font-bold tracking-tight text-white">Your cover, clearly organized</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-3 text-blue-100 ring-1 ring-white/15"><ShieldCheck className="h-7 w-7" /></div>
                </div>
                <div className="relative my-8 flex h-48 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-sky-100 via-blue-100 to-indigo-200 sm:h-56">
                  <div className="landing-cloud landing-cloud-one" />
                  <div className="landing-cloud landing-cloud-two" />
                  <div className="absolute bottom-0 h-16 w-full bg-gradient-to-t from-slate-300/70 to-transparent" />
                  <div className="landing-road absolute bottom-9 h-1 w-full bg-white/80" />
                  <div className="relative flex h-36 w-72 items-center justify-center rounded-[48%] bg-white/50 blur-2xl" />
                  <div className="landing-car absolute bottom-7"><CarFront className="h-36 w-36 text-blue-800 drop-shadow-xl sm:h-40 sm:w-40" strokeWidth={1.4} /></div>
                  <div className="landing-sparkle absolute left-[32%] top-[32%] text-blue-600">✦</div>
                  <div className="landing-sparkle landing-sparkle-late absolute right-[28%] top-[25%] text-emerald-500">✦</div>
                  <div className="absolute left-5 top-5 rounded-xl border border-white/70 bg-white/75 px-3 py-2 shadow-md backdrop-blur-md">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700"><span className="landing-status-dot h-2 w-2 rounded-full bg-emerald-500" /> Claims workspace</div>
                  </div>
                  <button type="button" onClick={() => setPoliciesOpen(true)} className="absolute bottom-5 right-4 rounded-xl border border-white/70 bg-white/85 px-3 py-2 shadow-lg backdrop-blur-md transition hover:-translate-y-0.5 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700"><FileText className="h-4 w-4 text-blue-700" /> Policy details</div>
                  </button>
                </div>
                <div className="relative grid grid-cols-1 gap-3 text-center">
                  <button type="button" onClick={() => setPoliciesOpen(true)} aria-label="View policy options" className="rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white transition hover:-translate-y-1 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white">
                    <FileText className="mx-auto h-5 w-5 text-blue-100" />
                    <span className="mt-1 block text-xs font-semibold text-blue-50">View policy options</span>
                  </button>
                </div>
                <div className="relative mt-4 flex items-center gap-3 rounded-2xl border border-white/50 bg-white/95 p-3 shadow-[0_12px_32px_-12px_rgba(15,23,42,0.35)] sm:p-4">
                  <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><ClipboardCheck className="h-5 w-5" /></div>
                  <div><p className="text-sm font-bold text-slate-800">Updates in one place</p><p className="text-xs text-slate-500">Stay informed as your claim moves</p></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-y border-slate-100 bg-white py-16 dark:border-slate-800 dark:!bg-slate-950 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">Built around your journey</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white sm:text-4xl">Insurance tasks, made easier to follow</h2>
              <p className="mt-4 text-lg leading-7 text-slate-600 dark:text-slate-300">A customer-friendly workspace for the everyday details and the moments when you need support.</p>
            </div>
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {benefits.map(({ icon: Icon, number, label, title, text }, index) => (
                <article key={title} className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-t-2 hover:border-t-blue-600 hover:shadow-xl hover:shadow-blue-950/5 dark:border-slate-800 dark:bg-slate-900 sm:p-7">
                  <div className="mb-6 flex items-center justify-between">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${index === 1 ? 'bg-emerald-50 text-emerald-700' : 'bg-blue-50 text-blue-700'}`}><Icon className="h-6 w-6" /></div>
                    <span className="text-xs font-bold tracking-[0.14em] text-slate-400 dark:text-slate-500">{number} / {label}</span>
                  </div>
                  <h3 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="coverage" className="bg-slate-50 py-16 dark:bg-slate-900 sm:py-20">
          <div className="mx-auto grid max-w-7xl gap-12 px-5 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">Motor cover and claims</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white sm:text-4xl">The details you need, all together</h2>
              <p className="mt-5 leading-7 text-slate-600 dark:text-slate-300">Your available cover depends on the policy assigned to your vehicle. Use your account to review policy information and contact the team if you need help understanding your cover.</p>
              <button type="button" onClick={openCallback} className="mt-7 inline-flex items-center gap-2 font-bold text-blue-800 hover:text-blue-950 dark:text-blue-300 dark:hover:text-blue-200">Talk to an agent <ArrowRight className="h-4 w-4" /></button>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {coverItems.map(([title, text], index) => (
                <div key={title} className="group flex gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-t-2 hover:border-t-blue-600 hover:shadow-xl hover:shadow-blue-950/5 dark:border-slate-800 dark:bg-slate-950">
                  <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${index === 3 ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'}`}>
                    {index === 3 ? <Wrench className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
                  </div>
                  <div><h3 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3><p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{text}</p></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="support" className="bg-white px-5 py-14 dark:!bg-slate-950 sm:px-8 sm:py-20">
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-7 rounded-3xl bg-[linear-gradient(135deg,#0F172A_0%,#1E293B_100%)] px-7 py-9 text-white shadow-xl shadow-slate-900/15 sm:px-10 sm:py-11 md:flex-row md:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-400">Need help with your account?</p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">Our team is here to help you move forward.</h2>
              <p className="mt-2 leading-6 text-slate-400">Sign in to view your policies, claims, and available support options.</p>
            </div>
            <Link to="/login" className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-slate-900 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_8px_20px_-8px_rgba(96,165,250,0.65)] transition-transform duration-200 hover:scale-105 hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-blue-400/30">Login <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:!bg-slate-950">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-7 text-sm text-slate-500 sm:px-8 md:flex-row md:items-center md:justify-between">
          <Link to="/" className="font-bold text-slate-800 dark:text-slate-100">InsureX <span className="text-blue-700 dark:text-blue-400">Nexus AI</span></Link>
          <p className="dark:text-slate-400">Manage your motor policy and claims in one secure workspace.</p>
          <div className="flex gap-5 font-medium"><Link to="/login" className="hover:text-blue-700">Login</Link><button type="button" onClick={openCallback} className="hover:text-blue-700">Request a callback</button></div>
        </div>
      </footer>

      {callbackOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/70 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setCallbackOpen(false) }}>
          <section role="dialog" aria-modal="true" aria-labelledby="callback-title" className="relative my-auto w-full max-w-lg rounded-[1.75rem] bg-white p-6 shadow-2xl dark:bg-slate-900 sm:p-9">
            <button type="button" onClick={() => setCallbackOpen(false)} aria-label="Close callback form" className="absolute right-4 top-4 rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"><X className="h-6 w-6" /></button>
            {submitted ? (
              <div className="py-8 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"><Check className="h-8 w-8" /></div>
                <h2 className="mt-5 text-2xl font-extrabold text-slate-950">Request received</h2>
                <p className="mx-auto mt-3 max-w-sm leading-6 text-slate-600">Thank you. An InsureX agent will contact you using the number you provided.</p>
                <button type="button" onClick={() => setCallbackOpen(false)} className="mt-7 rounded-xl bg-blue-700 px-7 py-3 font-bold text-white hover:bg-blue-800">Done</button>
              </div>
            ) : (
              <>
                <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">Speak with our team</p>
                <h2 id="callback-title" className="mt-2 pr-8 text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white">Request a callback</h2>
                <p className="mt-2 text-slate-600 dark:text-slate-300">Share a few details and an agent will get in touch with you.</p>
                <form onSubmit={submitCallback} className="mt-7 space-y-5">
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-200">Your name</span>
                    <span className="flex items-center gap-3 rounded-xl border border-slate-300 px-4 focus-within:border-blue-600 focus-within:ring-4 focus-within:ring-blue-100 dark:border-slate-700 dark:focus-within:ring-blue-900"><UserRound className="h-5 w-5 shrink-0 text-slate-400" /><input required maxLength={120} autoComplete="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Enter your name" className="min-w-0 flex-1 border-0 bg-transparent py-3.5 text-slate-900 outline-none placeholder:text-slate-400 dark:text-white" /></span>
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-200">Contact number</span>
                    <span className="flex items-center gap-3 rounded-xl border border-slate-300 px-4 focus-within:border-blue-600 focus-within:ring-4 focus-within:ring-blue-100 dark:border-slate-700 dark:focus-within:ring-blue-900"><span aria-hidden="true" className="font-semibold text-slate-400">+91</span><input required type="tel" inputMode="tel" autoComplete="tel-national" maxLength={20} value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Enter your phone number" className="min-w-0 flex-1 border-0 bg-transparent py-3.5 text-slate-900 outline-none placeholder:text-slate-400 dark:text-white" /></span>
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-200">Vehicle type</span>
                    <span className="flex items-center gap-3 rounded-xl border border-slate-300 px-4 focus-within:border-blue-600 focus-within:ring-4 focus-within:ring-blue-100 dark:border-slate-700 dark:focus-within:ring-blue-900"><CarFront className="h-5 w-5 shrink-0 text-slate-400" /><select required value={form.vehicle_type} onChange={(event) => setForm({ ...form, vehicle_type: event.target.value })} className="min-w-0 flex-1 appearance-none bg-transparent py-3.5 text-slate-800 outline-none dark:text-slate-100"><option value="">Select vehicle type</option><option value="car">Car</option><option value="two_wheeler">Two-wheeler</option><option value="commercial">Commercial vehicle</option><option value="other">Other</option></select><ChevronRight className="h-4 w-4 rotate-90 text-slate-400" /></span>
                  </label>
                  <label className="flex cursor-pointer items-start gap-3 text-sm leading-5 text-slate-600 dark:text-slate-300">
                    <input type="checkbox" required checked={form.consent} onChange={(event) => setForm({ ...form, consent: event.target.checked })} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-700 focus:ring-blue-600" />
                    <span>I agree that an InsureX agent may contact me about motor insurance.</span>
                  </label>
                  {submitError && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{submitError}</p>}
                  <button type="submit" disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3.5 font-bold text-white transition hover:bg-emerald-700 disabled:cursor-wait disabled:opacity-70">
                    {submitting && <LoaderCircle className="h-5 w-5 animate-spin" />}{submitting ? 'Sending request…' : 'Request a callback'}
                  </button>
                  <p className="text-center text-xs leading-5 text-slate-500 dark:text-slate-400">Your details will be used only to respond to this request.</p>
                </form>
              </>
            )}
          </section>
        </div>
      )}

      {policiesOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center overflow-y-auto bg-slate-950/70 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setPoliciesOpen(false) }}>
          <section role="dialog" aria-modal="true" aria-labelledby="policy-catalog-title" className="relative my-auto max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[1.75rem] bg-slate-50 p-5 shadow-2xl dark:bg-slate-900 sm:p-8">
            <button type="button" onClick={() => setPoliciesOpen(false)} aria-label="Close policy options" className="absolute right-4 top-4 rounded-full bg-white p-2 text-slate-500 shadow-sm transition hover:bg-slate-100 hover:text-slate-900"><X className="h-6 w-6" /></button>
            <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">Motor insurance</p>
            <h2 id="policy-catalog-title" className="mt-2 pr-12 text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white">Explore policy options</h2>
            <p className="mt-2 max-w-3xl leading-6 text-slate-600 dark:text-slate-300">Compare the cover types and add-ons in our current demo catalog. An agent can help confirm availability and explain which option fits your vehicle.</p>
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-5 text-amber-900">
              These are illustrative project examples, not confirmed products or insurer quotes. Coverage, eligibility, and premium must be confirmed by an agent.
            </div>
            <div className="mt-6">
              <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Filter by cover type</p>
              <SegmentedTabs
                tabs={policyFilters}
                value={policyFilter}
                onChange={setPolicyFilter}
                ariaLabel="Filter policy options by cover type"
                className="max-w-full"
              />
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {visiblePolicies.map((policy) => (
                <article key={policy.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-950">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wider text-blue-700">{policy.category}</p>
                      <h3 className="mt-1 text-lg font-bold leading-6 text-slate-900 dark:text-slate-100">{policy.name}</h3>
                    </div>
                    <ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-blue-600" />
                  </div>
                  <div className="mt-4">
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Coverage</p>
                    <ul className="mt-2 space-y-1.5">
                      {policy.coverageSections.map((coverage) => <li key={coverage} className="flex gap-2 text-sm leading-5 text-slate-700"><Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{coverage}</li>)}
                    </ul>
                  </div>
                  {policy.addons.length > 0 && <p className="mt-4 border-t border-slate-100 pt-3 text-sm leading-5 text-slate-600"><span className="font-semibold text-slate-800">Optional add-ons:</span> {policy.addons.join(', ')}</p>}
                  <p className="mt-2 text-xs text-slate-500">Example reference: {policy.id}</p>
                </article>
              ))}
            </div>
            <div className="mt-6 flex flex-col justify-between gap-4 rounded-2xl bg-blue-950 p-5 text-white sm:flex-row sm:items-center">
              <div><h3 className="font-bold">Need help choosing?</h3><p className="mt-1 text-sm text-blue-100">Leave your contact details and an agent can walk you through the options.</p></div>
              <button type="button" onClick={() => { setPoliciesOpen(false); openCallback() }} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-blue-950 transition hover:bg-blue-50">Request a callback <ArrowRight className="h-4 w-4" /></button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
