"""Ground-truth roll-up to claims, naive red-flag rules, and a capacity-constrained SIU.

The observable SIU outcome is *not* the truth: SIU only sees what it refers, refers on
visible signals, misses most quiet fraud, and occasionally confirms a genuine claim."""
import numpy as np
import pandas as pd
from .util import d2i, i2d

PRIORITY = ["ORGANIZED_RING", "INTERNAL_FRAUD", "HARD_FRAUD", "PRODUCER_FRAUD", "SOFT_FRAUD", "RATING_MISREP",
            "CLAIMS_LEAKAGE", "CATASTROPHE", "TREND", "LOOKALIKE"]


def claim_truth_long(W, with_payments=True):
    T = pd.concat(W.truth, ignore_index=True)
    C, F = W.table("claims"), W.table("features")
    out = []
    t = T[T.entity_type == "CLAIM"]
    out.append(pd.DataFrame({"claim_id": t.entity_id.values, "via": "CLAIM", **{k: t[k].values for k in ("scenario", "layer", "family", "ring_id", "signals")}}))
    t = T[T.entity_type == "FEATURE"]
    f2c = F.set_index("feature_id").claim_id
    out.append(pd.DataFrame({"claim_id": f2c.reindex(t.entity_id).values, "via": "FEATURE", **{k: t[k].values for k in ("scenario", "layer", "family", "ring_id", "signals")}}))
    if with_payments and "payments" in W.t and isinstance(W.t["payments"], pd.DataFrame):
        t = T[T.entity_type == "PAYMENT"]
        p2c = W.t["payments"].set_index("payment_id").claim_id
        out.append(pd.DataFrame({"claim_id": p2c.reindex(t.entity_id).values, "via": "PAYMENT", **{k: t[k].values for k in ("scenario", "layer", "family", "ring_id", "signals")}}))
    # policy / vehicle level misrepresentation reaches the claims it touches
    t = T[(T.entity_type == "POLICY") & T.scenario.isin(["SOFT_UNLISTED_DRIVER", "PRODUCER_GARAGING_EVASION"])]
    if len(t):
        cc = C[["claim_id", "customer_id", "operator_listed", "loss_cause"]].merge(
            t[["entity_id", "scenario", "layer", "family", "ring_id", "signals"]], left_on="customer_id", right_on="entity_id")
        cc = cc[(cc.scenario != "SOFT_UNLISTED_DRIVER") | (~cc.operator_listed)]
        out.append(pd.DataFrame({"claim_id": cc.claim_id.values, "via": "POLICY", **{k: cc[k].values for k in ("scenario", "layer", "family", "ring_id", "signals")}}))
    t = T[(T.entity_type == "VEHICLE") & (T.scenario == "SOFT_RIDESHARE_UNDISCLOSED")]
    if len(t):
        cc = C[["claim_id", "vehicle_id", "loss_cause"]].merge(t[["entity_id", "scenario", "layer", "family", "ring_id", "signals"]],
                                                              left_on="vehicle_id", right_on="entity_id")
        cc = cc[cc.loss_cause.isin(["AF_MULTI", "AF_SINGLE", "NAF", "NAF_UNINSURED"])]
        out.append(pd.DataFrame({"claim_id": cc.claim_id.values, "via": "VEHICLE", **{k: cc[k].values for k in ("scenario", "layer", "family", "ring_id", "signals")}}))
    L = pd.concat(out, ignore_index=True).dropna(subset=["claim_id"])
    L["n_signals"] = L.signals.fillna("").map(lambda s: 0 if not s else s.count(";") + 1)
    return L


