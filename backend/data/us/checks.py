"""Integrity and realism checks on a generated output folder:  python checks.py output"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1] if len(sys.argv) > 1 else "output"
rd = lambda n: pd.read_parquet(os.path.join(d, n + ".parquet"))
cu, dr, ve, T, pv = rd("customers"), rd("drivers"), rd("vehicles"), rd("policy_terms"), rd("policy_vehicles")
C, F, L, B, P, Rc, S = rd("claims"), rd("claim_features"), rd("estimate_lines"), rd("medical_bills"), rd("payments"), rd("recoveries"), rd("siu_investigations")
SP, PE, PR, EM = rd("service_providers"), rd("claim_persons"), rd("producers"), rd("employees")
ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")

print("== referential integrity")
check("claims.term_id in policy_terms", C.term_id.isin(T.term_id).all())
check("claims.vehicle_id in vehicles", C.vehicle_id.isin(ve.vehicle_id).all())
check("claims.operator_driver_id in drivers (when listed)", C[C.operator_driver_id != ""].operator_driver_id.isin(dr.driver_id).all())
check("features.claim_id in claims", F.claim_id.isin(C.claim_id).all())
ids = set(PE.person_id) | set("INS-" + cu.customer_id) | set("DRV-" + dr.driver_id)
check("features.claimant_id resolvable", F.claimant_id.isin(ids).all(), f"({(~F.claimant_id.isin(ids)).sum()} unresolved)")
check("estimate_lines.feature_id in features", L.feature_id.isin(F.feature_id).all())
check("medical_bills.feature_id in features", B.feature_id.isin(F.feature_id).all())
check("medical_bills.provider_id in providers", B.provider_id.isin(SP.provider_id).all())
check("payments.claim_id in claims", P.claim_id.isin(C.claim_id).all())
payees = set(SP.provider_id) | set(cu.customer_id) | set(PE.person_id) | set(dr.driver_id)
check("payments.payee_id resolvable", P.payee_id.isin(payees).all(), f"({(~P.payee_id.isin(payees)).sum()} unresolved)")
check("policy_vehicles keys", pv.term_id.isin(T.term_id).all() and pv.vehicle_id.isin(ve.vehicle_id).all())
check("terms.producer_id in producers", T.producer_id.isin(PR.producer_id).all())
check("claims.adjuster_id in employees", C.adjuster_id.isin(EM.employee_id).all())
check("siu.claim_id in claims", S.claim_id.isin(C.claim_id).all())

print("== temporal sanity")
ts = pd.to_datetime(T.set_index("term_id").term_start)
te = pd.to_datetime(T.set_index("term_id").term_end)
ld = pd.to_datetime(C.loss_datetime).dt.normalize()
inside = (ld.values >= ts.reindex(C.term_id).values) & (ld.values <= te.reindex(C.term_id).values)
check("loss date inside its policy term", inside.mean() > 0.999, f"({inside.mean():.4%})")
lag = (pd.to_datetime(C.report_datetime) - pd.to_datetime(C.loss_datetime)).dt.total_seconds() / 86400
check("report after loss (DQ noise excepted)", (lag >= 0).mean() > 0.998, f"({(lag < 0).sum()} negative, logged as DQ)")
fo, fc = pd.to_datetime(F.open_date), pd.to_datetime(F.close_date)
check("feature close >= open", ((fc >= fo) | fc.isna()).all())
sd = pd.to_datetime(B.service_date)
cl = pd.to_datetime(C.set_index("claim_id").loss_datetime).dt.normalize()
check("medical service on/after loss", (sd.values >= cl.reindex(B.claim_id).values).mean() > 0.999)
check("no payments after as-of", pd.to_datetime(P.issue_date).max() <= pd.Timestamp("2026-06-30"))

print("== financial sanity")
check("no negative paid", (F.paid_amount >= 0).all() and (P.amount > 0).all())
check("paid within limits", ((F.paid_amount <= F.limit_applied + 0.01) | F.limit_applied.isna()).all())
fp = F.groupby("claim_id").paid_amount.sum()
pp = P[P.status != "VOIDED"].groupby("claim_id").amount.sum()
gap = (pp.reindex(fp.index).fillna(0) - fp).abs()
check("payments reconcile to features (excl. planted duplicates/diversion)", (gap < 1).mean() > 0.98, f"({(gap >= 1).sum()} claims differ)")

print("== names")
full = cu.first_name + " " + cu.middle_name.str[:1] + " " + cu.last_name
check("customer full names ~unique", full.duplicated().mean() < 0.01, f"(dup rate {full.duplicated().mean():.3%})")
fn = pd.concat([cu.first_name, dr.first_name]).value_counts()
print("   top first names:", ", ".join(fn.head(12).index))
print("   Tom / Jerry present:", int(fn.get("Tom", 0)), "/", int(fn.get("Jerry", 0)))
print("   distinct first names:", len(fn), " distinct surnames:", cu.last_name.nunique())
print("   top surnames:", ", ".join(cu.last_name.value_counts().head(10).index))
print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
