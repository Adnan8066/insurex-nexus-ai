import { ShieldCheck, Sparkles } from 'lucide-react'

export function BrandArtwork() {
  return (
    <div className="relative mx-auto aspect-[1.08/1] w-full max-w-[540px]" aria-label="Illustration of an insurance dashboard and protected vehicle" role="img">
      <div className="absolute inset-[8%] rounded-[2.5rem] bg-gradient-to-br from-sky-300/25 via-blue-400/10 to-indigo-300/20 blur-2xl" />
      <svg viewBox="0 0 560 500" className="relative h-full w-full drop-shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="panel" x1="95" y1="76" x2="443" y2="411" gradientUnits="userSpaceOnUse"><stop stopColor="#fff"/><stop offset="1" stopColor="#eaf3ff"/></linearGradient>
          <linearGradient id="car" x1="161" y1="242" x2="388" y2="348" gradientUnits="userSpaceOnUse"><stop stopColor="#46b8ff"/><stop offset="1" stopColor="#2563eb"/></linearGradient>
          <linearGradient id="shield" x1="373" y1="92" x2="454" y2="190" gradientUnits="userSpaceOnUse"><stop stopColor="#53d2ff"/><stop offset="1" stopColor="#2563eb"/></linearGradient>
        </defs>
        <circle cx="285" cy="253" r="214" fill="#60a5fa" fillOpacity=".12"/>
        <circle cx="285" cy="253" r="171" stroke="#bfdbfe" strokeOpacity=".45" strokeDasharray="5 10"/>
        <rect x="74" y="72" width="362" height="326" rx="28" fill="url(#panel)"/>
        <rect x="74.75" y="72.75" width="360.5" height="324.5" rx="27.25" stroke="#fff" strokeOpacity=".7" strokeWidth="1.5"/>
        <rect x="101" y="100" width="36" height="36" rx="12" fill="#dbeafe"/>
        <path d="M112 119.5v-5.2a7 7 0 0 1 14 0v5.2M109 119h20v12h-20z" stroke="#2563eb" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
        <rect x="151" y="105" width="112" height="9" rx="4.5" fill="#10213c"/>
        <rect x="151" y="122" width="75" height="6" rx="3" fill="#94a3b8"/>
        <rect x="346" y="105" width="61" height="25" rx="12.5" fill="#dcfce7"/>
        <circle cx="360" cy="117.5" r="4" fill="#16a34a"/><rect x="370" y="114" width="26" height="7" rx="3.5" fill="#15803d"/>
        <rect x="101" y="158" width="308" height="126" rx="18" fill="#f8fbff" stroke="#e2e8f0"/>
        <path d="M117 253h275" stroke="#dbeafe" strokeWidth="2" strokeDasharray="4 8"/>
        <path d="m131 238 51-38 44 20 51-34 47 14 52-26" stroke="#3b82f6" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="181" cy="200" r="5" fill="#fff" stroke="#3b82f6" strokeWidth="3"/><circle cx="226" cy="220" r="5" fill="#fff" stroke="#3b82f6" strokeWidth="3"/><circle cx="277" cy="186" r="5" fill="#fff" stroke="#3b82f6" strokeWidth="3"/><circle cx="324" cy="200" r="5" fill="#fff" stroke="#3b82f6" strokeWidth="3"/>
        <rect x="101" y="303" width="137" height="68" rx="16" fill="#eff6ff"/>
        <rect x="117" y="320" width="48" height="7" rx="3.5" fill="#94a3b8"/><rect x="117" y="337" width="86" height="13" rx="6.5" fill="#1d4ed8"/>
        <rect x="252" y="303" width="157" height="68" rx="16" fill="#f0fdf4"/>
        <circle cx="275" cy="337" r="13" fill="#bbf7d0"/><path d="m269 337 4 4 8-9" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/><rect x="297" y="320" width="83" height="7" rx="3.5" fill="#86a99b"/><rect x="297" y="337" width="62" height="12" rx="6" fill="#15803d"/>
        <path d="M183 240h137l36 31v49a17 17 0 0 1-17 17H166a17 17 0 0 1-17-17v-48z" fill="url(#car)"/>
        <path d="m211 240 19-32a17 17 0 0 1 15-9h47a17 17 0 0 1 13 6l33 35z" fill="#bfdbfe" stroke="#fff" strokeWidth="5" strokeLinejoin="round"/>
        <path d="m239 207-17 29h49v-37h-13a23 23 0 0 0-19 8zm40-8v37h49l-27-32a14 14 0 0 0-11-5z" fill="#dff4ff"/>
        <path d="M150 278h202" stroke="#dbeafe" strokeWidth="4" strokeLinecap="round"/><path d="M161 299h13m158 0h13" stroke="#fff" strokeWidth="5" strokeLinecap="round"/>
        <circle cx="201" cy="331" r="21" fill="#10213c"/><circle cx="201" cy="331" r="9" fill="#dbeafe"/><circle cx="317" cy="331" r="21" fill="#10213c"/><circle cx="317" cy="331" r="9" fill="#dbeafe"/>
        <path d="M416 87c0-8 6-14 14-14s14 6 14 14v5c0 30-19 56-48 66-29-10-48-36-48-66v-5c0-8 6-14 14-14h54z" fill="url(#shield)"/>
        <path d="m381 126 13 13 27-29" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="115" cy="365" r="25" fill="#fef3c7"/><path d="M115 352v13l9 6" stroke="#d97706" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="438" cy="250" r="23" fill="#ede9fe"/><path d="m438 236 3.4 8.6 9 3.4-9 3.4-3.4 8.6-3.4-8.6-9-3.4 9-3.4z" fill="#7c3aed"/>
        <circle cx="405" cy="376" r="7" fill="#38bdf8"/><circle cx="139" cy="133" r="5" fill="#a78bfa"/>
      </svg>
    </div>
  )
}

