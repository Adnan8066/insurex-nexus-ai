"""Settlement, reserves, recoveries, payments and pricing.

Every feature is settled twice: once on the amounts actually presented (lines, bills,
multipliers) and once on the *genuine* counterfactual (`_genuine_*`). The difference is the
fraud excess the ground truth reports, so the story's dollar figures add up exactly."""
import numpy as np
import pandas as pd
from . import refdata as R
from .util import d2i, i2d, lognormal, pick

TOW_PARTS = ("Towing", "Storage (per day)")


def _per_person(lim):
    return np.array([float(str(x).split("/")[0]) * 1000 for x in lim])


def assign_adjusters(W):
    rng = W.rng
    C = W.table("claims")
    F = W.table("features")
    E = W.t["employees"]
    exp = F.groupby("claim_id")._target.sum().reindex(C.claim_id).fillna(0).values
    role = np.select([exp < 6000, exp < 20000, exp < 60000], ["CLAIMS_REP", "ADJUSTER", "SENIOR_ADJUSTER"], "CLAIMS_MANAGER")
    adj = C.adjuster_id.values.astype(object).copy()
    st = C.loss_state.values
    need = adj == ""
    for (r, s), g in E[E.role != "SIU_INVESTIGATOR"].groupby(["role", "office_state"]):
        m = need & (role == r) & (st == s)
        if m.any():
            adj[m] = g.employee_id.values[rng.integers(0, len(g), m.sum())]
    left = adj == ""
    if left.any():
        pool = E[E.role.isin(["ADJUSTER", "SENIOR_ADJUSTER"])].employee_id.values
        adj[left] = pool[rng.integers(0, len(pool), left.sum())]
    C["adjuster_id"] = adj
    W.t["claims"] = C


