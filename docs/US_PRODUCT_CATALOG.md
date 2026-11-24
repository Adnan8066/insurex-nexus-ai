# Spec: US personal lines product catalog

Status: draft, 2026-11-24. Extends [US_MIGRATION_PLAN.md](US_MIGRATION_PLAN.md) and [US_POLICY_SPEC.md](US_POLICY_SPEC.md).

InsureX targets the policies US households actually buy, so it can sell and service them together (a "bundle"). This spec lists those products, how each is structured, what InsureX needs to support them, and the order to build them in. Rating figures are placeholders, not filed rates.

> **Verify before relying on it.** State rules (hurricane deductibles, residual markets, credit restrictions) change often. Check every state rule with the state's Department of Insurance before it reaches production.

## 1. Which products, and why

US households usually insure their car and their home with the same company. Insurers encourage this with a multi-policy discount, because bundled customers renew more often. A US personal lines platform is expected to offer at least auto, home and renters.

| Product | ISO form | Who buys it | InsureX scope |
| --- | --- | --- | --- |
| **Personal auto** | PP 00 01 | Almost every adult with a car; required by law | **Launch.** Specified in [US_POLICY_SPEC.md](US_POLICY_SPEC.md) |
| **Homeowners** | HO 00 03 (HO-3) | Owners of a house; required by mortgage lenders | **Wave 2** |
| **Renters** | HO 00 04 (HO-4) | Tenants; often required by landlords | **Wave 2** |
| **Condo** | HO 00 06 (HO-6) | Condo unit owners | **Wave 2** |
| **Personal umbrella** | DL 98 01 or insurer form | Households wanting $1M+ extra liability | **Wave 3** |
| Motorcycle, RV, boat | Insurer forms | Owners of these vehicles | Later |
| Landlord (dwelling fire) | DP-3 | Owners renting a house out | Later |
| Flood | NFIP or private | Homes in flood zones (homeowners policies exclude flood) | Later, as a partner or referral product |
| Earthquake | CEA (CA) or private | Mainly CA homes | Later, as a partner or referral product |

**Out of scope:** health, life, disability and commercial lines. They use different licences, regulators and claim processes, and don't fit a motor and property claims platform.

## 2. Homeowners (HO-3)

### Coverage structure

| Section | Coverage | What it pays | Typical limit |
| --- | --- | --- | --- |
| I | **A – Dwelling** | The house and attached structures | Cost to rebuild (from a replacement-cost estimator), **not** market value |
| I | **B – Other structures** | Detached garage, fence, shed | 10% of A |
| I | **C – Personal property** | Belongings | 50–70% of A |
| I | **D – Loss of use** | Extra living costs while the home can't be lived in | 20–30% of A |
| II | **E – Personal liability** | Injury or damage the household causes to others | $100k, $300k, $500k |
| II | **F – Medical payments to others** | Guests' minor injuries, regardless of fault | $1k–$5k |

- **Perils:** HO-3 covers the dwelling against all risks except those excluded ("open perils"), and belongings only against listed causes ("named perils"). HO-5 covers both on open perils. Standard exclusions include flood, earthquake, wear and tear, and neglect.
- **Settlement:** replacement cost on the dwelling. Belongings are paid at actual cash value unless the replacement-cost endorsement is added.
- **Deductibles:** an all-peril deductible ($500–$2,500), plus in some states a separate **percentage** deductible for wind or hurricane (for example 2% of Coverage A).
- **Common endorsements:** replacement cost on contents, extended replacement cost (125%), scheduled valuables (jewelry, art), water backup, ordinance or law, service line, equipment breakdown, identity theft.
- **Mortgagee clause:** the lender is listed on the policy and is paid on large dwelling claims. Premiums are often paid by the lender from escrow.

### Renters (HO-4) and condo (HO-6)

- **Renters:** Coverages C, D, E and F only. There is no dwelling coverage, because the landlord insures the building. Premiums are low, often $15–$30 a month.
- **Condo:** Coverage A covers only the "walls-in" (interior finishes and improvements), because the association insures the building. It adds **loss assessment** coverage for the owner's share of an association claim.

### Rating factors (Wave 2)

Territory (ZIP or finer), fire protection class (ISO PPC 1–10), construction type (frame, masonry), year built, **roof age and material**, Coverage A amount, deductible, prior claims (from the CLUE claims history database), credit-based insurance score where allowed, protective devices (alarms, sprinklers), wind mitigation features, and the multi-policy discount.

### State notes for the launch states

| State | What matters for home |
| --- | --- |
| **FL** | Hurricane deductibles (percentage of Coverage A). Insurers must offer **wind mitigation discounts**. The state-run Citizens Property Insurance writes many homes. Sinkhole and catastrophic ground cover collapse rules. Roof and water claim fraud: the 2022–2023 reforms ended assignment of benefits (AOB) for new policies |
| **TX** | Wind and hail percentage deductibles are common. Coastal wind is often written by the Texas Windstorm Insurance Association (TWIA) instead of the home policy |
| **CA** | Wildfire risk drives availability. The state FAIR Plan is the insurer of last resort. Insurers must offer earthquake cover (usually through the CEA). Prop 103 rules apply, and credit can't be used |
| **GA, OH** | Standard ISO-style forms. Wind and hail are the main weather perils |