export function AuthBrandPanel({ mode = 'login' }) {
  return (
    <aside className="relative hidden min-h-screen overflow-hidden bg-[#071b35] px-10 py-10 text-white md:flex md:flex-col md:justify-between lg:px-14">
      <div className="absolute -left-32 top-1/3 h-80 w-80 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="relative flex items-center gap-3">
        <img src="/insurex-nexus-ai-logo.jpg" alt="InsureX Nexus AI logo" className="h-12 w-12 rounded-2xl object-cover ring-1 ring-white/20" />
        <span className="text-lg font-bold">InsureX <span className="text-sky-300">Nexus AI</span></span>
      </div>
      <div className="relative mx-auto w-full max-w-xl py-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold tracking-wide text-sky-200"><Sparkles className="h-3.5 w-3.5"/> CONNECTED INSURANCE WORKSPACE</div>
        <h2 className="max-w-lg text-4xl font-bold leading-tight lg:text-5xl">Coverage, claims, and care in one place.</h2>
        <p className="mt-4 max-w-lg text-base leading-7 text-slate-300">Follow policy and claim activity with clear updates and people reviewing the important decisions.</p>
        <div className="my-5"><BrandArtwork /></div>
        <div className="flex items-center gap-2 text-sm text-slate-300"><ShieldCheck className="h-4 w-4 text-emerald-300"/> {mode === 'register' ? 'Create your customer account to get started.' : 'A single workspace for your insurance journey.'}</div>
      </div>
      <p className="relative text-xs text-slate-400">© 2026 InsureX Nexus AI · Secure account access</p>
    </aside>
  )
}

export function AuthLayout({ children, mode }) {
  return <div className="min-h-screen bg-slate-50 md:grid md:grid-cols-[minmax(0,1.1fr)_minmax(440px,.9fr)]"><AuthBrandPanel mode={mode}/><main className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-8 md:py-12">{children}</main></div>
}
