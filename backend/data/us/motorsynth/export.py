"""Shape the internal tables into the published schema, add light data-quality noise,
and write observable tables + a separate ground_truth folder."""
import json
import os
import numpy as np
import pandas as pd
from .util import i2d, break_vin

DAY_COLS = {"terms": ["term_start", "term_end", "cancel_date"]}


def _d(a):
    a = np.asarray(a)
    out = i2d(np.where(a < 0, 0, a))
    return np.where(a < 0, np.datetime64("NaT"), out)


def _clean(df):
    return df[[c for c in df.columns if not str(c).startswith("_")]].copy()


def build(W):
    cfg = W.cfg
    hh, dr, ve, T, vt = W.t["households"], W.t["drivers"], W.t["vehicles"], W.t["terms"], W.t["vt"]
    C, F, L, B = W.table("claims"), W.table("features"), W.table("estimate_lines"), W.table("medical_bills")
    out = {}
    out["producers"] = _clean(W.t["producers"])
    out["employees"] = _clean(W.t["employees"])
    out["service_providers"] = _clean(W.t["parties"]).rename(columns={"party_id": "provider_id", "party_type": "provider_type"})
    cu = hh[["customer_id", "first_name", "middle_name", "last_name", "suffix", "gender", "date_of_birth", "address", "city", "state",
             "zip", "phone", "email", "credit_tier", "homeowner", "customer_since", "channel", "producer_id"]].copy()
    out["customers"] = cu
    d = dr[dr._listed].copy()
    out["drivers"] = _clean(d)
    out["vehicles"] = ve[["vehicle_id", "customer_id", "vin", "model_year", "make", "model", "body_type", "segment", "msrp",
                          "adas_equipped", "lienholder_flag", "declared_usage", "declared_annual_miles", "garaging_zip"]].copy()
    t = T.copy()
    for c in DAY_COLS["terms"]:
        t[c] = _d(t[c].values)
    t["bind_datetime"] = i2d(T.bind_datetime.values).astype("datetime64[m]") + (T._bind_hour.values * 60 + W.rng.integers(0, 60, len(T))).astype("timedelta64[m]")
    t["nsf_payment_count"] = hh._missed_payments.values[T._hh.values]
    out["policy_terms"] = _clean(t)
    pv = vt[["term_id", "vehicle_id", "coll_deductible", "comp_deductible", "rental_coverage", "towing_coverage", "exp_years"] +
            [c for c in vt.columns if c.startswith("premium_")] + ["vehicle_premium", "earned_premium"]].rename(columns={"exp_years": "earned_exposure_years"})
    out["policy_vehicles"] = pv
    pdv = T[["term_id", "customer_id"]].merge(d[["driver_id", "customer_id", "relationship"]], on="customer_id")
    out["policy_drivers"] = pdv[["term_id", "driver_id", "relationship"]]
    c = C.copy()
    c["loss_metro_city"] = c.loss_city
    out["claims"] = _clean(c.drop(columns=["loss_metro_city"]))
    f = F.copy()
    f["attorney_retained_date"] = np.where(f.attorney_party_id.values != "", i2d(f._rep_day.values + np.nan_to_num(f._att_days.values).astype(int)), np.datetime64("NaT"))
    f = f.rename(columns={"subtype": "loss_subtype", "repairer_party_id": "repair_vendor_id", "attorney_party_id": "attorney_id"})
    keep = ["feature_id", "claim_id", "coverage", "loss_subtype", "claimant_id", "claimant_role", "injury_type", "tp_vehicle_vin",
            "tp_vehicle_desc", "repair_vendor_id", "attorney_id", "attorney_retained_date", "acv", "theft_recovered", "total_loss_flag",
            "loss_amount", "deductible_applied", "limit_applied", "tow_storage_amount", "rental_days", "paid_amount", "reserve_amount",
            "salvage_recovery", "subrogation_potential", "subrogation_status", "subrogation_recovery", "status", "open_date", "close_date"]
    f["rental_days"] = f.get("rental_days", pd.Series(np.nan, index=f.index))
    f["loss_subtype"] = f.loss_subtype.replace({"AF_MULTI": "COLLISION", "AF_SINGLE": "COLLISION", "NAF": "COLLISION", "NAF_UNINSURED": "COLLISION"})
    out["claim_features"] = f[keep]
    l = L.copy()
    l = l.sort_values(["feature_id", "is_supplement", "written_date", "zone"], kind="stable")
    l["line_no"] = l.groupby("feature_id").cumcount() + 1
    l.insert(0, "estimate_line_id", W.ids.take("EST", len(l), 9))
    out["estimate_lines"] = l[["estimate_line_id", "feature_id", "claim_id", "line_no", "zone", "operation", "part_name", "part_type",
                               "quantity", "body_labor_hours", "refinish_hours", "labor_rate", "paint_rate", "part_amount", "line_amount",
                               "vendor_party_id", "is_supplement", "written_date"]].rename(columns={"vendor_party_id": "sublet_vendor_id"})
    b = B.copy().sort_values(["feature_id", "service_date"], kind="stable")
    b.insert(0, "bill_id", W.ids.take("MBL", len(b), 9))
    out["medical_bills"] = b[["bill_id", "feature_id", "claim_id", "claimant_id", "provider_party_id", "service_date", "service_code",
                              "service_desc", "diagnosis_group", "units", "billed_amount", "allowed_amount"]].rename(columns={"provider_party_id": "provider_id"})
    out["payments"] = _clean(W.t["payments"]).sort_values(["claim_id", "issue_date"], kind="stable")
    out["recoveries"] = _clean(W.t["recoveries"])
    s = W.t["siu"]
    out["siu_investigations"] = s[["investigation_id", "claim_id", "referral_date", "referral_source", "investigator_id", "outcome", "closed_date"]]
    P = W.table("persons")
    used = set(F.claimant_id.dropna()) | set(B.claimant_id.dropna())
    out["claim_persons"] = P[P.claimant_id.isin(used)].rename(columns={"claimant_id": "person_id"})
    return out