def settle_amounts(W):
    rng, cfg = W.rng, W.cfg
    sv = cfg["severity"]
    asof = d2i(cfg["run"]["as_of_date"])
    C, F, L, B = W.table("claims"), W.table("features"), W.table("estimate_lines"), W.table("medical_bills")
    vt = W.t["vt"]
    # unrecovered thefts have no repair estimate
    th_unrec = F.feature_id[(F.subtype == "THEFT") & ~F.theft_recovered.astype(bool)]
    L = L[~L.feature_id.isin(th_unrec)].reset_index(drop=True)
    for c, g in (("_genuine_amount", "line_amount"),):
        if c not in L:
            L[c] = L[g]
    if "_genuine_allowed" not in B:
        B["_genuine_allowed"] = B["allowed_amount"]
    is_tow = L.part_name.isin(TOW_PARTS).values
    agg = pd.DataFrame({"fid": L.feature_id.values,
                        "rep": np.where(is_tow, 0, L.line_amount.values), "tow": np.where(is_tow, L.line_amount.values, 0),
                        "rep_g": np.where(is_tow, 0, L._genuine_amount.values), "tow_g": np.where(is_tow, L._genuine_amount.values, 0)}
                       ).groupby("fid").sum()
    bagg = pd.DataFrame({"fid": B.feature_id.values, "al": B.allowed_amount.values, "al_g": B._genuine_allowed.values}).groupby("fid").sum()
    fid = F.feature_id.values
    rep = agg.rep.reindex(fid).fillna(0).values; tow = agg.tow.reindex(fid).fillna(0).values
    rep_g = agg.rep_g.reindex(fid).fillna(0).values; tow_g = agg.tow_g.reindex(fid).fillna(0).values
    al = bagg.al.reindex(fid).fillna(0).values; al_g = bagg.al_g.reindex(fid).fillna(0).values
    cov = F.coverage.values; sub = F.subtype.values
    acv = F.acv.values.astype(float)
    cidx = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(F.claim_id).values
    v = vt.iloc[C._vt_idx.values[cidx]]
    veh = np.isin(cov, ["COLL", "COMP", "UMPD"])
    theft_unrec = (sub == "THEFT") & ~F.theft_recovered.values.astype(bool)
    thr = sv["total_loss_threshold"]
    tl = veh & ((theft_unrec) | (~np.isnan(acv) & (rep >= thr * np.nan_to_num(acv, nan=1e12))))
    tl_g = veh & ((theft_unrec) | (~np.isnan(acv) & (rep_g >= thr * np.nan_to_num(acv, nan=1e12))))
    ind = np.where(tl, acv + tow, rep + tow)
    ind_g = np.where(tl_g, acv + tow_g, rep_g + tow_g)
    prop = (cov == "PD") & (sub == "PROPERTY")
    ind = np.where(prop, F._target.values, ind); ind_g = np.where(prop, F._target.values, ind_g)
    gd = F._gd.values.astype(float); gd = np.where(np.isnan(gd), 1.0, gd)
    gdg = F._gd_genuine.values.astype(float); gdg = np.where(np.isnan(gdg), gd, gdg)
    inj = np.isin(cov, ["BI", "PIP", "MEDPAY", "UMBI"])
    ind = np.where(inj, al * np.where(np.isin(cov, ["BI", "UMBI"]), gd, 1.0), ind)
    ind_g = np.where(inj, al_g * np.where(np.isin(cov, ["BI", "UMBI"]), gdg, 1.0), ind_g)
    ind_g = ind_g * F._genuine_mult.values.astype(float)
    ind_g = np.where(F._fraud_full.values.astype(bool), 0.0, ind_g)
    # deductibles (FL & AZ: $0 glass by statute / common endorsement)
    glass0 = (sub == "GLASS") & np.isin(v.state.values, ["FL", "AZ"])
    ded = np.select([cov == "COLL", cov == "COMP", cov == "UMPD"],
                    [v.coll_deductible.values, v.comp_deductible.values, np.full(len(F), 250.0)], 0.0)
    ded = np.where(glass0, 0.0, np.nan_to_num(ded))
    lim = np.select([cov == "PD", np.isin(cov, ["BI", "UMBI"]), cov == "PIP", cov == "MEDPAY"],
                    [v.pd_limit.values.astype(float), _per_person(v.bi_limit.values), v.pip_limit.values.astype(float),
                     v.medpay_limit.values.astype(float)], np.inf)
    lim = np.where(lim <= 0, np.inf, lim)
    paid = np.clip(ind - ded, 0, lim)
    paid_g = np.clip(ind_g - ded, 0, lim)
    tiny = np.isin(cov, ["COLL", "COMP", "UMPD"]) & (paid < 75)      # under-deductible losses close without payment
    paid = np.where(tiny, 0.0, paid); paid_g = np.where(paid_g < 75, np.where(np.isin(cov, ["COLL", "COMP", "UMPD"]), 0.0, paid_g), paid_g)
    F["loss_amount"] = np.round(ind, 2)
    F["deductible_applied"] = np.where(ind > 0, np.minimum(ded, ind), 0)
    F["limit_applied"] = np.where(np.isinf(lim), np.nan, lim)
    F["total_loss_flag"] = tl
    F["tow_storage_amount"] = np.round(tow, 2)
    F["_paid_full"] = np.round(paid, 2)
    F["_paid_genuine"] = np.round(paid_g, 2)
    # salvage & subrogation potential
    salv_ok = tl & ~theft_unrec & (cov != "UMPD")
    F["salvage_recovery"] = np.where(salv_ok, np.round(acv * rng.uniform(*sv["salvage_share_of_acv"], len(F)), 0), 0.0)
    naf = C.loss_cause.values[cidx] == "NAF"
    F["subrogation_potential"] = (cov == "COLL") & naf
    F["subrogation_recovery"] = np.where(F.subrogation_potential & (rng.random(len(F)) < sv["subrogation_recovery_prob"]),
                                         np.round((paid + ded) * rng.uniform(0.85, 1.0, len(F)), 2), 0.0)
    F["subrogation_status"] = np.where(F.subrogation_potential, np.where(F.subrogation_recovery > 0, "RECOVERED", "PURSUED_UNCOLLECTIBLE"), "")
    # durations
    rep_day = C.report_datetime.values.astype("datetime64[D]").astype(int)[cidx]
    att = F.attorney_party_id.values != ""
    med = np.select([np.isin(cov, ["COLL", "COMP", "UMPD"]), cov == "PD", np.isin(cov, ["BI", "UMBI"]) & att,
                     np.isin(cov, ["BI", "UMBI"]), cov == "PIP", cov == "MEDPAY"], [18, 26, 390, 120, 170, 85], 20)
    dur = np.round(lognormal(rng, med, 0.55, len(F)) + np.where(tl, 16, 0)).astype(int)
    F["open_date"] = i2d(rep_day)
    F["_close_day"] = rep_day + dur
    F["_rep_day"] = rep_day
    W.t["features"], W.t["estimate_lines"], W.t["medical_bills"] = F, L, B


