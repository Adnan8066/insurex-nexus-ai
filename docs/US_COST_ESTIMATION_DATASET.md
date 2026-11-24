# US repair-cost estimation dataset: format

Status: proposed format, 2026-11-23. Nothing reads this format yet. Phase 3 of [US_MIGRATION_PLAN.md](US_MIGRATION_PLAN.md) builds the importer and the new repair-cost and total-loss models on it.

## Why a new format

Today's repair-cost model trains on `backend/data/insurance_claims.csv`. It has 1,000 rows, its target is `vehicle_claim`, and its inputs are mostly about the policyholder (age, premium, deductible) rather than the damage. It knows nothing about labor rates, parts, impact areas, airbags or the location of the loss, and those drive US repair costs most.

The format below describes the **vehicle damage** of each claim, the way a US appraisal does, so the model can learn cost from the damage itself. It is built so that:

- the Lumora synthetic data (`backend/data/us/`) converts into it directly;
- a carrier's own estimating export (CCC ONE, Mitchell or Audatex, flattened to CSV) can be mapped into it later;
- every input is something InsureX knows, or can ask, when the claim is filed.

## Files

| File | One row per | Required? | Used for |
| --- | --- | --- | --- |
| `repair_cost_claims.csv` | vehicle damage on a claim (one coverage line: collision, comprehensive or property damage) | **Yes** | Training the repair-cost and total-loss models |
| `repair_estimate_lines.csv` | line on the shop or appraiser estimate | Optional | Explaining estimates, padding detection, a future line-level model |

Rules for both files:

- UTF-8 CSV with a header row; comma separated; `.` as the decimal point.
- Money in **US dollars**, without `$` or thousands separators (`2450.00`, not `$2,450`).
- Dates as `YYYY-MM-DD`; date-times as `YYYY-MM-DD HH:MM` in the local time of the loss.
- Booleans as `true` / `false`.
- Empty cell = unknown. Never write `?`, `N/A` or `0` for "unknown".
- Category values in the exact spelling listed below (upper case).
- No names, street addresses, phone numbers, licence numbers or full VINs. Use the ZIP code and the first 11 characters of the VIN at most.

## `repair_cost_claims.csv`

The **When known** column matters for training. A model that scores claims at first notice of loss (FNOL) may only use `FNOL` columns. `ESTIMATE` columns are known only after an appraiser or shop has looked at the car. Use them in a second, more accurate model, or leave them out. `OUTCOME` columns are what the model learns to predict, and they must never be used as inputs.

### Identifiers

| Column | Type | Required | When known | Description |
| --- | --- | --- | --- | --- |
| `record_id` | text | yes | — | Unique row ID, for example `FEA00000001` |
| `claim_id` | text | yes | — | Claim the row belongs to. A claim can have several rows (own car under collision plus a third-party car under PD) |
| `source` | text | yes | — | Where the row came from: `LUMORA`, `CARRIER_<name>`, `MANUAL` |

### Vehicle

| Column | Type | Required | When known | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `model_year` | integer | yes | FNOL | e.g. `2022` |
| `make` | text | yes | FNOL | e.g. `Toyota` |
| `model` | text | yes | FNOL | e.g. `RAV4` |
| `trim` | text | no | FNOL | e.g. `XLE` |
| `body_type` | category | yes | FNOL | `SEDAN`, `COUPE`, `SUV`, `PICKUP`, `MINIVAN`, `WAGON`, `HATCHBACK`, `VAN` |
| `segment` | category | yes | FNOL | `SEDAN_SMALL`, `SEDAN_MID`, `SUV_SMALL`, `SUV_MID`, `SUV_LARGE`, `PICKUP`, `MINIVAN`, `WAGON`, `SPORTS`, `LUXURY`, `LUXURY_SUV`, `EV` |
| `fuel_type` | category | yes | FNOL | `GASOLINE`, `DIESEL`, `HYBRID`, `ELECTRIC` |
| `msrp` | money | yes | FNOL | Price when new |
| `actual_cash_value` | money | yes | FNOL | Pre-loss value of the vehicle (ACV). Total-loss decisions compare repair cost with it |
| `odometer_miles` | integer | no | FNOL | Reading at the loss |
| `adas_equipped` | boolean | yes | FNOL | Has cameras and radar that need calibration after repair |
| `vin_prefix` | text | no | FNOL | First 11 VIN characters only (make, model and plant; no serial) |

### Loss

