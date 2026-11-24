# motorsynth: synthetic US personal-auto insurer with planted, scenario-based anomalies

This generates a coherent book for a fictional carrier, **Lumora Mutual Auto Insurance Company**: about 1M policy terms over 2023–2025, valued 2026-06-30. Most of it is clean, genuine business. On top, anomalies are planted as **scenarios**: categories with probabilistic fingerprints, not rules. Every planted dollar is logged in a separate `ground_truth/` folder.

```bash
pip install numpy pandas pyarrow pyyaml names
python -m motorsynth.generate config.yaml                      # full run (~1M terms)
python -m motorsynth.generate config.yaml --terms 50000 --out sample   # quick sample
python checks.py output                                        # integrity + realism checks
```

## Design principles

1. **Calm baseline first.** Frequencies and severities are calibrated to Verisk's 2024 Personal Auto figures. Premium is solved so the whole book lands on the target loss ratio. Noise is light and logged.
2. **Anomalies are families, not flags.** Each scenario lists fingerprints with probabilities. Every instance draws its own subset, intensity, place and time. No single field identifies a scenario, and no two instances look identical.
3. **Same factory for good and bad.** Genuine and planted claims are built by one `ClaimFactory`, so they are structurally indistinguishable. Only their statistics differ.
4. **Look-alikes on purpose.** Hail and flood catastrophes, a Kia/Hyundai theft wave, winter pileups sharing one police report, and late reports from hospitalized claimants are genuine, but they trip naive rules.
5. **Dollar-exact truth.** Every feature is settled twice, as presented and as genuine. The difference is the fraud excess, so story numbers reconcile to the tables.
6. **Observable ≠ truth.** A capacity-constrained SIU only refers what it can see and sometimes gets it wrong. `siu_investigations` is the label a real carrier would have. `ground_truth/` is the label it would not have.

## Controlling the distribution (`config.yaml`)

| Knob | Effect |
|---|---|
| `run.target_policy_terms` | Book size; ring sizes scale with it (config counts are per 1M terms) |
| `frequency.*`, `severity.*` | Genuine claim generation |
| `scenarios.<NAME>.prevalence` | Share of eligible units (claims, features, policies, vehicles, payments) |
| `scenarios.<NAME>.signals` | Fingerprint probabilities; lower them to make a scenario harder to detect |
| `scenarios.<NAME>.geo`, `window` | Where and when a scenario is active (rings are local and time-bound) |
| `scenarios.<NAME>.enabled` | Switch any scenario off |
| `siu.*` | How much the carrier currently catches |
| `data_quality.*` | Noise rates (set `enabled: false` for pristine data) |

## Scenario catalog