def add_rental(W):
    rng = W.rng
    F, C = W.table("features"), W.table("claims")
    vt = W.t["vt"]
    cidx = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(F.claim_id).values
    has_rent = vt.rental_coverage.values[C._vt_idx.values[cidx]]
    m = F.coverage.isin(["COLL", "UMPD"]).values & has_rent & (F._paid_full.values > 0) & (rng.random(len(F)) < 0.78)
    base = F[m]
    n = len(base)
    days = np.where(base.total_loss_flag, rng.integers(5, 12, n), np.clip(3 + base.loss_amount.values / 650, 3, 30).astype(int))
    amt = np.minimum(days * rng.uniform(36, 48, n), 1200)
    metro = C._metro.values[cidx[m]]
    from .claims import ClaimFactory
    fac = ClaimFactory(W)
    R_ = pd.DataFrame({"feature_id": W.ids.take("FEA", n, 8) if n else [], "claim_id": base.claim_id.values, "coverage": "RENTAL",
                       "claimant_kind": "INSURED_OWNER", "subtype": "", "claimant_id": base.claimant_id.values,
                       "claimant_role": "INSURED", "repairer_party_id": fac._party("RENTAL", metro) if n else [],
                       "attorney_party_id": "", "loss_amount": np.round(amt, 2), "deductible_applied": 0.0,
                       "limit_applied": 1200.0, "total_loss_flag": False, "tow_storage_amount": 0.0,
                       "_paid_full": np.round(amt, 2),
                       "_paid_genuine": np.where(base._paid_genuine.values > 0, np.round(amt, 2), 0.0),
                       "salvage_recovery": 0.0, "subrogation_potential": False, "subrogation_recovery": 0.0,
                       "subrogation_status": "", "open_date": base.open_date.values, "_close_day": base._close_day.values,
                       "_rep_day": base._rep_day.values, "_target": amt, "rental_days": days,
                       "_fraud_full": base._fraud_full.values, "_genuine_mult": 1.0})
    W.t["features"] = pd.concat([F, R_], ignore_index=True)


def finalize(W):
    """Apply SIU outcomes, leakage, reserves; build payments & recoveries; roll up claims."""
    rng, cfg = W.rng, W.cfg
    asof = d2i(cfg["run"]["as_of_date"])
    C, F = W.table("claims"), W.table("features")
    siu = W.t.get("siu")
    outcome = pd.Series(dtype=object)
    if siu is not None and len(siu):
        outcome = siu.set_index("claim_id").outcome_for_finance
    oc = outcome.reindex(F.claim_id).fillna("").values
    denied = oc == "CONFIRMED_FRAUD"
    paid = np.where(denied, F._paid_genuine.values, F._paid_full.values)
    # leakage flags set by scenarios
    if "_leak_deductible" in F:
        add = F._leak_deductible.fillna(False).values.astype(bool)
        paid = np.where(add, paid + F.deductible_applied.values, paid)
        F.loc[add, "deductible_applied"] = 0.0
    F["siu_savings"] = np.round(np.where(denied, F._paid_full.values - paid, 0.0), 2)
    close = F._close_day.values + np.where(oc != "", rng.integers(45, 140, len(F)), 0)
    is_open = close > asof
    cov = F.coverage.values
    frac = np.clip((asof - F._rep_day.values) / np.maximum(close - F._rep_day.values, 1), 0, 1)
    ptd_frac = np.select([np.isin(cov, ["BI", "UMBI"]), np.isin(cov, ["PIP", "MEDPAY"])],
                         [np.where(frac > 0.9, 1.0, 0.0), frac * 0.9], np.where(frac > 0.4, 1.0, 0.0))
    paid_to_date = np.where(is_open, paid * ptd_frac, paid)
    reserve = np.where(is_open, np.maximum(paid - paid_to_date, 0) * rng.uniform(0.85, 1.25, len(F)), 0.0)
    F["status"] = np.where(is_open, "OPEN", np.where(denied & (paid == 0), "DENIED", np.where(paid > 0, "CLOSED_PAID", "CLOSED_NO_PAY")))
    F["close_date"] = np.where(is_open, np.datetime64("NaT"), i2d(np.minimum(close, asof)))
    F["paid_amount"] = np.round(paid_to_date, 2)
    F["reserve_amount"] = np.round(reserve, 2)
    F["_ultimate_paid"] = np.round(paid, 2)
    # recoveries only once closed + collected
    salv = np.where(F.get("_leak_salvage", pd.Series(False, index=F.index)).fillna(False).values.astype(bool), 0.0, F.salvage_recovery.values)
    F["salvage_recovery"] = np.where(is_open | denied, 0.0, salv)
    subro = np.where(F.get("_leak_subro", pd.Series(False, index=F.index)).fillna(False).values.astype(bool), 0.0, F.subrogation_recovery.values)
    rec_day = close + rng.integers(40, 220, len(F))
    F["subrogation_recovery"] = np.where((rec_day <= asof) & ~denied, np.minimum(subro, paid + F.deductible_applied.values), 0.0)
    if "_leak_subro" in F:
        F.loc[F._leak_subro.fillna(False).astype(bool).values, "subrogation_status"] = "NOT_PURSUED"
    F.loc[(F.subrogation_status == "RECOVERED") & (F.subrogation_recovery == 0), "subrogation_status"] = "IN_PROGRESS"
    F["_rec_day"] = rec_day
    W.t["features"] = F
    build_payments(W)
    build_recoveries(W)
    rollup_claims(W)