| Column | Type | Required | When known | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `loss_date` | date | yes | FNOL | |
| `report_date` | date | yes | FNOL | When the claim was reported |
| `loss_state` | category | yes | FNOL | Two-letter state: `OH`, `TX`, `FL`, `GA`, `CA` (launch states), others allowed |
| `loss_zip` | text | yes | FNOL | 5 digits; the model uses the first 3 (labor costs vary by area) |
| `coverage` | category | yes | FNOL | `COLL` (own car, collision), `COMP` (own car, other than collision), `PD` (third party's car), `UMPD` |
| `loss_cause` | category | yes | FNOL | `COLLISION_SINGLE`, `COLLISION_MULTI`, `HIT_WHILE_PARKED`, `ANIMAL`, `GLASS`, `HAIL`, `FLOOD`, `FIRE`, `THEFT`, `VANDALISM`, `WEATHER_OTHER` |
| `catastrophe_code` | text | no | FNOL | Event code when the loss belongs to a catastrophe (hail, flood) |
| `vehicles_involved` | integer | yes | FNOL | `1` and up |
| `point_of_impact` | category | yes | FNOL | Main area hit: `FRONT`, `REAR`, `LEFT`, `RIGHT`, `TOP`, `UNDERCARRIAGE`, `GLASS`, `INTERIOR`, `NONE` |
| `impact_areas` | text | no | FNOL | All areas hit, `;` separated, e.g. `FRONT;LEFT` |
| `reported_severity` | category | yes | FNOL | What the customer reports: `MINOR`, `MODERATE`, `MAJOR`, `TOTAL_LOSS` |
| `airbags_deployed` | boolean | yes | FNOL | |
| `drivable` | boolean | yes | FNOL | Car could be driven after the loss |
| `towed` | boolean | yes | FNOL | |
| `injuries` | boolean | yes | FNOL | Anyone hurt (a sign of impact force) |
| `police_report` | boolean | yes | FNOL | |
| `deductible` | money | yes | FNOL | Deductible on this coverage; `0` for PD |

### Estimate (known after inspection)

| Column | Type | Required | When known | Notes |
| --- | --- | --- | --- | --- |
| `repair_facility_type` | category | no | ESTIMATE | `DRP` (direct-repair shop), `INDEPENDENT`, `DEALER`, `MOBILE_GLASS` |
| `labor_rate` | money | no | ESTIMATE | Body labor $/hour at the shop |
| `paint_rate` | money | no | ESTIMATE | Refinish $/hour |
| `body_labor_hours` | decimal | no | ESTIMATE | Sum over estimate lines |
| `refinish_hours` | decimal | no | ESTIMATE | |
| `frame_hours` | decimal | no | ESTIMATE | Frame or structural labor |
| `mechanical_hours` | decimal | no | ESTIMATE | |
| `parts_oem_amount` | money | no | ESTIMATE | Original-equipment parts |
| `parts_aftermarket_amount` | money | no | ESTIMATE | |
| `parts_used_amount` | money | no | ESTIMATE | Recycled (LKQ) parts |
| `adas_calibration_amount` | money | no | ESTIMATE | Camera and radar calibration |
| `sublet_amount` | money | no | ESTIMATE | Work sent out (glass, alignment) |
| `tow_storage_amount` | money | no | ESTIMATE | Towing plus storage fees |
| `rental_days` | integer | no | ESTIMATE | |
| `supplement_count` | integer | no | ESTIMATE | Extra estimates added after teardown |
| `initial_estimate_amount` | money | no | ESTIMATE | First appraiser or shop estimate |

### Outcome (targets)

| Column | Type | Required | When known | Notes |
| --- | --- | --- | --- | --- |
| `final_repair_cost` | money | **yes** | OUTCOME | **Main target.** Agreed repair cost before the deductible (parts + labor + paint + sublet + tax). For a total loss, the ACV settlement |
| `total_loss` | boolean | **yes** | OUTCOME | Second target: declared a total loss |
| `paid_amount` | money | yes | OUTCOME | Paid by the insurer, after the deductible |
| `salvage_recovery` | money | no | OUTCOME | Received for the wreck after a total loss |
| `subrogation_recovery` | money | no | OUTCOME | Recovered from an at-fault party |
| `closed_date` | date | yes | OUTCOME | Only closed rows are used for training |
| `is_suspected_inflated` | boolean | no | OUTCOME | Set from SIU findings or Lumora ground truth. Rows marked `true` are left out of cost training, so padded bills don't teach the model to overestimate |

## `repair_estimate_lines.csv` (optional)

One row per line on an estimate. It uses the same layout as Lumora's `estimate_lines.csv`, so the synthetic data loads without changes.

| Column | Type | Notes |
| --- | --- | --- |
| `estimate_line_id` | text | Unique line ID |
| `record_id` | text | Links to `repair_cost_claims.record_id` |
| `line_no` | integer | Order on the estimate |
| `zone` | category | `FRONT`, `REAR`, `LEFT`, `RIGHT`, `TOP`, `GLASS`, `SUBLET` |
| `operation` | category | `REPAIR`, `REPLACE`, `REFINISH`, `BLEND`, `R&I` (remove and install), `SUBLET` |
| `part_name` | text | e.g. `Rear bumper cover` |
| `part_type` | category | `OEM`, `AFTERMARKET`, `LKQ_USED`, `REMAN`, empty for labor-only lines |
| `quantity` | integer | |
| `body_labor_hours` | decimal | |
| `refinish_hours` | decimal | |
| `labor_rate` | money | $/hour |
| `paint_rate` | money | $/hour |
| `part_amount` | money | |
| `line_amount` | money | Parts + labor + paint for the line |
| `is_supplement` | boolean | Added after the first estimate |
| `written_date` | date | |

## How Lumora fills it

| Format column | Lumora source |
| --- | --- |
| `record_id`, `claim_id`, `coverage` | `claim_features.feature_id`, `claim_id`, `coverage` (keep `COLL`, `COMP`, `PD`, `UMPD`) |
| `model_year`, `make`, `model`, `body_type`, `segment`, `msrp`, `adas_equipped` | `vehicles` (own car), or `claim_features.tp_vehicle_desc` (third-party car) |
| `actual_cash_value`, `total_loss` | `claim_features.acv`, `total_loss_flag` |
| `loss_date`, `report_date`, `loss_state`, `loss_zip`, `vehicles_involved`, `police_report`, `catastrophe_code`, `odometer_miles` | `claims` |
| `loss_cause` | `claims.loss_cause` mapped: `AF_SINGLE`→`COLLISION_SINGLE`, `AF_MULTI`/`NAF`/`NAF_UNINSURED`→`COLLISION_MULTI`, `WEATHER`→`HAIL` or `WEATHER_OTHER` (by `catastrophe_code`), others by name |
| `point_of_impact`, `impact_areas`, hours, parts split, `sublet_amount`, `supplement_count` | Summed from `estimate_lines` |
| `labor_rate`, `paint_rate`, `repair_facility_type` | `estimate_lines`, `service_providers.labor_rate`, `drp_flag` |
| `tow_storage_amount`, `rental_days`, `deductible` | `claim_features` |
| `final_repair_cost` | `claim_features.loss_amount` |
| `paid_amount`, `salvage_recovery`, `subrogation_recovery`, `closed_date` | `claim_features` |
| `is_suspected_inflated` | `ground_truth/truth_claims` (`SOFT_ESTIMATE_PADDING` and ring scenarios). Training data only, never loaded into the app |
| `airbags_deployed`, `drivable`, `towed`, `injuries`, `reported_severity` | Not in Lumora directly. Derive them: `towed` from `tow_storage_amount > 0`, `injuries` from BI/PIP features on the claim, `reported_severity` from loss amount ÷ ACV bands. Mark them as derived in the importer |

## How it maps to the InsureX claim form

| Format column | InsureX field today | Gap |
| --- | --- | --- |
| `loss_date`, `report_date` | `Claim.incident_date`, `submitted_at` | — |
| `loss_cause` | `Claim.incident_type` | Needs single vs multi-vehicle collision and hit-while-parked; `water_damage` becomes `FLOOD` |
| `reported_severity` | `Claim.incident_severity` | — |
| `vehicles_involved`, `injuries`, `police_report` | same names on `Claim` | — |
| `point_of_impact`, `impact_areas`, `airbags_deployed`, `drivable`, `towed` | **missing** | Add to the claim form (Phase 2) |
| `loss_state`, `loss_zip` | only free-text `Claim.location` | Add structured fields (Phase 2) |
| `msrp`, `actual_cash_value`, `adas_equipped`, `segment` | `Vehicle.purchase_price` only | Add to `Vehicle` (Phase 2) |
| `deductible`, `coverage` | `Policy.deductible`, `PolicyCoverage` | Deductible per coverage (Phase 2) |

## Quality checks the importer should run

- `final_repair_cost` > 0 and `closed_date` is set for every training row.
- `report_date` ≥ `loss_date`, and `loss_date` within the policy term.
- `final_repair_cost` ≤ about 1.2 × `actual_cash_value`, unless `total_loss` is `true`.
- `labor_rate` between $35 and $200 an hour; `body_labor_hours` below 120.
- Estimate-line totals within 2% of the row's hours and parts amounts.
- Category values only from the lists above; reject the file with a list of bad rows otherwise.

Template files with example rows: `backend/data/us/templates/repair_cost_claims_template.csv` and `repair_estimate_lines_template.csv`.