def naive_flags(W):
    """Classic red-flag rules an insurer might already run. Used for SIU referral and for the story
    (how many claims the rules flag vs how many are really fraud)."""
    C, F, T = W.table("claims"), W.table("features"), W.t["terms"]
    tpos = pd.Series(np.arange(len(T)), index=T.term_id).reindex(C.term_id).values
    ld = C.loss_datetime.values.astype("datetime64[D]").astype(int)
    rd = C.report_datetime.values.astype("datetime64[m]")
    lag = (rd - C.loss_datetime.values.astype("datetime64[m]")).astype(int) / 1440
    hour = pd.to_datetime(C.loss_datetime).dt.hour.values
    g = F.groupby("claim_id")
    tgt = g._target.sum().reindex(C.claim_id).fillna(0).values
    ninj = g.coverage.apply(lambda s: s.isin(["BI", "PIP", "MEDPAY", "UMBI"]).sum()).reindex(C.claim_id).fillna(0).values
    att = g.attorney_party_id.apply(lambda s: (s != "").any()).reindex(C.claim_id).fillna(False).values
    fl = pd.DataFrame({"claim_id": C.claim_id.values,
                       "rf_early_claim": (ld - T.term_start.values[tpos] <= 30) & T.new_business_flag.values[tpos],
                       "rf_late_report": lag > 7,
                       "rf_attorney": att,
                       "rf_night_single_vehicle": (C.loss_cause.values == "AF_SINGLE") & (hour <= 4),
                       "rf_theft_or_fire": np.isin(C.loss_cause.values, ["THEFT", "FIRE"]),
                       "rf_high_severity": tgt > 25000,
                       "rf_multi_injury": ninj >= 3,
                       })
    fl["rf_count"] = fl.filter(like="rf_").sum(axis=1)
    return fl


def run(W):
    rng, cfg = W.rng, W.cfg
    s = cfg["siu"]
    C = W.table("claims")
    L = claim_truth_long(W, with_payments=False)
    fraud = L[(L.layer == "FRAUD") & ~L.family.isin(["PRODUCER_FRAUD", "RATING_MISREP"])]
    sig = fraud.groupby("claim_id").n_signals.sum()
    ring = fraud[fraud.family == "ORGANIZED_RING"].claim_id.unique()
    fl = naive_flags(W)
    is_fraud = C.claim_id.isin(sig.index).values
    score = np.where(is_fraud, 0.55 * sig.reindex(C.claim_id).fillna(0).values + np.isin(C.claim_id, ring) * 0.8, 0) + 0.45 * fl.rf_count.values
    p = np.clip(s["base_referral_genuine"] + s["referral_weight_per_signal"] * score * 0.35, 0, 0.92)
    ref = rng.random(len(C)) < p
    cap = int(s["capacity_share_of_claims"] * len(C))
    if ref.sum() > cap:
        idx = np.where(ref)[0]
        keep = idx[np.argsort(-(score[idx] + rng.normal(0, 0.8, len(idx))))[:cap]]
        ref = np.zeros(len(C), bool); ref[keep] = True
    n = ref.sum()
    fr = is_fraud[ref]
    u = rng.random(n)
    outcome = np.where(fr, np.where(u < s["confirm_prob_if_fraud"], "CONFIRMED_FRAUD",
                                    np.where(u < s["confirm_prob_if_fraud"] + s["inconclusive_prob_if_fraud"], "INCONCLUSIVE", "CLEARED")),
                       np.where(u < s["false_confirm_prob_if_genuine"], "CONFIRMED_FRAUD", np.where(u < 0.12, "INCONCLUSIVE", "CLEARED")))
    rep = C.report_datetime.values[ref].astype("datetime64[D]").astype(int)
    rdate = rep + rng.integers(1, 25, n)
    cdate = rdate + rng.integers(25, 160, n)
    asof = d2i(cfg["run"]["as_of_date"])
    E = W.t["employees"]
    inv = E[E.role == "SIU_INVESTIGATOR"].employee_id.values
    src = np.where(fl.rf_count.values[ref] > 0, np.where(rng.random(n) < 0.6, "RULES_ENGINE", "ADJUSTER_REFERRAL"),
                   np.where(rng.random(n) < 0.7, "ADJUSTER_REFERRAL", "ANONYMOUS_TIP"))
    S = pd.DataFrame({"investigation_id": W.ids.take("SIU", n, 7), "claim_id": C.claim_id.values[ref],
                      "referral_date": i2d(np.minimum(rdate, asof)), "referral_source": src,
                      "investigator_id": inv[rng.integers(0, len(inv), n)],
                      "outcome": np.where(cdate > asof, "OPEN", outcome), "closed_date": np.where(cdate > asof, np.datetime64("NaT"), i2d(cdate)),
                      "_final_outcome": outcome})
    # open investigations still hold payment if the eventual finding is fraud
    S["outcome"] = np.where((S.outcome == "OPEN") & (S._final_outcome == "CONFIRMED_FRAUD"), "OPEN", S.outcome)
    W.t["siu"] = S
    W.t["naive_flags"] = fl
    # finance only denies on a confirmed finding; open-with-fraud is withheld too
    W.t["siu"]["outcome_for_finance"] = np.where(S._final_outcome == "CONFIRMED_FRAUD", "CONFIRMED_FRAUD", S._final_outcome)