def build_payments(W):
    rng = W.rng
    F, C, L, B = W.table("features"), W.table("claims"), W.table("estimate_lines"), W.table("medical_bills")
    P = W.t["parties"].set_index("party_id")
    E = W.t["employees"].set_index("employee_id")
    cidx = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(F.claim_id).values
    rows = []
    pay = F.paid_amount.values
    cov = F.coverage.values
    has = pay > 0
    tow_share = np.where(F.loss_amount.values > 0, F.tow_storage_amount.values / np.maximum(F.loss_amount.values, 1), 0)
    tow_amt = np.round(pay * np.clip(tow_share, 0, 1), 2)
    # tow vendor per feature
    tl_v = L[L.part_name == "Towing"].drop_duplicates("feature_id").set_index("feature_id").vendor_party_id
    tow_vendor = tl_v.reindex(F.feature_id).fillna("").values
    veh = np.isin(cov, ["COLL", "COMP", "UMPD"]) & has
    tow_m = veh & (tow_amt > 0) & (tow_vendor != "")
    rows.append(pd.DataFrame({"fi": np.where(tow_m)[0], "payee_type": "TOW_VENDOR", "payee_id": tow_vendor[tow_m], "amount": tow_amt[tow_m]}))
    main = np.where(tow_m, pay - tow_amt, pay)
    rep = F.repairer_party_id.values
    drp = P.drp_flag.reindex(rep).fillna(False).values.astype(bool)
    glass = F.subtype.values == "GLASS"
    to_shop = veh & ~F.total_loss_flag.values & (rep != "") & (drp | glass | (rng.random(len(F)) < 0.55))
    to_ins = veh & ~to_shop
    rows.append(pd.DataFrame({"fi": np.where(to_shop)[0], "payee_type": np.where(glass[to_shop], "GLASS_VENDOR", "REPAIR_FACILITY"),
                              "payee_id": rep[to_shop], "amount": main[to_shop]}))
    lien = W.t["vehicles"].set_index("vehicle_id").lienholder_flag.reindex(C.vehicle_id.values[cidx]).fillna(False).values
    rows.append(pd.DataFrame({"fi": np.where(to_ins)[0],
                              "payee_type": np.where(F.total_loss_flag.values[to_ins] & lien[to_ins], "INSURED_AND_LIENHOLDER", "INSURED"),
                              "payee_id": C.customer_id.values[cidx[to_ins]], "amount": main[to_ins]}))
    pdm = (cov == "PD") & has
    pd_shop = pdm & (rng.random(len(F)) < 0.6) & (rep != "")
    rows.append(pd.DataFrame({"fi": np.where(pd_shop)[0], "payee_type": "REPAIR_FACILITY", "payee_id": rep[pd_shop], "amount": pay[pd_shop]}))
    pd_cl = pdm & ~pd_shop
    rows.append(pd.DataFrame({"fi": np.where(pd_cl)[0], "payee_type": "CLAIMANT", "payee_id": F.claimant_id.values[pd_cl], "amount": pay[pd_cl]}))
    bi = np.isin(cov, ["BI", "UMBI"]) & has
    att = F.attorney_party_id.values
    rows.append(pd.DataFrame({"fi": np.where(bi)[0], "payee_type": np.where(att[bi] != "", "ATTORNEY_TRUST", "CLAIMANT"),
                              "payee_id": np.where(att[bi] != "", att[bi], F.claimant_id.values[bi]), "amount": pay[bi]}))
    rn = (cov == "RENTAL") & has
    rows.append(pd.DataFrame({"fi": np.where(rn)[0], "payee_type": "RENTAL_AGENCY", "payee_id": rep[rn], "amount": pay[rn]}))
    # PIP / MEDPAY: pay providers pro rata to allowed amounts
    pm = np.isin(cov, ["PIP", "MEDPAY"]) & has
    if pm.any():
        fpos = pd.Series(np.arange(len(F)), index=F.feature_id)
        bb = B[B.feature_id.isin(F.feature_id[pm])].groupby(["feature_id", "provider_party_id"]).allowed_amount.sum().reset_index()
        tot = bb.groupby("feature_id").allowed_amount.transform("sum")
        fi = fpos.reindex(bb.feature_id).values
        rows.append(pd.DataFrame({"fi": fi, "payee_type": "MEDICAL_PROVIDER", "payee_id": bb.provider_party_id.values,
                                  "amount": pay[fi] * bb.allowed_amount.values / np.maximum(tot.values, 1)}))
    Pm = pd.concat(rows, ignore_index=True)
    Pm = Pm[Pm.amount > 0.5].reset_index(drop=True)
    pid = Pm.payee_id.astype(str)
    drv = pid.str.startswith("DRV-").values
    Pm.loc[drv, "payee_type"] = "INSURED_DRIVER"
    Pm["payee_id"] = pid.str.replace(r"^(DRV-|INS-)", "", regex=True).values
    fi = Pm.fi.values
    n = len(Pm)
    Pm["payment_id"] = W.ids.take("PAY", n, 9)
    Pm["claim_id"] = F.claim_id.values[fi]
    Pm["feature_id"] = F.feature_id.values[fi]
    Pm["amount"] = np.round(Pm.amount, 2)
    lo = F._rep_day.values[fi] + 3
    hi = np.minimum(np.where(pd.isna(F.close_date.values[fi]), d2i(W.cfg["run"]["as_of_date"]),
                             pd.to_datetime(F.close_date.values[fi]).values.astype("datetime64[D]").astype(int)), d2i(W.cfg["run"]["as_of_date"]))
    hi = np.maximum(hi, lo + 1)
    Pm["issue_date"] = i2d(np.minimum(lo + (rng.random(n) * (hi - lo)).astype(int), d2i(W.cfg["run"]["as_of_date"])))
    org = Pm.payee_type.isin(["REPAIR_FACILITY", "GLASS_VENDOR", "TOW_VENDOR", "MEDICAL_PROVIDER", "RENTAL_AGENCY", "ATTORNEY_TRUST"]).values
    Pm["payment_method"] = np.where(org & (rng.random(n) < 0.82), "EFT", "CHECK")
    Pm["payee_bank_account_token"] = np.where(Pm.payment_method == "EFT", P.bank_account_token.reindex(Pm.payee_id).fillna("").values, "")
    Pm["payee_name"] = P.name.reindex(Pm.payee_id).values
    Pm["payment_category"] = "INDEMNITY"
    adj = C.adjuster_id.values[pd.Series(np.arange(len(C)), index=C.claim_id).reindex(Pm.claim_id).values]
    Pm["issued_by"] = adj
    auth = E.authority_limit.reindex(adj).fillna(0).values
    mgr = E[E.role == "CLAIMS_MANAGER"].index.values
    over = Pm.amount.values > auth
    Pm["approved_by"] = np.where(over, mgr[rng.integers(0, len(mgr), n)], adj)
    Pm["status"] = np.where(rng.random(n) < 0.004, "VOIDED", "CLEARED")
    W.t["payments"] = Pm.drop(columns=["fi"])


