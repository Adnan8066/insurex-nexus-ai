# Spec: US personal auto policy

Status: draft, 2026-11-24. Supports Phases 2, 5 and 6 of [US_MIGRATION_PLAN.md](US_MIGRATION_PLAN.md).

This spec describes how a US personal auto policy is structured, which rules InsureX must enforce for the five launch states (OH, TX, FL, GA, CA), and how the `policies`, `vehicles` and `customers` models change to hold it. Rating figures in this spec are placeholders, not filed rates.

> **Verify before relying on it.** State minimum limits, PIP rules and rating restrictions change, often yearly. Every state rule here must be checked against that state's Department of Insurance before it is used in production, and the config must record the date it was checked.

## 1. How a US auto policy is structured

US insurers base personal auto policies on the ISO **Personal Auto Policy** form (PP 00 01) or their own version of it, plus state endorsements. A policy has six parts:

| Part | Name | What it does |
| --- | --- | --- |
| A | Liability | Pays for bodily injury (BI) and property damage (PD) the insured causes to others. No deductible |
| B | Medical Payments (MedPay) | Pays medical bills for the insured and passengers, regardless of fault |
| C | Uninsured/Underinsured Motorist (UM/UIM) | Pays the insured's injuries (UMBI) and, in some states, car damage (UMPD) when the at-fault driver has no or too little insurance |
| D | Damage to Your Auto | **Collision** and **other than collision** (comprehensive: theft, fire, glass, weather, flood, animal, vandalism). Pays actual cash value (ACV) minus a deductible |
| E | Duties After an Accident or Loss | Prompt notice, cooperation, police report for theft, and so on. Conditions, not coverage |
| F | General Provisions | Policy period, territory, cancellation, nonrenewal, fraud. Conditions, not coverage |

In no-fault states, a state endorsement adds **Personal Injury Protection (PIP)**, which pays the insured's medical bills and lost wages whatever the fault.

Key facts the data model must reflect:

1. **One policy, not one per coverage.** A customer buys one auto policy and chooses coverages inside it. "Collision" and "comprehensive" are coverages, not policy types.
2. **One policy covers several vehicles and drivers.** Liability, PIP, MedPay and UM apply to the whole policy. Collision, comprehensive, rental and towing are chosen **per vehicle**, each with its own deductible.
3. **Liability uses split limits.** `100/300/100` means $100k BI per person, $300k BI per accident and $100k PD per accident.
4. **Each policy belongs to one state.** The state is the one where the vehicles are garaged. It sets the minimum limits, required coverages and allowed rating factors.
5. **Terms are 6 or 12 months.**

## 2. Coverage catalog

The codes match the Lumora `coverage` column, so imported claims can link to coverages without a lookup table.

| Code | Coverage | Level | Limit form | Deductible | Notes |
| --- | --- | --- | --- | --- | --- |
| `BI` | Bodily injury liability | Policy | Split: per person / per accident | None | Required in every launch state except FL (see §4) |
| `PD` | Property damage liability | Policy | Per accident | None | Required in every launch state |
| `PIP` | Personal injury protection | Policy | Per person | Optional in some states | Required in FL; must be offered in TX |
| `MEDPAY` | Medical payments | Policy | Per person | None | Optional |
| `UMBI` | Uninsured/underinsured motorist BI | Policy | Split, cannot exceed BI | None | Must be offered in TX, FL, GA, CA. Rejection must be in writing (see §4) |
| `UMPD` | Uninsured motorist property damage | Policy | Per accident | State-specific | Rules differ by state; optional at launch |
| `COLL` | Collision | Vehicle | ACV | $250 / $500 / $1,000 / $2,000 | |
| `COMP` | Comprehensive (other than collision) | Vehicle | ACV | $0 / $250 / $500 / $1,000 | |
| `RENTAL` | Rental reimbursement | Vehicle | Per day / maximum, e.g. $30/$900 | None | Requires `COMP` or `COLL` |
| `TOW` | Towing and labor | Vehicle | Per disablement, e.g. $75 | None | |
| `GLASS0` | Full glass, no deductible | Vehicle | — | $0 on glass | Requires `COMP` |