| Family | Scenario | What it looks like in the data |
|---|---|---|
| Soft fraud | `SOFT_ESTIMATE_PADDING` | Unrelated-zone lines, repair→replace, inflated labor hours, late supplements |
| | `SOFT_PRIOR_DAMAGE` | Second impact zone, rust/wear language, same zone as an earlier claim |
| | `SOFT_INJURY_BUILDUP` | Early attorney, chiro/PT volume, MRI on soft tissue, treatment gaps, low-impact/high-injury |
| Rating misrep | `SOFT_UNLISTED_DRIVER` | Claims with an operator not on the policy, usually under 25, same surname or address |
| | `SOFT_RIDESHARE_UNDISCLOSED` | Odometer far above declared miles, night/weekend losses, unrelated passengers, airport/venue locations |
| Hard fraud | `HARD_POST_LOSS_INCEPTION` | Loss 0–10 days after bind, coverage lapse, night online bind, fresh low deductibles |
| | `HARD_OWNER_GIVEUP` | Theft or fire of a financed, mid-age, high-value car; NSF payments; recent deductible drop; one key |
| | `HARD_DUPLICATE_LOSS` | Same damage lines and narrative re-claimed months later, often at a different shop |
| | `HARD_PHANTOM_VEHICLE` | Bad or cloned VIN, no lienholder on a near-new car, total loss within 90 days |
| Organized rings | `RING_BODYSHOP_HOUSTON` | Two shops whose share grows over time; supplements, replace-not-repair, affiliated tow, one inside appraiser |
| | `RING_PIP_MILL_MIAMI` | Recruited policies sharing phones and addresses; 2–4 occupants per low-speed crash; one clinic group; two attorneys; identical treatment plans |
| | `RING_SWOOP_AND_SQUAT` | LA and Atlanta crews: innocent insureds rear-end the same crew vehicles; repeat claimants; same attorney and clinics |
| | `RING_TOW_STORAGE_PHILLY` | Captured tows at 2.5–4× market rate, 15–45 storage days, tows to an affiliate shop |
| | `RING_GLASS_SOLICITATION` | Vendor-reported windshields clustered in 3 ZIPs, ADAS calibration on non-ADAS cars, repeat claims ($0 glass deductible states) |
| Producer fraud | `PRODUCER_GARAGING_EVASION` | Allentown PA agencies writing Brooklyn drivers: NY phones and licences, NY losses, shared garaging addresses |
| | `PRODUCER_GHOST_POLICIES` | Atlanta agent whose new business cancels for non-payment within 60 days; commission never charged back |
| Internal | `INTERNAL_ADJUSTER_DIVERSION` | Dallas adjuster pays a new shell vendor just under their authority limit, sometimes after claim closure; vendor may share the adjuster's home address |
| Leakage | `LEAK_*` | Missed subrogation, duplicate payments, deductible not applied, salvage not recovered |
| Benign | `BENIGN_*` | Catastrophes, theft trend, pileups, hospitalized late reports (genuine) |

## Tables

**Observable** (`output/*.parquet|csv`): `customers`, `drivers`, `vehicles`, `producers`, `employees`, `service_providers`, `policy_terms`, `policy_vehicles` (coverage and premium by coverage), `policy_drivers`, `claims`, `claim_features` (one row per coverage × claimant), `claim_persons` (third parties and passengers), `estimate_lines`, `medical_bills`, `payments`, `recoveries`, `siu_investigations`, `company.json`.

ID conventions: a `claimant_id` starting `INS-` is the named insured (`customers.customer_id`). One starting `DRV-` is a listed driver. Anything else is in `claim_persons`.

**Ground truth** (`output/ground_truth/`):
- `truth_instances`: one row per scenario × entity (claim, feature, policy, vehicle, payment, party, person, employee, VIN), with the fingerprints it drew.
- `truth_claims`: per-claim labels plus `fraud_excess_paid`, `leakage_amount`, `internal_diversion_amount` and `siu_savings`.
- `truth_policy_premium`: premium the policy *would* have paid if it had been truthful.
- `data_quality_log`, `scenario_catalog`, `scenario_distribution.csv`, `storyline_summary.csv`, `storylines.json`.

`STORY.md` is the business narrative computed from the data. `VALIDATION.md` holds the benchmarks and the realized scenario distribution.

## Notes and limits

- People and businesses are synthetic. Phones use the 555 exchange, emails use `.example` domains, and bank accounts and licence numbers are tokens. Makes and models are real US vehicles, and VINs carry valid check digits unless a scenario or DQ noise breaks them.
- Names come from US Census frequency lists (1990 first names plus a modern-name supplement for younger drivers, and 88,799 surnames). Weights are tempered so common names (James, Mary, Tom, Jerry, Smith) stay most frequent while full names are about 99.8% unique.
- State minimum limits, PIP amounts and glass-deductible rules are representative, not authoritative. ZIP codes use real 3-digit prefixes for each metro, but the 5-digit codes are generated.
- Premium is solved from losses and the target loss ratio, so average premium per vehicle is comparable to average *expenditure* (NAIC-style). It is not comparable to quoted-rate surveys for a sample driver, which run higher.