### Home claims and fraud signals

FNOL for home records the cause of loss (wind, hail, water, fire, theft, liability), a catastrophe code during storms, damage to the dwelling and to contents, and loss of use. Common red flags:
- A fire or theft soon after the policy starts, or after coverage was increased
- Contents claimed that are worth more than the household is likely to own, or no receipts
- Repeated water claims at the same address
- Theft without a police report
- Roof claims filed by a contractor soon after a storm that missed the area
- A claim filed while the policy was being cancelled or not renewed

## 3. Personal umbrella

- Adds **$1M to $5M** of liability on top of the auto and home policies. It pays only after the underlying policy's limit is used up.
- **Required underlying limits** (typical, set by the insurer): auto 250/500/100 (or $300k CSL), home liability $300k. A **self-insured retention**, often $250–$1,000, applies to claims the underlying policies don't cover.
- Rated by number of drivers, vehicles, homes, youthful drivers, pools, trampolines, dogs and watercraft.
- **InsureX rule:** an umbrella can only be bound when the household's auto and home policies meet the required limits. That's easiest when InsureX also writes those policies, which is why umbrella comes after Wave 2.

## 4. What this changes in the data model

The auto spec designs the policy around vehicles. To add home lines without a second rebuild, Phase 2 should make the policy **line-agnostic** from the start:

| Change | Detail |
| --- | --- |
| `Policy.type` → `Policy.line` + `Policy.form` | `line`: `personal_auto`, `homeowners`, `condo`, `renters`, `umbrella`. `form`: `PP0001`, `HO3`, `HO5`, `HO4`, `HO6`, … |
| New `Household` (or `Account`) | Groups a customer's policies for bundling discounts, umbrella underlying checks and a single view in the customer portal |
| Auto-only data stays in auto tables | `PolicyVehicle`, `PolicyDriver` and the auto limit fields from the auto spec are used only when `line = personal_auto` |
| New `Property` (Wave 2) | Address, ZIP, county, year built, construction, roof material and year, square footage, stories, protection class, distance to coast, occupancy (owner, tenant, landlord), mortgagee |
| New `PropertyCoverage` (Wave 2) | Coverages A–F, all-peril deductible, wind/hurricane deductible (flat or percentage), settlement basis, endorsements |
| New `UmbrellaDetail` (Wave 3) | Limit, self-insured retention, and links to the underlying `Policy` rows |
| `Claim` | Add `line`. `vehicle` becomes optional and a nullable `property` is added. Claim features (Phase 2) use coverage codes from both lines (`COV_A` … `COV_F` for home) |
| Remove | `Policy.property_*` fields and the homeowners fields on `PolicyCoverage`, once `Property` and `PropertyCoverage` replace them |

This replaces open question 1 in the auto spec: the non-auto types stay, but they're rebuilt properly in Wave 2 instead of keeping today's placeholder fields.

## 5. Data and AI impact

- **Lumora is auto-only.** No home, renters or umbrella data exists in the project. The fraud, repair-cost and total-loss models are all auto models.
- Until home data exists, home claims are triaged with **rules only** (the red flags in §2), scored by a separate `triage_heuristic_home_v1.json`, and the UI must say no model was used.
- Getting home data means either extending `motorsynth` with a property book (dwellings, perils, catastrophe events, contents claims) or getting a client's history. Extending the generator is the larger task and should be its own plan.
- The RL routing simulator models auto claims only. Home claims use the normal least-busy assignment until it's extended.

## 6. Build order

| Wave | Products | Depends on | Main work |
| --- | --- | --- | --- |
| 1 | Personal auto | Migration plan Phases 1–9 | As planned, with the line-agnostic `Policy` from §4 built in Phase 2 |
| 2 | Homeowners, renters, condo | Wave 1, Phase 2 | `Property`, `PropertyCoverage`, home rating for the five states, home FNOL, home red-flag rules, multi-policy discount |
| 3 | Personal umbrella | Wave 2 | `UmbrellaDetail`, underlying-limit checks, umbrella rating |
| Later | Motorcycle, landlord, flood and earthquake referral | Wave 2 | |

## 7. Open questions

1. **Hurricane and wildfire exposure.** FL and CA homes carry catastrophe risk that a new insurer often avoids. Offer home in all five launch states, or start with OH, GA and TX?
2. **Home data.** Extend `motorsynth` with a property book, or wait for a client's data?
3. **Flood and earthquake.** Refer customers to partners, or leave them out entirely?
4. **Household model.** Is a household the same as the named insured's customer record, or a separate account that several customers can share (for example, spouses)?

## Sources

- [SOA GI-302 study note: US policies](https://www.soa.org/globalassets/assets/files/edu/2025/fall/study-note/2025-11-gi-302-study-note-us-policies.pdf)
- [ISO PP 00 01 01 05 form, Virginia SCC copy](https://appspre.scc.virginia.gov/boi/co/pc/auto/PP00010105.pdf)

The homeowners, renters, condo and umbrella structures, typical limits and state notes come from general industry knowledge, not these sources. Check them against the ISO forms and each state's Department of Insurance before Wave 2.