def build_recoveries(W):
    rng = W.rng
    F = W.table("features")
    rows = []
    for col, kind in (("subrogation_recovery", "SUBROGATION"), ("salvage_recovery", "SALVAGE")):
        m = F[col].values > 0
        rows.append(pd.DataFrame({"claim_id": F.claim_id.values[m], "feature_id": F.feature_id.values[m], "recovery_type": kind,
                                  "amount": F[col].values[m], "received_date": i2d(np.minimum(F._rec_day.values[m], d2i(W.cfg["run"]["as_of_date"])))}))
    Rc = pd.concat(rows, ignore_index=True)
    Rc.insert(0, "recovery_id", W.ids.take("REC", len(Rc), 8))
    W.t["recoveries"] = Rc


def rollup_claims(W):
    C, F = W.table("claims"), W.table("features")
    Pm = W.t["payments"]
    g = F.groupby("claim_id")
    paid = Pm[Pm.status != "VOIDED"].groupby("claim_id").amount.sum()
    C["paid_total"] = np.round(paid.reindex(C.claim_id).fillna(0).values, 2)
    C["reserve_total"] = np.round(g.reserve_amount.sum().reindex(C.claim_id).fillna(0).values, 2)
    C["incurred_total"] = np.round(C.paid_total + C.reserve_total, 2)
    C["recovery_total"] = np.round((g.subrogation_recovery.sum() + g.salvage_recovery.sum()).reindex(C.claim_id).fillna(0).values, 2)
    C["net_incurred"] = np.round(C.incurred_total - C.recovery_total, 2)
    any_open = g.status.apply(lambda s: (s == "OPEN").any()).reindex(C.claim_id).values
    all_denied = g.status.apply(lambda s: (s == "DENIED").all()).reindex(C.claim_id).values
    C["claim_status"] = np.where(any_open, "OPEN", np.where(all_denied, "DENIED", "CLOSED"))
    C["closed_date"] = np.where(any_open, np.datetime64("NaT"), g.close_date.max().reindex(C.claim_id).values)
    C["total_loss_flag"] = g.total_loss_flag.any().reindex(C.claim_id).fillna(False).values
    C["attorney_represented"] = g.attorney_party_id.apply(lambda s: (s != "").any()).reindex(C.claim_id).fillna(False).values
    W.t["claims"] = C