def claim_truth_wide(W):
    C, F = W.table("claims"), W.table("features")
    L = claim_truth_long(W, with_payments=True)
    L["prio"] = L.family.map({k: i for i, k in enumerate(PRIORITY)}).fillna(99)
    L = L.sort_values(["claim_id", "prio"])
    g = L.groupby("claim_id")
    first = g.first()
    agg = pd.DataFrame({
        "scenarios": g.scenario.apply(lambda s: ";".join(dict.fromkeys(s))),
        "families": g.family.apply(lambda s: ";".join(dict.fromkeys(s))),
        "ring_ids": g.ring_id.apply(lambda s: ";".join(x for x in dict.fromkeys(s) if x)),
        "n_signals": g.n_signals.sum(),
    })
    agg["primary_scenario"] = first.scenario
    agg["primary_family"] = first.family
    agg["primary_layer"] = first.layer
    claim_fraud = L[(L.layer == "FRAUD") & ~L.family.isin(["PRODUCER_FRAUD", "RATING_MISREP"])].claim_id.unique()
    policy_fraud = L[L.family.isin(["PRODUCER_FRAUD", "RATING_MISREP"])].claim_id.unique()
    leak = L[L.layer == "LEAKAGE"].claim_id.unique()
    benign = L[L.layer == "BENIGN"].claim_id.unique()
    W_ = pd.DataFrame({"claim_id": C.claim_id.values})
    W_ = W_.merge(agg, left_on="claim_id", right_index=True, how="left")
    W_["is_claim_fraud"] = W_.claim_id.isin(claim_fraud)
    W_["is_policy_fraud"] = W_.claim_id.isin(policy_fraud)
    W_["is_leakage"] = W_.claim_id.isin(leak)
    W_["is_benign_lookalike"] = W_.claim_id.isin(benign)
    W_["is_clean"] = ~(W_.is_claim_fraud | W_.is_policy_fraud | W_.is_leakage | W_.is_benign_lookalike)
    for c in ("scenarios", "families", "ring_ids", "primary_scenario", "primary_family", "primary_layer"):
        W_[c] = W_[c].fillna("")
    W_["n_signals"] = W_.n_signals.fillna(0).astype(int)
    # dollars
    # excess on an incurred basis: share of each feature's ultimate that is not genuine, applied to paid + reserve
    ult = F._ultimate_paid.values
    frac = np.where(ult > 0, np.clip((ult - np.minimum(F._paid_genuine.values, ult)) / np.maximum(ult, 1e-9), 0, 1), 0)
    fx = pd.Series(frac * (F.paid_amount.values + F.reserve_amount.values), index=F.index).where(F.claim_id.isin(claim_fraud), 0)
    W.feature_excess = pd.Series(fx.values, index=F.feature_id.values)
    W_["fraud_excess_paid"] = fx.groupby(F.claim_id).sum().reindex(W_.claim_id).fillna(0).round(2).values
    sav = F.siu_savings.groupby(F.claim_id).sum()
    W_["siu_savings"] = sav.reindex(W_.claim_id).fillna(0).round(2).values
    T = pd.concat(W.truth, ignore_index=True)
    if "excess_amount" in T:
        le = T[T.layer == "LEAKAGE"].dropna(subset=["excess_amount"])
        le_c = pd.concat([F.set_index("feature_id").claim_id.reindex(le[le.entity_type == "FEATURE"].entity_id).rename("claim_id").reset_index(drop=True)
                          .to_frame().assign(x=le[le.entity_type == "FEATURE"].excess_amount.values),
                          W.t["payments"].set_index("payment_id").claim_id.reindex(le[le.entity_type == "PAYMENT"].entity_id).rename("claim_id").reset_index(drop=True)
                          .to_frame().assign(x=le[le.entity_type == "PAYMENT"].excess_amount.values)])
        W_["leakage_amount"] = le_c.groupby("claim_id").x.sum().reindex(W_.claim_id).fillna(0).round(2).values
        it = T[(T.scenario == "INTERNAL_ADJUSTER_DIVERSION") & (T.entity_type == "PAYMENT")]
        ic = W.t["payments"].set_index("payment_id").claim_id.reindex(it.entity_id).values
        W_["internal_diversion_amount"] = pd.Series(it.excess_amount.values, index=ic).groupby(level=0).sum().reindex(W_.claim_id).fillna(0).round(2).values
    return W_