### Limit options at launch

| Coverage | Options |
| --- | --- |
| BI | State minimum, 50/100, 100/300, 250/500 |
| PD | State minimum, 50,000, 100,000 |
| UMBI | Rejected, state minimum, or equal to BI |
| MEDPAY | 0, 1,000, 5,000, 10,000 |
| PIP | State options only (see §4) |

These match Lumora's `bi_limit_mix`, `coll_deductible_mix` and `comp_deductible_mix`.

## 3. Business rules (checked at quote and bind)

Rules are enforced in a validator shared by `quote/`, `bind-quote/` and endorsements. A failed rule blocks the bind and returns a plain-English reason.

| ID | Rule |
| --- | --- |
| R1 | Every BI and PD limit is at least the policy state's minimum |
| R2 | Coverages required by the state are present (FL: `PIP` and `PD`) |
| R3 | Coverages the state requires insurers to **offer** (UM in TX, FL, GA, CA; PIP in TX) are either selected or have a recorded rejection: who rejected, when, and the signed form as a `PolicyDocument` |
| R4 | UMBI limits never exceed BI limits |
| R5 | A vehicle with a lienholder (`lienholder_flag`) has both `COLL` and `COMP` |
| R6 | `RENTAL` and `GLASS0` require `COMP` on that vehicle |
| R7 | `term_months` is 6 or 12, and `end_date = start_date + term_months` |
| R8 | Every vehicle has a garaging ZIP in the policy state. A ZIP in another state needs underwriter review, since this is a common rate-evasion signal |
| R9 | Every household driver aged 16 or over is listed as rated or as excluded. Exclusions are allowed only where the state permits them |
| R10 | Rating factors the state forbids are never used (see §5) |

## 4. State rules for the launch states

These are the values to load into a new `US_STATE_RULES` config. Each figure is marked `SPEC` (from statute or a regulator) or `PLACEHOLDER` (an internal choice), the same way `POLICY_RATING_TABLES` is marked today.

| | OH | TX | FL | GA | CA |
| --- | --- | --- | --- | --- | --- |
| Minimum BI | 25/50 | 30/60 | None for most drivers¹ | 25/50 | 30/60 (since 2025-01-01) |
| Minimum PD | 25,000 | 25,000 | 10,000 | 25,000 | 15,000 |
| No-fault / PIP | No | No; PIP $2,500 must be offered, rejectable in writing | **Yes; PIP $10,000 required** | No | No |
| UM | Optional | Must be offered, rejectable in writing | Must be offered, rejectable in writing | Must be offered, rejectable in writing; "added-on" or "reduced-by" choice | Must be offered, rejectable in writing |
| Credit-based insurance score | Allowed | Allowed, with limits | Allowed, not as the only factor | Allowed | **Not allowed** |
| Gender as a factor | Allowed | Allowed | Allowed | Allowed | **Not allowed** |
| Other | | | BI may be required after certain incidents (financial responsibility 10/20/10) | | Prop 103: driving record, annual miles and years licensed must carry the most weight; good-driver discount required |

¹ Florida requires PIP and PD but not BI for most drivers. Lumora uses 10/20 as Florida's BI floor, which matches the financial-responsibility limit.

Gaps to fix in Lumora (`motorsynth/refdata.py`): Texas PIP is `[0]`, but Texas insurers must offer $2,500 PIP. Either add it as an offered option with a high rejection rate, or note the gap in `STORY.md`.

## 5. Rating (Phase 5)

Premium is calculated **per vehicle, per coverage**, and then summed:

```
coverage premium = base rate[state, coverage]
                 × territory factor[ZIP3]
                 × driver class factor          (age, years licensed, violations, at-fault accidents)
                 × vehicle factor[coverage]     (symbol from MSRP and segment; COLL/COMP only)
                 × limit or deductible factor[coverage]
                 × credit tier factor           (only where §4 allows it)
                 × usage and mileage factor
vehicle premium  = Σ coverage premiums × discounts (multi-car, homeowner, paid in full, good driver)
policy premium   = max(Σ vehicle premiums, minimum premium) + state fees
```

- The highest-rated driver is assigned to the highest-rated vehicle (a common default; it's an internal choice, so it's a `PLACEHOLDER`).
- Lumora's `pricing` block gives starting placeholder values: driver age factors, credit tiers A–D, 1.22 per violation, 0.90 multi-car, 0.95 homeowner, mileage bands, and a $420 minimum per vehicle.
- The rating breakdown stored on `PolicyApplication.rating_breakdown` lists every factor per vehicle and coverage, so a quote can always be explained.
- There is no GST. A few states charge small fees or surcharges, held as `state_fees` in `US_STATE_RULES`.

## 6. Data model changes

### `Policy`

| Change | Field | Notes |
| --- | --- | --- |
| Replace | `type` | Becomes `line` + `form` (see [US_PRODUCT_CATALOG.md](US_PRODUCT_CATALOG.md) §4). The three auto types become `line = personal_auto`, `form = PP0001`, with a data migration |
| Add | `state` | Two-letter code, one of the launch states |
| Add | `term_months` | 6 or 12 |
| Add | `bi_per_person`, `bi_per_accident`, `pd_limit` | Replace the single `liability` figure |
| Add | `umbi_per_person`, `umbi_per_accident`, `umpd_limit`, `um_rejected_at` | Rejection evidence for R3 |
| Add | `pip_limit`, `pip_rejected_at`, `medpay_limit` | |
| Add | `channel`, `producer` (FK to the new `Producer`), `prior_carrier`, `prior_lapse_days`, `bind_datetime` | From Lumora `policy_terms`; needed for fraud signals |
| Add | `renewal_seq`, `previous_term` (FK to itself) | Lets each 6- or 12-month term be its own row, as in Lumora |
| Remove later | `vehicle`, `deductible`, `coverage` (JSON), `property_*` | Keep until nothing reads them (Phase 2 risk note) |

### New `PolicyVehicle` (replaces `Policy.vehicle`)

`policy`, `vehicle`, `coll_deductible` (null means no collision), `comp_deductible` (null means no comprehensive), `rental`, `towing`, `glass0`, `lienholder_name`, and the premium per coverage (`premium_bi`, `premium_pd`, … `premium_comp`, `vehicle_premium`), the same as Lumora's `policy_vehicles`.

### New `Driver` and `PolicyDriver`

- `Driver` (in `customers`): `customer`, `relationship`, name, `date_of_birth`, `gender` (not used for rating in CA), `license_state`, `license_number` (stored encrypted, shown masked), `first_licensed_date`, `violations_3yr`, `at_fault_accidents_3yr`, `marital_status`.
- `PolicyDriver`: `policy`, `driver`, `status` (`rated` or `excluded`), `assigned_vehicle`.

### `Vehicle`

Add `msrp`, `segment`, `adas_equipped`, `lienholder_flag`, `declared_usage`, `declared_annual_miles` and `garaging_zip`, as listed in the migration plan. Remove `engine_cc` and `ex_showroom_price` when Phase 5 replaces IRDAI rating.

### `PolicyCoverage`

Retire it. Its policy-level fields move onto `Policy`, and its vehicle-level fields move onto `PolicyVehicle`. The homeowners fields (`dwelling`, `personal_property`, `additional_living_expenses`) move to `PropertyCoverage` in Wave 2 (see [US_PRODUCT_CATALOG.md](US_PRODUCT_CATALOG.md)).

### Documents

