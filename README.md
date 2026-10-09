# InsureX Nexus AI – Intelligent Insurance Claim and Decision Management Platform

> A modern, professional enterprise React frontend designed for AI-driven insurance claim triage, fraud risk assessment, multi-agent adjudication, and reinforcement learning-assisted decision management.

---

## 🌟 Key Platform Highlights

- **Vite + React (JavaScript)**: Fast HMR, clean modular architecture.
- **Enterprise Fintech / InsurTech Design**: Responsive sidebar navigation, role-tailored dashboards, statistical KPI cards, and Chart.js telemetry.
- **Role-Based Access Control**:
  - 👤 **Customer** (Self-service claim intake, policy coverage, vehicle history, tracking)
  - ⚡ **Insurance Employee / Adjuster** (Claim review, triage, adjudication)
  - 🔍 **SIU Investigator** (Fraud risk analysis, evidence logging, case docket)
  - 🔧 **Repair Shop** (Certified body shop capacity, parts tracking, repair staging)
  - 📊 **Executive Administrator** (Macro-analytics, loss ratio, fraud distribution)
- **Django REST Framework Ready**: Fully structured Axios services with JWT bearer interceptors and automatic token refresh logic in `src/services/`.
- **Explainable Multi-Agent AI System**: Visualizes end-to-end multi-agent orchestration (Claim Agent, Policy Agent, Fraud Agent, Damage Assessment Agent, Settlement Agent, Decision Agent).
- **Simulated Reinforcement Learning (PPO)**: Offline policy gradient optimization for turnaround minimization and optimal investigator/repair dispatch.

---

## 🚀 Quick Start

### 1. Installation
```bash
npm install --legacy-peer-deps
```

### 2. Run Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:5173/`.

### 3. Production Build
```bash
npm run build
```

---

## 🔐 Demo Credentials (1-Click Login Enabled)

On the `/login` screen, you can click any of the quick-login role chips or use:

| Role | Email | Password | Primary Console |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer@demo.com` | `demo123` | Customer Dashboard (`/dashboard`) |
| **Insurance Employee** | `employee@demo.com` | `demo123` | Employee Operations Dashboard (`/dashboard`) |
| **Investigator (SIU)** | `investigator@demo.com` | `demo123` | Investigator Workspace (`/investigators`) |
| **Repair Shop** | `repair@demo.com` | `demo123` | Collision Repair Shop Console (`/repair-shops`) |
| **Administrator** | `admin@demo.com` | `demo123` | Analytics & BI Executive Dashboard (`/analytics`) |

---

## 📦 Project Modules

### 1. Authentication (`/login`, `/register`, `/forgot-password`)
- Secure login, sign up with role selection, password reset flow.
- Seamless mock fallback when Django API is offline with persistent JWT simulation.

### 2. Customer Dashboard (`/dashboard`)
- Active policies, total claims, pending & approved metrics.
- Recent claims feed, policy coverage summary, and interactive activity charts.

### 3. Policy Management (`/policies`, `/policies/:id`)
- Policy list with search, status, and insurance type filters.
- Comprehensive details: coverage limits, annual premiums, deductibles, effective dates, and linked vehicle specs.

### 4. Vehicle Management (`/vehicles`, `/vehicles/:id`)
- Fleet of insured automobiles with VIN, registration expiry, mileage, fuel type, and linked claim history.

### 5. Claim Management (`/claims`, `/claims/:id`, `/claims/new`, `/claims/:id/tracking`)
- Full 7-stage workflow: `Submitted → Under Review → AI Assessment → Investigation → Approved/Rejected → Repair/Settlement → Closed`.
- Guided 4-step Claim Submission wizard (Intake, Damage & Injuries, Police Reports, Estimate Upload).
- Real-time Lifecycle Workflow Tracker with handler attribution.

### 6. AI Claim Assessment Dashboard (`/ai-assessment`)
- Deep learning inference diagnostics: Predicted Repair Cost, Fraud Risk Score, Total Loss Probability, and Triage Priority.
- Side-by-side cost reconciliation against local repair shop benchmarks.
- Explainable AI feature importance weights (SHAP-style breakdown).

### 7. Fraud Investigation Dashboard (`/fraud`)
- High-risk claims flagged by neural embeddings.
- Risk factor evidence breakdown (Inconsistent statements, recent inception, ACV ratio).
- Investigator assignment modal and SIU case routing.

### 8. Investigator Dashboard (`/investigators`)
- SIU officer profile, active case docket, and fraud risk breakdown.
- Interactive investigation log notes with persistent timestamps.

### 9. Repair Shop Dashboard (`/repair-shops`)
- Collision repair facility capacity tracker and work orders board.
- Stage management: Teardown, Frame Straightening, Painting, Quality Check, Delivery.

### 10. Settlement Dashboard (`/settlements`)
- Net payout calculation (Estimated amount minus deductible).
- Payout execution simulation with ACH transfer tracking.

### 11. Admin Analytics Dashboard (`/analytics`)
- 7 Core Insurance KPIs: Total Policies, Active Policies, Total Claims, Pending Claims, Fraud Alerts, Total Loss Cases, Average Claim Cost.
- 5 Interactive Charts: Claims Over Time, Fraud Risk Distribution, Claim Status Distribution, Repair Cost by Vehicle Class, Total Loss Ratio.

### 12. AI Decision Center (`/ai-decision`)
- Visual flowchart: `Claim → ML Predictions → AI Multi-Agents → Decision Engine → RL Recommendation → Recommended Action`.
- Deep-dive into 6 autonomous sub-agents: Claim Agent, Policy Agent, Fraud Agent, Damage Assessment Agent, Settlement Agent, Decision Agent.
- Interactive decision simulation pipeline.

### 13. AI/RL Operations Page (`/operations`)
- PPO policy optimization outputs: Priority Tuning, Investigator Matching, Body Shop Routing, and Processing Time Estimation.
- RL reward convergence curves over 50,000 training episodes.

### 14. Notifications, Profile & Settings (`/notifications`, `/profile`, `/settings`)
- Notification alerts with category filters.
- User profile editing and password modification.
- API base URL and inference threshold configuration.

---

## 🏗️ Technical Architecture & Folder Structure

```
src/
├── assets/           # Static logos and imagery
├── components/
│   ├── charts/       # Chart.js implementations (Area, Bar, Doughnut, Pie)
│   ├── forms/        # Form inputs, select dropdowns, textareas
│   ├── layout/       # Responsive Sidebar and Top Navbar
│   ├── tables/       # Enterprise DataTable, headers, pagination
│   └── ui/           # Badges, Buttons, Cards, Modals, EmptyStates, Spinners
├── context/
│   └── AuthContext   # User state, JWT storage, role verification
├── data/             # Realistic mock datasets (policies, claims, AI, operations)
├── layouts/
│   └── MainLayout    # Responsive enterprise dashboard wrapper
├── pages/
│   ├── admin/        # Executive analytics
│   ├── ai/           # AI claim assessment
│   ├── auth/         # Login, Register, ForgotPassword
│   ├── claims/       # List, Details, Submit, Tracking
│   ├── dashboard/    # Customer and Employee Dashboards
│   ├── decision/     # AI Decision Center & Multi-Agent Swarm
│   ├── fraud/        # Fraud Investigation Dashboard
│   ├── investigator/ # Investigator Workspace
│   ├── notifications/# Alerts and messages
│   ├── operations/   # AI / Reinforcement Learning Operations
│   ├── policies/     # Policy management
│   ├── profile/      # User account & credentials
│   ├── repair/       # Repair shop console
│   ├── settings/     # System & model thresholds
│   ├── settlement/   # Settlement & disbursement
│   └── vehicles/     # Vehicle management
├── routes/
│   └── AppRoutes     # React Router v6 setup with role-aware protection
├── services/
│   ├── api.js        # Axios instance with JWT interceptors
│   ├── authService   # Authentication APIs
│   ├── claimService  # Claim endpoints
│   ├── policyService # Policy endpoints
│   ├── vehicleService# Vehicle endpoints
│   ├── settlementService # Settlement endpoints
│   └── aiService     # Model inference endpoints
└── utils/
    └── helpers.js    # Currency formatters, date formatters, badges
```

---

## 🔮 Future Integration Pipeline

The frontend is architected as an API-ready client for:
```
React Frontend (Vite)
       │
       ▼  (REST / Axios + JWT)
Django REST Framework
       │
       ▼
PostgreSQL Database
       │
       ▼
Python ML Inference Models (ONNX / PyTorch)
       │
       ▼
Multi-Agent Orchestrator
       │
       ▼
Reinforcement Learning Engine (Ray RLlib / Stable-Baselines3)
```
