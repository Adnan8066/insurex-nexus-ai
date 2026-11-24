"""Validation + story report computed from the generated tables (never from config),
so every number in STORY.md can be reproduced with a query against the data."""
import os
import numpy as np
import pandas as pd

BENCH = {  # Verisk 2024 Personal Auto Executive Insights (Q2'23-Q1'24): frequency per insured vehicle-year, severity
    "BI": (0.007, 25118), "PD": (0.026, 5844), "PIP": (0.013, 8867), "COLL": (0.045, 7155), "COMP": (0.064, 2191)}


def _m(x):
    x = float(x)
    if abs(x) >= 1e6:
        return f"${x/1e6:,.1f}M"
    if abs(x) >= 1e3:
        return f"${x/1e3:,.0f}K"
    return f"${x:,.0f}"


def compute(W, out, truth_claims):
    C, F, T, vt = out["claims"], out["claim_features"], out["policy_terms"], W.t["vt"]
    Pm = out["payments"]
    r = {}
    r["customers"] = W.t["households"].shape[0]
    r["policy_terms"] = len(T); r["vehicles"] = len(out["vehicles"]); r["vehicle_years"] = vt.exp_years.sum()
    r["drivers"] = len(out["drivers"]); r["claims"] = len(C); r["features"] = len(F)
    r["written_premium"] = T.written_premium.sum(); r["earned_premium"] = T.earned_premium.sum()
    paid = Pm[Pm.status != "VOIDED"].amount.sum()
    r["paid"] = paid
    r["incurred"] = C.incurred_total.sum(); r["net_incurred"] = C.net_incurred.sum()
    r["loss_ratio"] = r["net_incurred"] / r["earned_premium"]
    fc = vt[~vt.coll_deductible.isna()]
    r["avg_premium_full"] = fc.vehicle_premium.mean()
    r["avg_premium_liab"] = vt[vt.coll_deductible.isna() & vt.comp_deductible.isna()].vehicle_premium.mean()
    # frequency & severity per coverage
    rows = []
    for cov, (bf, bs) in BENCH.items():
        if cov in ("COLL",):
            expo = vt.exp_years[~vt.coll_deductible.isna()].sum()
        elif cov == "COMP":
            expo = vt.exp_years[~vt.comp_deductible.isna()].sum()
        elif cov == "PIP":
            expo = vt.exp_years[vt.pip_limit > 0].sum()
        else:
            expo = vt.exp_years.sum()
        f = F[(F.coverage == cov)]
        fpaid = f[(f.status == "CLOSED_PAID")]
        sev = (fpaid.paid_amount + fpaid.deductible_applied).mean()
        rows.append({"coverage": cov, "features": len(f), "frequency_per_100": 100 * len(f) / expo, "benchmark_freq_per_100": 100 * bf,
                     "avg_paid_severity": sev, "benchmark_severity": bs})
    r["freq_sev"] = pd.DataFrame(rows)
    # anomaly distribution
    tc = truth_claims
    r["share_claim_fraud"] = tc.is_claim_fraud.mean(); r["share_policy_fraud"] = tc.is_policy_fraud.mean()
    r["share_leakage"] = tc.is_leakage.mean(); r["share_benign"] = tc.is_benign_lookalike.mean(); r["share_clean"] = tc.is_clean.mean()
    r["fraud_excess"] = tc.fraud_excess_paid.sum(); r["leakage"] = tc.get("leakage_amount", pd.Series(0)).sum()
    r["internal"] = tc.get("internal_diversion_amount", pd.Series(0)).sum()
    r["siu_savings"] = tc.siu_savings.sum()
    Tt = W.t["terms"]
    misrep_terms = Tt[Tt._earned_premium_true > Tt.earned_premium + 1]
    r["premium_leakage"] = (misrep_terms._earned_premium_true - misrep_terms.earned_premium).sum()
    gh = Tt[Tt._ghost]
    r["ghost_commission"] = gh.commission_amount.sum()
    # SIU and naive rules
    s = out["siu_investigations"]
    fl = W.t["naive_flags"]
    m = fl.merge(tc[["claim_id", "is_claim_fraud"]], on="claim_id")
    flagged = m.rf_count > 0
    r["rules_flag_share"] = flagged.mean()
    r["rules_precision"] = m.is_claim_fraud[flagged].mean()
    r["rules_recall"] = flagged[m.is_claim_fraud].mean()
    s2 = s.merge(tc[["claim_id", "is_claim_fraud", "fraud_excess_paid"]], on="claim_id", how="left")
    r["siu_referred"] = len(s); r["siu_referred_share"] = len(s) / len(C)
    r["siu_confirmed"] = (s.outcome == "CONFIRMED_FRAUD").sum()
    r["siu_hit_rate"] = s2.is_claim_fraud.mean()
    fraud_claims = tc[tc.is_claim_fraud]
    r["fraud_claims"] = len(fraud_claims)
    r["fraud_claims_referred"] = fraud_claims.claim_id.isin(s.claim_id).mean()
    # scenario table
    TI = pd.concat(W.truth, ignore_index=True)
    ex = tc.assign(sc=tc.scenarios.str.split(";")).explode("sc")
    ex = ex[ex.sc != ""]
    claims_by = ex.groupby("sc").claim_id.nunique()
    # attribute each feature's fraud excess to the scenarios that touched it (split evenly on overlap)
    Fx = W.table("features")[["feature_id", "claim_id"]].copy()
    Fx["x"] = W.feature_excess.reindex(Fx.feature_id).fillna(0).values
    fr = TI[(TI.layer == "FRAUD") & TI.entity_type.isin(["FEATURE", "CLAIM"]) & ~TI.family.isin(["PRODUCER_FRAUD", "RATING_MISREP"])]
    a1 = fr[fr.entity_type == "FEATURE"][["scenario", "entity_id"]].rename(columns={"entity_id": "feature_id"})
    a2 = fr[fr.entity_type == "CLAIM"][["scenario", "entity_id"]].rename(columns={"entity_id": "claim_id"}).merge(Fx[["feature_id", "claim_id"]], on="claim_id")[["scenario", "feature_id"]]
    att = pd.concat([a1, a2]).drop_duplicates()
    att["w"] = 1.0 / att.groupby("feature_id").scenario.transform("count")
    att = att.merge(Fx[["feature_id", "x"]], on="feature_id")
    fraud_by = (att.w * att.x).groupby(att.scenario).sum()
    cfgsc = W.cfg["scenarios"]
    srows = []
    for name, sc in cfgsc.items():
        if not sc.get("enabled", True):
            continue
        ti = TI[TI.scenario == name]
        unit_ent = {"feature": ["FEATURE"], "claim": ["CLAIM"], "policy": ["POLICY"], "vehicle": ["VEHICLE"], "payment": ["PAYMENT"],
                    "ring": ["CLAIM", "FEATURE", "POLICY", "PAYMENT"], "event": ["CLAIM"]}[sc["unit"]]
        prim = ti[ti.entity_type.isin(unit_ent) & ~ti.role.isin(["recruited_policy", "producer"])]
        srows.append({"scenario": name, "layer": sc["layer"], "family": sc["family"], "unit": sc["unit"],
                      "target_prevalence": sc.get("prevalence", ""), "instances": len(prim),
                      "entity_types": ",".join(sorted(prim.entity_type.unique())),
                      "claims_touched": int(claims_by.get(name, 0)), "share_of_claims": claims_by.get(name, 0) / len(C),
                      "fraud_excess": float(fraud_by.get(name, 0.0)),
                      "excess_amount_logged": float(ti.excess_amount.sum()) if "excess_amount" in ti else 0.0})
    r["scenarios"] = pd.DataFrame(srows)
    # storylines
    st = []
    for rid, meta in W.storylines.items():
        cl = tc[tc.ring_ids.str.contains(rid, regex=False)]
        if not len(cl) and meta["scenario"] not in ("PRODUCER_GARAGING_EVASION", "PRODUCER_GHOST_POLICIES", "INTERNAL_ADJUSTER_DIVERSION"):
            continue
        cc = C[C.claim_id.isin(cl.claim_id)]
        st.append({"ring_id": rid, "title": meta["title"], "scenario": meta["scenario"], "claims": len(cl),
                   "paid": cc.incurred_total.sum(), "fraud_excess": cl.fraud_excess_paid.sum(),
                   "internal_diversion": cl.get("internal_diversion_amount", pd.Series(0)).sum(),
                   "first_loss": cc.loss_datetime.min(), "last_loss": cc.loss_datetime.max(),
                   "siu_referred_share": cl.claim_id.isin(s.claim_id).mean() if len(cl) else np.nan})
    r["storylines"] = pd.DataFrame(st)
    # producer view for the garaging story
    gp = W.storylines.get("GAR-ALLENTOWN", {}).get("producers", [])
    if gp:
        Tt2 = Tt.copy()
        ci = C.groupby("term_id").net_incurred.sum()
        Tt2["loss"] = ci.reindex(Tt2.term_id).fillna(0).values
        g = Tt2.groupby(Tt2.producer_id.isin(gp))
        r["garaging_lr"] = (g.loss.sum() / g.earned_premium.sum()).to_dict()
        r["garaging_terms"] = int(Tt2.producer_id.isin(gp).sum())
    gh = W.storylines.get("GHOST-ATL", {}).get("producers", [])
    if gh:
        a = Tt[Tt.producer_id.isin(gh)]
        b = Tt[(Tt.channel == "CAPTIVE_AGENT") & ~Tt.producer_id.isin(gh) & Tt.new_business_flag]
        r["ghost_cancel60"] = ((a.cancel_date > 0) & (a.cancel_date - a.term_start <= 60) & a.new_business_flag).sum() / max(a.new_business_flag.sum(), 1)
        r["peer_cancel60"] = ((b.cancel_date > 0) & (b.cancel_date - b.term_start <= 60)).mean()
    return r