# ---------------------------------------------------------------- pricing
BASE_LOSS_COST = {"BI": 176, "PD": 152, "PIP": 125, "MEDPAY": 18, "UM": 48, "COLL": 330, "COMP": 140}
COLL_DED_F = {250: 1.15, 500: 1.0, 1000: 0.84, 2000: 0.70}
COMP_DED_F = {0: 1.35, 250: 1.12, 500: 1.0, 1000: 0.84}
BI_F = {"10/20": 0.70, "15/30": 0.75, "25/50": 0.85, "30/60": 0.88, "50/100": 1.0, "100/300": 1.18, "250/500": 1.36}


def _rating_rel(W, vt, declared=True):
    pr = W.cfg["pricing"]
    hh = W.t["households"]
    h = vt._hh.values
    if declared:
        metro = hh.metro.values[h]; zf = hh._zip_factor.values[h]
    else:
        metro = vt.metro.values; zf = vt.zip_factor.values
    terr = W.geo.territory(metro) * zf
    st = np.array([R.STATES[s][4] for s in vt.state.values])
    from .util import band_lookup
    age = vt.youngest_age.values if declared else vt["_true_youngest_age"].values
    age_f = band_lookup(pr["youngest_driver_factor"], age)
    cr = pd.Series(vt.credit_tier.values).map(pr["credit_factor"]).values
    viol = pr["violation_factor_each"] ** np.minimum(vt.violations.values, 4)
    ve = W.t["vehicles"].set_index("vehicle_id")
    miles = (ve.declared_annual_miles if declared else ve._true_miles).reindex(vt.vehicle_id).values
    use = (ve.declared_usage if declared else ve._true_usage).reindex(vt.vehicle_id).values
    mf = np.where(miles < 7500, pr["miles_factor"]["low"], np.where(miles > 15000, pr["miles_factor"]["high"], 1.0))
    uf = np.where(use == "RIDESHARE", 1.9, np.where(use == "BUSINESS", 1.1, np.where(use == "PLEASURE", 0.93, 1.0)))
    disc = np.where(vt.n_vehicles.values > 1, pr["multi_car_discount"], 1.0) * np.where(vt.homeowner.values, pr["homeowner_discount"], 1.0)
    seg = np.array([R.SEGMENT_REL[s] for s in vt.segment.values])
    return terr * st * age_f * cr * viol * mf * uf * disc, seg