Add `um_rejection` and `pip_rejection` to `PolicyDocument.DOCUMENT_TYPES`. The `declaration` document (the declarations page) lists the named insured, policy period, state, drivers, vehicles with VINs and garaging ZIPs, each coverage with its limit, deductible and premium, lienholders, discounts and the total premium.

## 7. Lumora → model mapping (policy tables only)

| Lumora column | InsureX field |
| --- | --- |
| `policy_terms.policy_number`, `term_start`, `term_end`, `renewal_seq` | `Policy.policy_number` (plus the term suffix), `start_date`, `end_date`, `renewal_seq` |
| `state`, `garaging_zip` | `Policy.state`; `Vehicle.garaging_zip` |
| `bi_limit` (`"50/100"`) | `bi_per_person`, `bi_per_accident` (× 1,000) |
| `pd_limit`, `pip_limit`, `medpay_limit` | Same names on `Policy` |
| `um_flag` | `umbi_*` equal to BI when true, otherwise `um_rejected_at = bind_datetime` |
| `payment_plan` (`MONTHLY_CARD`, …) | `payment_frequency` plus payment method |
| `channel`, `producer_id`, `prior_carrier`, `prior_lapse_days`, `bind_datetime` | Same names on `Policy` |
| `written_premium` | `Policy.premium` |
| `policy_vehicles.*` | `PolicyVehicle` |
| `policy_drivers.*`, `drivers.*` | `PolicyDriver`, `Driver` |

With `PolicyVehicle` in place, Phase 2 no longer needs to split a multi-vehicle term into one `Policy` per vehicle, so the Phase 6 follow-up in the migration plan can be dropped.

## 8. Rollout

1. **Phase 2:** add the new fields and models next to the old ones (nullable), write `US_STATE_RULES` for the five states, import Lumora into them, and add validator rules R1–R9.
2. **Phase 5:** build the US rating engine (§5) and R10, rewrite `test_rating.py` for 3–4 states, and switch the `quote/` and `bind-quote/` APIs and the `PolicyForm`, `RequestPolicy` and `PlanCompare` screens to the new structure.
3. **Phase 6:** retire `Policy.vehicle`, `Policy.deductible`, `Policy.coverage`, `PolicyCoverage` and the IRDAI tables once nothing reads them.

Tests to add: a validator test per rule (R1–R10) for each launch state, a Lumora import round-trip for one multi-vehicle term, and a declarations-page snapshot.

## 9. Open questions

1. ~~**Non-auto policy types.**~~ **Decided 2026-11-24:** keep them. Homeowners, renters and condo come in Wave 2 and umbrella in Wave 3; see [US_PRODUCT_CATALOG.md](US_PRODUCT_CATALOG.md). Until then, hide them in the UI.
2. **Default term.** Offer both 6 and 12 months, or 12 only at launch? Lumora generates 12-month terms only.
3. **Driver exclusions.** Allowed in all five launch states? This needs a per-state check before R9 is built.
4. **UMPD and stacking.** Out of scope at launch, or needed for GA and CA?
5. **Licence and PII handling.** Driver licence numbers need encryption at rest and masking. Agree the approach before Phase 2 adds them.

## Sources

- [ISO PP 00 01 01 05 form, Virginia SCC copy](https://appspre.scc.virginia.gov/boi/co/pc/auto/PP00010105.pdf)
- [SOA GI-302 study note: US policies](https://www.soa.org/globalassets/assets/files/edu/2025/fall/study-note/2025-11-gi-302-study-note-us-policies.pdf)
- [MoneyGeek: state minimum car insurance requirements (2026)](https://www.moneygeek.com/insurance/auto/state-minimum-car-insurance-requirements/)
- [Insurance.com: states changing minimums for 2026](https://insurance.com/auto-insurance/states-with-minimum-car-insurance-requirement-changes/)

The per-state UM, PIP, credit and gender rules in §4 come from general industry knowledge, not from these sources. Check each against the state's Department of Insurance (Ohio DOI, Texas DOI, Florida OIR, Georgia OCI, California DOI) before Phase 5.