def write(W, r, folder):
    os.makedirs(folder, exist_ok=True)
    r["scenarios"].to_csv(os.path.join(folder, "ground_truth", "scenario_distribution.csv"), index=False)
    r["storylines"].to_csv(os.path.join(folder, "ground_truth", "storyline_summary.csv"), index=False)
    fs = r["freq_sev"].copy()
    lines = ["# Validation report", "",
             f"Seed {W.cfg['run']['seed']} · window {W.cfg['run']['window_start']} → {W.cfg['run']['window_end']} · as-of {W.cfg['run']['as_of_date']}", "",
             "## Book", "",
             f"| Metric | Value |", "|---|---|",
             f"| Customers (households) | {r['customers']:,} |", f"| Policy terms | {r['policy_terms']:,} |",
             f"| Vehicles | {r['vehicles']:,} |", f"| Earned vehicle-years | {r['vehicle_years']:,.0f} |",
             f"| Listed drivers | {r['drivers']:,} |", f"| Claims | {r['claims']:,} |", f"| Claim features | {r['features']:,} |",
             f"| Written premium | {_m(r['written_premium'])} |", f"| Earned premium | {_m(r['earned_premium'])} |",
             f"| Net incurred | {_m(r['net_incurred'])} |", f"| Loss ratio (net incurred / earned) | {r['loss_ratio']:.1%} |",
             f"| Avg annual premium, full coverage vehicle | ${r['avg_premium_full']:,.0f} |",
             f"| Avg annual premium, liability-only vehicle | ${r['avg_premium_liab']:,.0f} |", "",
             "## Frequency and severity vs industry benchmark", "",
             "Benchmark: Verisk 2024 Personal Auto Executive Insights (Q2 2023–Q1 2024). Severity here = paid + deductible on closed paid features.", "",
             "| Coverage | Features | Freq /100 veh-yr | Benchmark | Avg severity | Benchmark |", "|---|---|---|---|---|---|"]
    for _, x in fs.iterrows():
        lines.append(f"| {x.coverage} | {x.features:,} | {x.frequency_per_100:.2f} | {x.benchmark_freq_per_100:.2f} | ${x.avg_paid_severity:,.0f} | ${x.benchmark_severity:,.0f} |")
    lines += ["", "## Claim mix by truth layer", "",
              f"| Layer | Share of claims |", "|---|---|",
              f"| Clean genuine | {r['share_clean']:.1%} |", f"| Claim fraud (soft, hard, ring, internal) | {r['share_claim_fraud']:.1%} |",
              f"| On a misrepresented or fraudulently written policy (rating/producer fraud) | {r['share_policy_fraud']:.1%} |",
              f"| Leakage | {r['share_leakage']:.1%} |", f"| Benign look-alike (cat, trend, late report) | {r['share_benign']:.1%} |", "",
              "## Scenario distribution", "", "| Scenario | Layer | Instances | Claims touched | % claims | Fraud excess | Leakage / diverted |",
              "|---|---|---|---|---|---|---|"]
    for _, x in r["scenarios"].iterrows():
        lines.append(f"| {x.scenario} | {x.layer} | {x.instances:,} | {x.claims_touched:,} | {x.share_of_claims:.2%} | {_m(x.fraud_excess)} | {_m(x.excess_amount_logged)} |")
    open(os.path.join(folder, "VALIDATION.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def story(W, r, folder):
    co = W.cfg["company"]["name"]
    tot_loss = r["paid"]
    fraud_pct = r["fraud_excess"] / tot_loss
    leak_total = r["leakage"] + r["internal"]
    st = r["storylines"]
    st = st[st.claims > 0].assign(_k=st.fraud_excess + st.internal_diversion).sort_values("_k", ascending=False)
    lines = [f"# {co}: the story in the data", "",
             f"*Synthetic dataset. {r['policy_terms']:,} policy terms, {r['claims']:,} claims, "
             f"{W.cfg['run']['window_start'][:4]}–{W.cfg['run']['window_end'][:4]}, valued {W.cfg['run']['as_of_date']}. Every figure below is computed from the tables.*", "",
             "## 1. A healthy-looking book", "",
             f"{co} earned {_m(r['earned_premium'])} and booked {_m(r['net_incurred'])} of net incurred losses: a {r['loss_ratio']:.0%} loss ratio. "
             f"Average full-coverage premium is ${r['avg_premium_full']:,.0f} per vehicle and claim frequency and severity sit on top of industry benchmarks (see VALIDATION.md). "
             "Nothing on the surface says anything is wrong.", "",
             "## 2. What is underneath", "",
             f"- **{r['share_claim_fraud']:.1%} of claims** carry claim fraud, from padded estimates to organized rings.",
             f"- That fraud added **{_m(r['fraud_excess'])} of excess incurred losses**, {r['fraud_excess'] / r['incurred']:.1%} of all incurred losses.",
             f"- Claims-handling leakage and an inside job added **{_m(leak_total)}** more: missed subrogation, unrecovered salvage, unapplied deductibles, duplicate checks and payments to a shell vendor.",
             f"- Rating misrepresentation left **{_m(r['premium_leakage'])} of premium uncollected**: garaging fraud, undisclosed drivers and undisclosed rideshare use.",
             f"- A ghost-policy producer collected **{_m(r['ghost_commission'])} in commission** on policies that never paid.", "",
             "## 3. Today's defences miss most of it", "",
             f"- The red-flag rules flag **{r['rules_flag_share']:.0%} of all claims**, but only **{r['rules_precision']:.0%}** of the flagged claims are fraud (rules recall {r['rules_recall']:.0%}).",
             f"- The SIU has capacity to investigate **{r['siu_referred_share']:.1%} of claims**. Only {r['fraud_claims_referred']:.0%} of fraud claims are ever referred.",
             f"- SIU saved {_m(r['siu_savings'])}, roughly {r['siu_savings'] / max(r['fraud_excess'] + r['siu_savings'], 1):.0%} of the fraud dollars presented.",
             "- Benign events look like fraud to the rules: hail and flood catastrophes, the Kia/Hyundai theft wave, winter pileups that share one police report, and hospitalized claimants who report late.", "",
             "## 4. The storylines", "", "| Storyline | Claims | Incurred on those claims | Fraud excess / diverted | Active | SIU referral rate |", "|---|---|---|---|---|---|"]
    for _, x in st.iterrows():
        act = "" if pd.isna(x.first_loss) else f"{pd.Timestamp(x.first_loss):%b %Y} – {pd.Timestamp(x.last_loss):%b %Y}"
        rr = "" if pd.isna(x.siu_referred_share) else f"{x.siu_referred_share:.0%}"
        lines.append(f"| {x.title} | {x.claims:,} | {_m(x.paid)} | {_m(x.fraud_excess + x.internal_diversion)} | {act} | {rr} |")
    if "garaging_lr" in r:
        lr = r["garaging_lr"]
        lines += ["", f"**Allentown agencies:** loss ratio {lr.get(True, 0):.0%} on {r['garaging_terms']:,} terms versus {lr.get(False, 0):.0%} for the rest of the book. "
                  "Their customers crash in Brooklyn, carry New York phones and licences, and share a handful of garaging addresses."]
    if "ghost_cancel60" in r:
        lines += ["", f"**Atlanta ghost book:** {r['ghost_cancel60']:.0%} of this agent's new business cancels for non-payment within 60 days, versus {r['peer_cancel60']:.1%} for peer captive agents. Commission is never charged back."]
    lines += ["", "Catastrophe rows are genuine events; the small fraud excess inside them is opportunistic prior damage riding on the storm, which is itself part of the story."]
    lines += ["", "## 5. The pitch", "",
              "Each scheme is visible only when you join data that today sits in separate systems:",
              "- claims to policies, for early claims, rating mismatches and odometer readings against declared mileage;",
              "- parties to people, for shared phones, addresses and bank accounts;",
              "- estimate lines and medical bills, for padding and treatment mills;",
              "- payments to employees, for authority-limit gaming and shell vendors.", "",
              "A graph plus anomaly-model layer replaces red-flag rules with ring-level detection. Its value comes from recovering a slice of the "
              f"{_m(r['fraud_excess'] + leak_total + r['premium_leakage'])} identified above, while referring fewer false positives to a capacity-constrained SIU.", "",
              "Ground truth for every claim, policy, party and payment is in `ground_truth/`, so the uplift of any model built on the observable tables can be measured exactly."]
    open(os.path.join(folder, "STORY.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