def premium(W):
    cfg = W.cfg
    vt = W.t["vt"]
    T = W.t["terms"]
    base, seg = _rating_rel(W, vt, True)
    true_base, _ = _rating_rel(W, vt, False)
    acv_f = (vt.msrp.values / 32000) ** 0.75
    pip = vt.pip_limit.values > 0
    def comp(b):
        p = {}
        p["BI"] = BASE_LOSS_COST["BI"] * b * pd.Series(vt.bi_limit.values).map(BI_F).fillna(1.0).values
        p["PD"] = BASE_LOSS_COST["PD"] * b
        p["PIP"] = np.where(pip, BASE_LOSS_COST["PIP"] * b * (1 + np.log10(np.maximum(vt.pip_limit.values, 5000) / 10000) * 0.35), 0)
        p["MEDPAY"] = np.where(vt.medpay_limit.values > 0, BASE_LOSS_COST["MEDPAY"] * b, 0)
        p["UM"] = np.where(vt.um_flag.values, BASE_LOSS_COST["UM"] * b, 0)
        p["COLL"] = np.where(np.isnan(vt.coll_deductible.values), 0, BASE_LOSS_COST["COLL"] * b * seg[:, 0] * acv_f *
                             pd.Series(vt.coll_deductible.values).map(COLL_DED_F).fillna(1.0).values)
        p["COMP"] = np.where(np.isnan(vt.comp_deductible.values), 0, BASE_LOSS_COST["COMP"] * (b ** 0.6) * seg[:, 1] * acv_f *
                             pd.Series(vt.comp_deductible.values).map(COMP_DED_F).fillna(1.0).values)
        return p
    p, pt = comp(base), comp(true_base)
    annual = sum(p.values()); annual_true = sum(pt.values())
    earned_frac = vt.exp_years.values
    C = W.table("claims")
    losses = C.net_incurred.sum()
    s = losses / (cfg["pricing"]["target_loss_ratio"] * (annual * earned_frac).sum())
    minp = cfg["pricing"]["min_premium_per_vehicle"]
    for k in p:
        vt[f"premium_{k.lower()}"] = np.round(p[k] * s, 2)
    vt["vehicle_premium"] = np.round(np.maximum(annual * s, minp), 2)
    vt["_vehicle_premium_true"] = np.round(np.maximum(annual_true * s, minp), 2)
    vt["earned_premium"] = np.round(vt.vehicle_premium * earned_frac, 2)
    vt["_earned_premium_true"] = np.round(vt._vehicle_premium_true * earned_frac, 2)
    g = vt.groupby("term_id")
    T["written_premium"] = np.round(g.vehicle_premium.sum().reindex(T.term_id).fillna(0).values, 2)
    T["earned_premium"] = np.round(g.earned_premium.sum().reindex(T.term_id).fillna(0).values, 2)
    T["_earned_premium_true"] = np.round(g._earned_premium_true.sum().reindex(T.term_id).fillna(0).values, 2)
    rate = pd.Series(T.channel.values).map(cfg["book"]["commission_rate"]).fillna(0).values
    T["commission_amount"] = np.round(T.written_premium * rate, 2)
    T["n_vehicles"] = g.vehicle_id.count().reindex(T.term_id).fillna(0).astype(int).values
    W.t["terms"], W.t["vt"] = T, vt
    W.premium_scale = s