def data_quality(W, out):
    """Light, logged noise. Every change is written to ground_truth/data_quality_log."""
    rng, dq = W.rng, W.cfg["data_quality"]
    log = []
    if not dq.get("enabled", True):
        return out, pd.DataFrame(columns=["table", "record_id", "issue", "detail"])
    cu = out["customers"]
    m = rng.random(len(cu)) < dq["missing_email"]
    cu.loc[m, "email"] = None
    log.append(pd.DataFrame({"table": "customers", "record_id": cu.customer_id[m], "issue": "MISSING_EMAIL", "detail": ""}))
    m = rng.random(len(cu)) < dq["missing_phone"]
    cu.loc[m, "phone"] = None
    log.append(pd.DataFrame({"table": "customers", "record_id": cu.customer_id[m], "issue": "MISSING_PHONE", "detail": ""}))
    z0 = cu.zip.str.startswith("0") & (rng.random(len(cu)) < dq["zip_leading_zero_dropped"])
    cu.loc[z0, "zip"] = cu.loc[z0, "zip"].str[1:]
    log.append(pd.DataFrame({"table": "customers", "record_id": cu.customer_id[z0], "issue": "ZIP_LEADING_ZERO_DROPPED", "detail": ""}))
    # duplicate customer records (same person, second id, small variation)
    m = rng.random(len(cu)) < dq["duplicate_customer_record"]
    dup = cu[m].copy()
    orig = dup.customer_id.values
    dup["customer_id"] = W.ids.take("CUS", len(dup), 7)
    var = rng.integers(0, 3, len(dup))
    dup["first_name"] = np.where(var == 0, dup.first_name.str[:1] + ".", dup.first_name)
    dup["email"] = np.where(var == 1, None, dup.email)
    dup["address"] = np.where(var == 2, dup.address.str.replace(" St", " Street").str.replace(" Ave", " Avenue"), dup.address)
    out["customers"] = pd.concat([cu, dup], ignore_index=True)
    log.append(pd.DataFrame({"table": "customers", "record_id": dup.customer_id.values, "issue": "DUPLICATE_CUSTOMER_RECORD", "detail": orig}))
    ve = out["vehicles"]
    m = rng.random(len(ve)) < dq["make_model_typo"]
    typo = {"Chevrolet": "Chevy", "Volkswagen": "VW", "Mercedes-Benz": "Mercedes", "Toyota": "TOYOTA", "Honda": "honda", "Ford": "FORD"}
    ve.loc[m, "make"] = ve.loc[m, "make"].map(lambda x: typo.get(x, x.upper()))
    log.append(pd.DataFrame({"table": "vehicles", "record_id": ve.vehicle_id[m], "issue": "MAKE_VARIANT_SPELLING", "detail": ""}))
    m = rng.random(len(ve)) < dq["invalid_vin_checkdigit"]
    ve.loc[m, "vin"] = [break_vin(rng, v) for v in ve.loc[m, "vin"]]
    log.append(pd.DataFrame({"table": "vehicles", "record_id": ve.vehicle_id[m], "issue": "VIN_KEYING_ERROR", "detail": ""}))
    c = out["claims"]
    m = rng.random(len(c)) < dq["report_before_loss_date"]
    c.loc[m, "report_datetime"] = c.loc[m, "loss_datetime"] - pd.to_timedelta(rng.integers(1, 3, m.sum()), "D")
    log.append(pd.DataFrame({"table": "claims", "record_id": c.claim_id[m], "issue": "REPORT_BEFORE_LOSS_DATE", "detail": ""}))
    return out, pd.concat(log, ignore_index=True)


def write(W, out, truth, folder):
    cfg = W.cfg
    os.makedirs(folder, exist_ok=True)
    gt = os.path.join(folder, "ground_truth")
    os.makedirs(gt, exist_ok=True)
    sizes = {}
    def _w(df, path):
        if cfg["run"].get("write_parquet", True):
            df.to_parquet(path + ".parquet", index=False)
        if cfg["run"].get("write_csv", True):
            df.to_csv(path + ".csv", index=False)
    for k, df in out.items():
        _w(df, os.path.join(folder, k)); sizes[k] = len(df)
    for k, df in truth.items():
        _w(df, os.path.join(gt, k)); sizes["ground_truth/" + k] = len(df)
    json.dump({**cfg["company"], "as_of_date": cfg["run"]["as_of_date"], "window": [cfg["run"]["window_start"], cfg["run"]["window_end"]],
               "note": "Fictional company. All people, businesses, phone numbers (555 exchange) and accounts are synthetic."},
              open(os.path.join(folder, "company.json"), "w", encoding="utf-8"), indent=2)
    json.dump(W.storylines, open(os.path.join(gt, "storylines.json"), "w", encoding="utf-8"), indent=2, default=str)
    return sizes
