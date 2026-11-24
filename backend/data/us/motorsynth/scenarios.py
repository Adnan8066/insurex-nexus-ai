"""Scenario injectors.

An anomaly here is a *category*, not a rule. Each instance draws its own subset of the
scenario's fingerprints (W.signals), its own intensity, and its own place and time inside
the scenario's window, so instances resemble each other the way real cases do: by family
resemblance, never by a single field that gives them away.

Phases:
  pre_terms   - misrepresentation that changes what the policy *says* (garaging, ghosts, set-ups)
  pre_claims  - hidden truths that change risk (unlisted drivers, rideshare use)
  add_claims  - claims that exist only because of the scenario (rings, staged, cats ...)
  mutate      - genuine claims that get inflated (padding, buildup, steering ...)
  post_settle - leakage in claim handling
  post_pay    - payment-level fraud and leakage
"""
import numpy as np
import pandas as pd
from . import refdata as R
from .util import d2i, i2d, pick, break_vin, make_vins, token, lognormal


def _on(W, name):
    s = W.cfg["scenarios"].get(name)
    return s is not None and s.get("enabled", True)


def _sc(W, name):
    return W.cfg["scenarios"][name]


def _n(W, x):
    """Scale absolute instance counts with the book size (config numbers are for 1M terms)."""
    return max(3, int(round(x * W.cfg["run"]["target_policy_terms"] / 1_000_000)))


def _sigstr(df):
    cols = list(df.columns)
    return np.array([";".join(c for c, v in zip(cols, r) if v) for r in df.values], dtype=object)


def new_parties(W, kind, metro, n, ring, **attrs):
    rng = W.rng
    st, city = R.METROS[metro][0], R.METROS[metro][1]
    names = [W.biz.make(kind, city) for _ in range(n)]
    z, _ = W.geo.sample_zip([metro] * n)
    df = pd.DataFrame({"party_id": W.ids.take("PTY", n, 6), "party_type": kind, "name": names, "metro": metro,
                       "state": st, "city": city, "address": W.geo.street(n), "zip": z, "phone": W.geo.phone([metro] * n),
                       "tax_id": [f"{a:02d}-{b:07d}" for a, b in zip(rng.integers(10, 99, n), rng.integers(0, 9999999, n))],
                       "bank_account_token": token(rng, "BA", n, 10), "drp_flag": False,
                       "labor_rate": np.nan, "established_date": pd.to_datetime("2019-01-01") + pd.to_timedelta(rng.integers(0, 1500, n), "D"),
                       "_volume": 1.0, "_ring": ring})
    for k, v in attrs.items():
        df[k] = v
    W.t["parties"] = pd.concat([W.t["parties"], df], ignore_index=True)
    return df.party_id.values


def ring_people(W, n, metro, n_phones, n_addr, ring, scenario):
    rng = W.rng
    g = np.where(rng.random(n) < 0.55, "M", "F")
    by = rng.integers(1965, 2004, n)
    f, m, l, s = W.names.people(g, by)
    phones = W.geo.phone([metro] * n_phones)
    addr = W.geo.street(n_addr)
    z, _ = W.geo.sample_zip([metro] * n_addr)
    pi = rng.integers(0, n_phones, n); ai = rng.integers(0, n_addr, n)
    df = pd.DataFrame({"claimant_id": W.ids.take("CLT", n, 8), "first_name": f, "middle_name": m, "last_name": l, "gender": g,
                       "date_of_birth": pd.to_datetime(by.astype(str)) + pd.to_timedelta(rng.integers(0, 365, n), "D"),
                       "phone": phones[pi], "address": addr[ai], "zip": z[ai],
                       "city": R.METROS[metro][1], "state": R.METROS[metro][0]})
    W.append("persons", df)
    W.truth_add_raw(scenario, "PERSON", df.claimant_id.values, ring, role="ring_member")
    return df.claimant_id.values


def window_days(W, sc, n):
    w = sc.get("window") or [W.cfg["run"]["window_start"], W.cfg["run"]["as_of_date"]]
    a, b = d2i(w[0]), d2i(w[1])
    return W.rng.integers(a, b, n)


def sample_active(W, cand, days, tries=60):
    """For each day, pick a vt row from `cand` whose exposure covers that day (-1 if none)."""
    rng = W.rng
    vt = W.t["vt"]
    cand = np.asarray(cand)
    out = np.full(len(days), -1)
    if len(cand) == 0:
        return out
    s, e = vt.term_start.values[cand], vt.exp_end.values[cand]
    for _ in range(tries):
        need = np.where(out < 0)[0]
        if len(need) == 0:
            break
        p = rng.integers(0, len(cand), len(need))
        ok = (s[p] <= days[need]) & (e[p] > days[need])
        out[need[ok]] = cand[p[ok]]
    return out


def mark_genuine(W, claim_ids, coverages=None, mult=0.0):
    W.genuine_rules.append((np.asarray(claim_ids, dtype=object), coverages, mult))


# =============================================================================
# PRE-TERMS
# =============================================================================
def pre_terms(W):
    if _on(W, "PRODUCER_GARAGING_EVASION"):
        garaging(W)
    if _on(W, "PRODUCER_GHOST_POLICIES"):
        ghosts(W)
    if _on(W, "HARD_PHANTOM_VEHICLE"):
        phantom_setup(W)
    if _on(W, "HARD_POST_LOSS_INCEPTION"):
        postloss_setup(W)
    if _on(W, "HARD_OWNER_GIVEUP"):
        giveup_setup(W)


def garaging(W):
    rng, sc = W.rng, _sc(W, "PRODUCER_GARAGING_EVASION")
    hh, pr, dr, ve = W.t["households"], W.t["producers"], W.t["drivers"], W.t["vehicles"]
    decl, true = sc["geo_declared"][0], sc["geo_true"][0]
    st = R.METROS[decl][0]
    ag = pr[pr.channel == "INDEPENDENT_AGENT"].sample(sc["producers"], random_state=int(rng.integers(1e9))).index
    prods = pr.loc[ag, "producer_id"].values
    # move the two agencies to the declared metro and re-home their old book
    old = hh.producer_id.isin(prods)
    for m in hh.loc[old, "metro"].unique():
        idx = hh.index[old & (hh.metro == m)]
        alt = pr[(pr.metro == m) & (pr.channel == "INDEPENDENT_AGENT") & ~pr.producer_id.isin(prods)].producer_id.values
        hh.loc[idx, "producer_id"] = alt[rng.integers(0, len(alt), len(idx))] if len(alt) else "PRD-DIRECT"
    pr.loc[ag, ["metro", "state", "city"]] = [decl, st, R.METROS[decl][1]]
    pr.loc[ag, "phone"] = W.geo.phone([decl] * len(ag))
    n_bad = _n(W, sc["policies"])
    n_good = int(n_bad * (1 - sc["book_share"]) / sc["book_share"])
    good = hh.index[hh.metro == decl]
    good = rng.choice(good, min(n_good, len(good)), replace=False)
    hh.loc[good, ["channel", "producer_id"]] = np.column_stack([["INDEPENDENT_AGENT"] * len(good), prods[rng.integers(0, len(prods), len(good))]])
    bad = rng.choice(hh.index[hh.metro == true], n_bad, replace=False)
    sig = W.signals("PRODUCER_GARAGING_EVASION", n_bad)
    sig["loss_far_from_garaging"] = sig["loss_far_from_garaging"]  # applied at claim time
    pool_addr = W.geo.street(30)
    pool_zip, pool_zf = W.geo.sample_zip([decl] * 30)
    zipc, zf = W.geo.sample_zip([decl] * n_bad)
    addr = W.geo.street(n_bad)
    sh = sig.shared_garaging_address.values
    k = rng.integers(0, 30, n_bad)
    addr = np.where(sh, pool_addr[k], addr); zipc = np.where(sh, pool_zip[k], zipc); zf = np.where(sh, pool_zf[k], zf)
    hh.loc[bad, "_true_zip_factor"] = hh.loc[bad, "_zip_factor"].values
    hh.loc[bad, ["metro", "state", "city", "address", "zip"]] = np.column_stack(
        [[decl] * n_bad, [st] * n_bad, [R.METROS[decl][1]] * n_bad, addr, zipc])
    hh.loc[bad, "_zip_factor"] = zf
    hh.loc[bad, "phone"] = np.where(sig.out_of_state_phone.values, hh.loc[bad, "phone"].values, W.geo.phone([decl] * n_bad))
    hh.loc[bad, ["channel", "producer_id"]] = np.column_stack([["INDEPENDENT_AGENT"] * n_bad, prods[rng.integers(0, len(prods), n_bad)]])
    hh.loc[bad, "pip_limit"] = R.STATES[st][1][0]
    hh.loc[bad, "_garaging_sig"] = _sigstr(sig)
    cids = hh.loc[bad, "customer_id"].values
    keep_ny = pd.Series(sig.out_of_state_license.values, index=cids)
    dm = dr.customer_id.isin(cids)
    dr.loc[dm, "license_state"] = np.where(keep_ny.reindex(dr.loc[dm, "customer_id"]).values, R.METROS[true][0], st)
    vm = ve.customer_id.isin(cids)
    ve.loc[vm, "garaging_zip"] = hh.set_index("customer_id").zip.reindex(ve.loc[vm, "customer_id"]).values
    W.truth_add("PRODUCER_GARAGING_EVASION", "POLICY", cids, sig, ring_id="GAR-ALLENTOWN", role="misrepresented_policy")
    W.truth_add("PRODUCER_GARAGING_EVASION", "PRODUCER", prods, ring_id="GAR-ALLENTOWN", role="producer")
    W.storylines["GAR-ALLENTOWN"] = {"title": "Allentown agencies writing Brooklyn drivers",
                                     "scenario": "PRODUCER_GARAGING_EVASION", "producers": list(prods)}


def ghosts(W):
    rng, sc = W.rng, _sc(W, "PRODUCER_GHOST_POLICIES")
    hh, pr, ve = W.t["households"], W.t["producers"], W.t["vehicles"]
    m = sc["geo"][0]
    cand = pr[(pr.metro == m) & (pr.channel == "CAPTIVE_AGENT")]
    prod = cand.producer_id.values[rng.integers(len(cand))]
    w = sc["window"]
    elig = hh.index[(hh.metro == m) & (hh._tenure == 0) & (hh._first_start >= d2i(w[0])) & (hh._first_start <= d2i(w[1]))
                    & (hh.get("_garaging_sig", pd.Series("", index=hh.index)).fillna("") == "")]
    n = min(_n(W, sc["policies"]), len(elig))
    g = rng.choice(elig, n, replace=False)
    sig = W.signals("PRODUCER_GHOST_POLICIES", n)
    hh.loc[g, ["channel", "producer_id"]] = np.column_stack([["CAPTIVE_AGENT"] * n, [prod] * n])
    hh.loc[g, "_n_terms"] = 1
    hh.loc[g, "_force_cancel"] = np.where(sig.cancel_nonpay_within_60d.values, rng.integers(14, 60, n), rng.integers(61, 130, n))
    hh.loc[g, "_frailty"] = 0.0
    hh.loc[g, "_ghost"] = True
    shared = sig.shared_email_domain_or_phone.values
    pool_ph = W.geo.phone([m] * 20)
    hh.loc[g, "phone"] = np.where(shared, pool_ph[rng.integers(0, 20, n)], hh.loc[g, "phone"].values)
    hh.loc[g, "email"] = np.where(shared, [f"{a.lower()}{rng.integers(10, 99)}@quickinbox.example" for a in hh.loc[g, "first_name"]],
                                  hh.loc[g, "email"].values)
    hh.loc[g, "prior_carrier"] = "NONE"
    cids = hh.loc[g, "customer_id"].values
    mini = pd.Series(sig.minimal_vehicle_info.values, index=cids)
    vm = ve.customer_id.isin(cids) & mini.reindex(ve.customer_id).fillna(False).values
    ve.loc[vm, "declared_annual_miles"] = 12000
    ve.loc[vm, "lienholder_flag"] = False
    W.truth_add("PRODUCER_GHOST_POLICIES", "POLICY", cids, sig, ring_id="GHOST-ATL", role="fictitious_policy")
    W.truth_add("PRODUCER_GHOST_POLICIES", "PRODUCER", [prod], ring_id="GHOST-ATL", role="producer")
    W.storylines["GHOST-ATL"] = {"title": "Atlanta captive agent writing policies that never pay", "scenario": "PRODUCER_GHOST_POLICIES", "producers": [prod]}


def _nb_pool(W):
    hh = W.t["households"]
    clean = (hh._tenure == 0)
    for c in ("_ghost", "_garaging_sig", "_phantom", "_postloss"):
        if c in hh:
            clean &= ~hh[c].fillna(False).astype(bool) if hh[c].dtype == bool else (hh[c].fillna("") == "")
    return hh.index[clean]


def phantom_setup(W):
    rng, sc = W.rng, _sc(W, "HARD_PHANTOM_VEHICLE")
    hh, ve = W.t["households"], W.t["vehicles"]
    pool = _nb_pool(W)
    n = max(5, int(len(pool) * sc["prevalence"]))
    g = rng.choice(pool, n, replace=False)
    sig = W.signals("HARD_PHANTOM_VEHICLE", n)
    hh.loc[g, "_phantom"] = True
    hh.loc[g, "_n_terms"] = np.maximum(1, hh.loc[g, "_n_terms"].values)
    hh.loc[g, "prior_carrier"] = np.where(sig.no_prior_insurance.values, "NONE", hh.loc[g, "prior_carrier"].values)
    cids = hh.loc[g, "customer_id"].values
    first_v = ve[ve.customer_id.isin(cids)].groupby("customer_id").head(1).set_index("customer_id")
    vidx = ve.index[ve.vehicle_id.isin(first_v.vehicle_id.reindex(cids).values)]
    order = pd.Series(vidx, index=ve.loc[vidx, "customer_id"].values).reindex(cids).values
    yrs = rng.integers(2020, 2025, n)
    ve.loc[order, "model_year"] = yrs
    ve.loc[order, "msrp"] = np.round(ve.loc[order, "msrp"].values * rng.uniform(1.15, 1.5, n), -2)
    vins = ve.loc[order, "vin"].values.copy()
    donors = ve.vin.values[rng.integers(0, len(ve), n)]
    vins = np.where(sig.vin_cloned_from_other_vehicle.values, donors, vins)
    vins = np.array([break_vin(rng, v) if b else v for v, b in zip(vins, sig.vin_fails_checkdigit.values)], dtype=object)
    ve.loc[order, "vin"] = vins
    ve.loc[order, "lienholder_flag"] = ~sig.no_lienholder_on_new_vehicle.values
    ve.loc[order, "coll_deductible"] = np.where(np.isnan(ve.loc[order, "coll_deductible"].values.astype(float)), 500.0, ve.loc[order, "coll_deductible"].values)
    ve.loc[order, "comp_deductible"] = np.where(np.isnan(ve.loc[order, "comp_deductible"].values.astype(float)), 500.0, ve.loc[order, "comp_deductible"].values)
    ve.loc[order, "_phantom_sig"] = _sigstr(sig)
    W.truth_add("HARD_PHANTOM_VEHICLE", "VEHICLE", ve.loc[order, "vehicle_id"].values, sig, role="phantom_vehicle")


def postloss_setup(W):
    rng, sc = W.rng, _sc(W, "HARD_POST_LOSS_INCEPTION")
    hh, ve = W.t["households"], W.t["vehicles"]
    pool = _nb_pool(W)
    n = int(len(pool) * sc["prevalence"])
    g = rng.choice(pool, n, replace=False)
    sig = W.signals("HARD_POST_LOSS_INCEPTION", n)
    hh.loc[g, "_postloss"] = _sigstr(sig)
    hh.loc[g, "prior_lapse_days"] = np.where(sig.prior_coverage_lapse.values, rng.integers(4, 95, n), 0)
    hh.loc[g, "prior_carrier"] = np.where(sig.prior_coverage_lapse.values & (rng.random(n) < 0.4), "NONE", hh.loc[g, "prior_carrier"].values)
    on = sig.online_bind_night.values
    hh.loc[g[on], ["channel", "producer_id"]] = ["DIRECT_ONLINE", "PRD-DIRECT"]
    hh.loc[g, "_bind_hour_force"] = np.where(on, rng.choice([22, 23, 0, 1, 2], n), -1)
    cids = hh.loc[g, "customer_id"].values
    v1 = ve[ve.customer_id.isin(cids)].groupby("customer_id").head(1)
    add = pd.Series(sig.coverage_added_at_bind.values, index=cids).reindex(v1.customer_id).values
    ve.loc[v1.index, "coll_deductible"] = np.where(add | np.isnan(v1.coll_deductible.values.astype(float)), rng.choice([250.0, 500.0], len(v1)), v1.coll_deductible.values)
    ve.loc[v1.index, "comp_deductible"] = np.where(add | np.isnan(v1.comp_deductible.values.astype(float)), rng.choice([0.0, 250.0], len(v1)), v1.comp_deductible.values)
    ve.loc[v1.index, "_postloss_vehicle"] = True
    W.truth_add("HARD_POST_LOSS_INCEPTION", "POLICY", cids, sig, role="post_loss_bind")


def giveup_setup(W):
    rng, sc = W.rng, _sc(W, "HARD_OWNER_GIVEUP")
    hh, ve = W.t["households"], W.t["vehicles"]
    age = 2024 - ve.model_year.values
    w = np.where((age >= 3) & (age <= 12), 1.0, 0.05) * (ve.msrp.values / 30000) ** 1.5
    bad_hh = hh.index[hh.get("_ghost", pd.Series(False, index=hh.index)).fillna(False).astype(bool)]
    w[ve._hh.isin(bad_hh).values] = 0
    n = int(len(ve) * sc["prevalence"])
    idx = ve.index[rng.choice(len(ve), n, replace=False, p=w / w.sum())]
    sig = W.signals("HARD_OWNER_GIVEUP", n)
    ve.loc[idx, "lienholder_flag"] = sig.financed_vehicle.values | ve.loc[idx, "lienholder_flag"].values
    rc = sig.recent_coverage_change.values
    cur = ve.loc[idx, "comp_deductible"].values.astype(float)
    ve.loc[idx, "comp_deductible"] = np.where(rc, rng.choice([0.0, 250.0], n), np.where(np.isnan(cur), 500.0, cur))
    ve.loc[idx, "coll_deductible"] = np.where(np.isnan(ve.loc[idx, "coll_deductible"].values.astype(float)), 1000.0, ve.loc[idx, "coll_deductible"].values)
    hhi = ve.loc[idx, "_hh"].values
    hh.loc[hh.index[hhi[sig.missed_payments.values]], "_missed_payments"] += rng.integers(2, 6, sig.missed_payments.sum())
    ve.loc[idx, "_giveup_sig"] = _sigstr(sig)
    W.truth_add("HARD_OWNER_GIVEUP", "VEHICLE", ve.loc[idx, "vehicle_id"].values, sig, role="owner_giveup_vehicle")


# =============================================================================
# PRE-CLAIMS (exposure exists)
# =============================================================================
def pre_claims(W):
    vt = W.t["vt"]
    hh = W.t["households"]
    vt["_uplift_liab"] = 1.0; vt["_uplift_coll"] = 1.0; vt["_uplift_comp"] = 1.0
    vt["metro_declared"] = hh.metro.values[vt._hh.values]
    gs = hh.get("_garaging_sig", pd.Series("", index=hh.index)).fillna("").values
    vt["_garaging_sig"] = gs[vt._hh.values]
    ve = W.t["vehicles"].set_index("vehicle_id")
    for col in ("_phantom_sig", "_giveup_sig"):
        if col in ve:
            s = ve[col].reindex(vt.vehicle_id).fillna("").values
            vt.loc[s != "", ["_uplift_liab", "_uplift_coll", "_uplift_comp"]] = 0.0 if col == "_phantom_sig" else 1.0
    if _on(W, "SOFT_UNLISTED_DRIVER"):
        unlisted(W)
    if _on(W, "SOFT_RIDESHARE_UNDISCLOSED"):
        rideshare(W)


def unlisted(W):
    rng, sc = W.rng, _sc(W, "SOFT_UNLISTED_DRIVER")
    hh, dr, vt = W.t["households"], W.t["drivers"], W.t["vt"]
    age = 2023 - hh.date_of_birth.dt.year.values
    w = np.where((age >= 38) & (age <= 62), 1.0, 0.25)
    for c in ("_ghost", "_phantom"):
        if c in hh:
            w[hh[c].fillna(False).astype(bool).values] = 0
    n = int(len(hh) * sc["prevalence"])
    g = rng.choice(len(hh), n, replace=False, p=w / w.sum())
    sig = W.signals("SOFT_UNLISTED_DRIVER", n)
    da = np.where(sig.operator_under_25.values, rng.integers(16, 24, n), rng.integers(25, 31, n))
    gender = np.where(rng.random(n) < 0.55, "M", "F")
    sur = np.where(sig.operator_same_surname.values, hh.last_name.values[g], W.names.surnames(n))
    f, m, l, s = W.names.people(gender, 2023 - da, surname=np.array([x.upper() for x in sur], dtype=object))
    addr = np.where(sig.operator_address_match.values, hh.address.values[g], W.geo.street(n))
    new = pd.DataFrame({"driver_id": W.ids.take("DRV", n, 7), "customer_id": hh.customer_id.values[g],
                        "relationship": np.where(sig.operator_same_surname.values, "CHILD", "OTHER"),
                        "first_name": f, "middle_name": m, "last_name": l, "suffix": s, "gender": gender,
                        "date_of_birth": pd.to_datetime((2023 - da).astype(str)) + pd.to_timedelta(rng.integers(0, 365, n), "D"),
                        "license_state": hh.state.values[g], "license_number": token(rng, "DL", n, 9),
                        "violations_3yr": rng.poisson(0.5, n), "at_fault_accidents_3yr": rng.poisson(0.2, n),
                        "marital_status": "SINGLE", "_listed": False, "_address": addr})
    new["first_licensed_date"] = new.date_of_birth + pd.to_timedelta(rng.integers(16 * 365, 18 * 365, n), "D")
    W.t["drivers"] = pd.concat([dr, new], ignore_index=True)
    hid = pd.Series(new.driver_id.values, index=g)
    m_vt = np.isin(vt._hh.values, g)
    vt.loc[m_vt, "_unlisted_driver"] = hid.reindex(vt._hh.values[m_vt]).values
    vt["_unlisted_driver"] = vt._unlisted_driver.fillna("")
    hid_age = pd.Series(new.date_of_birth.dt.year.values, index=g).reindex(vt._hh.values[m_vt]).values
    ys = 1970 + vt.term_start.values[m_vt] / 365.25
    vt.loc[m_vt, "_true_youngest_age"] = np.minimum(vt.loc[m_vt, "youngest_age"].values, (ys - hid_age).astype(int))
    up = sc["frequency_uplift"]
    vt.loc[m_vt, "_uplift_liab"] *= up; vt.loc[m_vt, "_uplift_coll"] *= up
    W.truth_add("SOFT_UNLISTED_DRIVER", "POLICY", hh.customer_id.values[g], sig, role="policy_with_unlisted_driver")
    W.truth_add_raw("SOFT_UNLISTED_DRIVER", "DRIVER", new.driver_id.values, "", role="unlisted_driver")


def rideshare(W):
    rng, sc = W.rng, _sc(W, "SOFT_RIDESHARE_UNDISCLOSED")
    ve, hh, vt = W.t["vehicles"], W.t["households"], W.t["vt"]
    metro = hh.metro.values[ve._hh.values]
    elig = np.isin(metro, sc["geo"]) & (ve.model_year.values >= 2016) & np.isin(ve.segment.values, ["sedan_mid", "sedan_small", "suv_small", "suv_mid", "ev", "minivan"])
    idx = ve.index[elig]
    n = int(len(idx) * sc["prevalence"] / 0.35)  # prevalence is of the whole book, concentrated in these metros
    n = min(n, len(idx))
    pick_i = rng.choice(idx, n, replace=False)
    sig = W.signals("SOFT_RIDESHARE_UNDISCLOSED", n)
    true_miles = np.round(rng.uniform(26000, 46000, n), -2)
    ve.loc[pick_i, "_true_usage"] = "RIDESHARE"
    ve.loc[pick_i, "_true_miles"] = true_miles
    ve.loc[pick_i, "_odo_miles"] = np.where(sig.odometer_vs_declared_miles.values, true_miles, ve.loc[pick_i, "declared_annual_miles"].values)
    s = pd.Series(_sigstr(sig), index=ve.loc[pick_i, "vehicle_id"].values)
    vt["_rideshare_sig"] = s.reindex(vt.vehicle_id).fillna("").values
    m = vt._rideshare_sig.values != ""
    decl = ve.set_index("vehicle_id").declared_annual_miles.reindex(vt.vehicle_id[m]).values
    tm = ve.set_index("vehicle_id")._true_miles.reindex(vt.vehicle_id[m]).values
    mf = lambda x: np.where(x < 7500, 0.85, np.where(x > 15000, 1.0 + (x - 15000) / 30000, 1.0))
    adj = sc["frequency_uplift"] / (mf(tm) / mf(decl))
    vt.loc[m, "_uplift_liab"] *= np.maximum(adj, 1.0); vt.loc[m, "_uplift_coll"] *= np.maximum(adj, 1.0)
    W.truth_add("SOFT_RIDESHARE_UNDISCLOSED", "VEHICLE", ve.loc[pick_i, "vehicle_id"].values, sig, role="undisclosed_rideshare_vehicle")


# =============================================================================
# ADD CLAIMS
# =============================================================================
def _spec(vt_idx, days, cause, **kw):
    d = {"vt_idx": np.asarray(vt_idx), "loss_day": np.asarray(days), "cause": cause}
    d.update(kw)
    n = len(d["vt_idx"])
    for k, v in list(d.items()):
        if not isinstance(v, (np.ndarray, list, pd.Series)):
            d[k] = [v] * n if v is None or isinstance(v, (list, tuple)) else np.repeat(v, n)
        if isinstance(d[k], list):
            s_ = pd.Series([None] * n, dtype=object)
            for i, x in enumerate(d[k]):
                s_.iat[i] = x
            d[k] = s_
    return pd.DataFrame(d)


def _hours(W, n, night=False):
    from .baseline import hours
    return hours(W.rng, W.cfg["frequency"]["hourly_profile"], n, night=np.full(n, night))


def add_claims(W, fac):
    W.genuine_rules = getattr(W, "genuine_rules", [])
    steps = [("HARD_POST_LOSS_INCEPTION", postloss_claims), ("HARD_OWNER_GIVEUP", giveup_claims),
             ("HARD_PHANTOM_VEHICLE", phantom_claims), ("RING_PIP_MILL_MIAMI", pip_mill),
             ("RING_SWOOP_AND_SQUAT", swoop), ("RING_GLASS_SOLICITATION", glass_ring),
             ("BENIGN_CAT_HAIL", cat_events), ("BENIGN_CAT_FLOOD", cat_events),
             ("BENIGN_THEFT_WAVE_KIA_HYUNDAI", theft_wave), ("BENIGN_WINTER_PILEUP", pileups),
             ("HARD_DUPLICATE_LOSS", duplicates)]
    for name, fn in steps:
        if _on(W, name):
            fn(W, fac, name)


def _first_vt(W, cids, vehicle_col=None):
    vt = W.t["vt"]
    hh = W.t["households"]
    cid = hh.customer_id.values[vt._hh.values]
    d = pd.DataFrame({"i": np.arange(len(vt)), "cid": cid, "s": vt.term_start.values, "veh": vt.vehicle_id.values})
    d = d[d.cid.isin(cids)]
    if vehicle_col is not None:
        d = d[d.veh.isin(vehicle_col)]
    return d.sort_values("s").groupby("cid").head(1 if vehicle_col is None else 10**6)


def postloss_claims(W, fac, name):
    rng = W.rng
    hh, ve, vt = W.t["households"], W.t["vehicles"], W.t["vt"]
    rows = hh[hh.get("_postloss", pd.Series("", index=hh.index)).fillna("") != ""]
    vids = ve[ve.get("_postloss_vehicle", pd.Series(False, index=ve.index)).fillna(False).astype(bool)].vehicle_id
    d = _first_vt(W, rows.customer_id.values, vids.values)
    d = d.sort_values("s").groupby("cid").head(1)
    n = len(d)
    sig = rows.set_index("customer_id")._postloss.reindex(d.cid).values
    days = d.s.values + rng.integers(0, 11, n)
    cause = pick(rng, {"AF_SINGLE": 0.40, "NAF_UNINSURED": 0.35, "AF_MULTI": 0.25}, n)
    older = np.array(["damage_older_than_loss_date" in s for s in sig])
    narr = np.where(older, "Insured reports collision on {road}. Appraiser notes weathering and debris in damaged area inconsistent with reported loss date.", "")
    spec = _spec(d.i.values, days, cause, loss_hour=_hours(W, n, night=True), sev_mult=rng.uniform(1.2, 2.0, n),
                 report_lag=rng.uniform(0.05, 1.5, n), narrative=narr, n_tp_injured=0, n_ins_injured=0,
                 want_pd=cause == "AF_MULTI", want_coll=True)
    c = fac.create(spec, tag=name)
    mark_genuine(W, c.claim_id.values)
    W.truth_add(name, "CLAIM", c.claim_id.values, list(sig[:len(c)]), role="claim_on_post_loss_policy")


def giveup_claims(W, fac, name):
    rng = W.rng
    ve, vt = W.t["vehicles"], W.t["vt"]
    gv = ve[ve.get("_giveup_sig", pd.Series("", index=ve.index)).fillna("") != ""]
    d = pd.DataFrame({"i": np.arange(len(vt)), "veh": vt.vehicle_id.values, "s": vt.term_start.values, "e": vt.exp_end.values})
    d = d[d.veh.isin(gv.vehicle_id) & ((d.e - d.s) > 90)]
    d = d.sample(frac=1, random_state=int(rng.integers(1e9))).groupby("veh").head(1)
    n = len(d)
    sig = gv.set_index("vehicle_id")._giveup_sig.reindex(d.veh).values
    days = d.s.values + (rng.uniform(0.25, 0.97, n) * (d.e.values - d.s.values)).astype(int)
    fire = rng.random(n) < 0.35
    burned = np.array(["burned_recovered_remote" in s for s in sig])
    keys = np.array(["keys_unaccounted" in s for s in sig])
    late = np.array(["late_report" in s for s in sig])
    narr = np.where(fire, "Vehicle caught fire while parked at {loc} overnight; fire department responded.",
                    np.where(burned, "Vehicle stolen from {loc}; later recovered burned in a remote area.",
                             "Vehicle stolen from {loc} overnight."))
    narr = np.array([x + (" Insured could provide only one key." if k else "") for x, k in zip(narr, keys)], dtype=object)
    spec = _spec(d.i.values, days, np.where(fire, "FIRE", "THEFT"), loss_hour=_hours(W, n, night=True),
                 report_lag=np.where(late, rng.uniform(2, 7, n), rng.uniform(0.1, 1.0, n)),
                 theft_recovered=np.where(burned, 1.0, 0.0), total_loss_force=fire | burned, narrative=narr)
    c = fac.create(spec, tag=name)
    mark_genuine(W, c.claim_id.values)
    m = pd.Series(sig, index=d.i.values)
    W.truth_add(name, "CLAIM", c.claim_id.values, list(m.reindex(c._vt_idx.values).values), role="owner_giveup_claim")


def phantom_claims(W, fac, name):
    rng = W.rng
    ve, vt = W.t["vehicles"], W.t["vt"]
    pv = ve[ve.get("_phantom_sig", pd.Series("", index=ve.index)).fillna("") != ""]
    d = pd.DataFrame({"i": np.arange(len(vt)), "veh": vt.vehicle_id.values, "s": vt.term_start.values, "e": vt.exp_end.values})
    d = d[d.veh.isin(pv.vehicle_id)].sort_values("s").groupby("veh").head(1)
    n = len(d)
    days = np.minimum(d.s.values + rng.integers(25, 90, n), d.e.values - 1)
    theft = rng.random(n) < 0.55
    spec = _spec(d.i.values, days, np.where(theft, "THEFT", "AF_SINGLE"), loss_hour=_hours(W, n, night=True),
                 theft_recovered=0.0, total_loss_force=True, want_pd=False, report_lag=rng.uniform(0.2, 2, n))
    c = fac.create(spec, tag=name)
    mark_genuine(W, c.claim_id.values)
    sig = pv.set_index("vehicle_id")._phantom_sig.reindex(c.vehicle_id).values
    W.truth_add(name, "CLAIM", c.claim_id.values, list(sig), role="phantom_vehicle_total_loss")


def pip_mill(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    m = sc["geo"][0]
    ring = "RING-MIA-PIP"
    prov = {}
    for pt in ("CHIRO", "IMAGING", "PAIN_MGMT", "PT", "ORTHO"):
        prov[pt] = new_parties(W, pt, m, 1, ring)[0]
    atts = new_parties(W, "ATTORNEY", m, 2, ring)
    W.ring_providers["MIA_MILL"] = prov
    fac.__init__(W)
    runners = ring_people(W, _n(W, 110), m, 14, 18, ring, name)
    vt, hh = W.t["vt"], W.t["households"]
    mh = np.where((hh.metro.values == m) & ~hh.get("_ghost", pd.Series(False, index=hh.index)).fillna(False).astype(bool).values)[0]
    recruit = rng.choice(mh, min(_n(W, sc["households"]), len(mh)), replace=False)
    sh = rng.random(len(recruit)) < sc["signals"]["shared_phone_or_address"]
    ph = W.geo.phone([m] * 14)
    ad = W.geo.street(18)
    hh.loc[hh.index[recruit[sh]], "phone"] = ph[rng.integers(0, 14, sh.sum())]
    two = sh & (rng.random(len(recruit)) < 0.5)
    hh.loc[hh.index[recruit[two]], "address"] = ad[rng.integers(0, 18, two.sum())]
    cand = np.where(np.isin(vt._hh.values, recruit))[0]
    n = _n(W, sc["staged_accidents"])
    days = window_days(W, sc, n)
    vi = sample_active(W, cand, days)
    ok = vi >= 0
    vi, days = vi[ok], days[ok]
    n = len(vi)
    sig = W.signals(name, n)
    sig["shared_phone_or_address"] = pd.Series(sh, index=recruit).reindex(vt._hh.values[vi]).values
    occ = rng.integers(sc["occupants"][0], sc["occupants"][1] + 1, n)
    dr = W.t["drivers"]
    ni = dr[dr.relationship == "NAMED_INSURED"].set_index("customer_id").driver_id
    op = ni.reindex(hh.customer_id.values[vt._hh.values[vi]]).values
    pas = []
    for k, o, rep in zip(occ, op, sig.claimant_repeats.values):
        lst = ["DRV-" + o]
        for _ in range(k - 1):
            lst.append(runners[rng.integers(len(runners))] if (rep or rng.random() < 0.3) else None)
        pas.append(lst)
    cause = np.where(rng.random(n) < 0.7, "NAF", "AF_MULTI")
    spec = _spec(vi, days, cause, loss_hour=rng.integers(10, 20, n), n_ins_injured=occ, n_occupants=occ,
                 passenger_ids=pas, operator_driver_id=op,
                 attorney_id=np.where(sig.same_attorney.values, atts[rng.integers(0, 2, n)], ""),
                 provider_set=np.where(sig.same_clinic.values, "MIA_MILL", ""),
                 treatment=np.where(sig.identical_treatment_plan.values, "MILL", ""),
                 sev_mult=np.where(sig.low_property_damage.values, rng.uniform(0.15, 0.4, n), 1.0),
                 pd_sev_mult=np.where(sig.low_property_damage.values, rng.uniform(0.15, 0.4, n), 1.0),
                 reported_by=np.where(rng.random(n) < 0.4, "ATTORNEY", "INSURED"), report_lag=rng.uniform(0.5, 5, n),
                 loss_metro=m, want_coll=True, want_pd=True,
                 narrative=np.where(cause == "NAF", "Low-speed rear-end collision at {road}; vehicle occupied by driver and passengers, all complaining of neck and back pain.", ""))
    c = fac.create(spec, tag=name)
    mark_genuine(W, c.claim_id.values)
    W.truth_add(name, "CLAIM", c.claim_id.values, sig.iloc[:len(c)], ring_id=ring, role="staged_claim")
    W.truth_add_raw(name, "PARTY", list(prov.values()) + list(atts), ring, role="ring_provider_or_attorney")
    W.truth_add_raw(name, "POLICY", hh.customer_id.values[recruit], ring, role="recruited_policy")
    W.storylines[ring] = {"title": "Miami PIP mill: clinic + attorneys + recruited policies", "scenario": name,
                          "parties": list(prov.values()) + list(atts)}


def swoop(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    vt = W.t["vt"]
    total = _n(W, sc["staged_accidents"])
    split = [0.6, 0.4]
    for m, share in zip(sc["geo"], split):
        ring = f"RING-{m[:3]}-SWOOP"
        prov = {pt: new_parties(W, pt, m, 1, ring)[0] for pt in ("CHIRO", "PT", "IMAGING", "ORTHO")}
        att = new_parties(W, "ATTORNEY", m, 1, ring)[0]
        key = f"{m}_SWOOP"
        W.ring_providers[key] = prov
        fac.__init__(W)
        crew = ring_people(W, _n(W, 40), m, 8, 10, ring, name)
        k = sc["crew_vehicles_per_ring"]
        vi_ = rng.choice(len(R.VEHICLES), k)
        yrs = rng.integers(2007, 2016, k)
        cvins = make_vins(rng, np.array([R.VEHICLES[i][5] for i in vi_], dtype=object), yrs)
        cdesc = np.array([f"{y} {R.VEHICLES[i][0]} {R.VEHICLES[i][1]}" for y, i in zip(yrs, vi_)], dtype=object)
        n = int(total * share)
        days = window_days(W, sc, n)
        cand = np.where(vt.metro.values == m)[0]
        vi = sample_active(W, cand, days)
        ok = vi >= 0
        vi, days = vi[ok], days[ok]
        n = len(vi)
        sig = W.signals(name, n)
        occ = rng.integers(sc["occupants"][0], sc["occupants"][1] + 1, n)
        tpc = [[crew[rng.integers(len(crew))] if (r or rng.random() < 0.25) else None for _ in range(o)]
               for o, r in zip(occ, sig.repeat_tp_claimants.values)]
        cv = rng.integers(0, k, n)
        spec = _spec(vi, days, "AF_MULTI", loss_hour=_hours(W, n), n_tp_injured=occ, n_ins_injured=0,
                     tp_claimant_ids=tpc, tp_vin=np.where(sig.repeat_tp_vehicle.values, cvins[cv], ""),
                     tp_vehicle_desc=np.where(sig.repeat_tp_vehicle.values, cdesc[cv], ""),
                     attorney_id=np.where(sig.same_attorney.values, att, ""),
                     provider_set=np.where(sig.same_provider.values, key, ""),
                     treatment=np.where(sig.same_provider.values & (rng.random(n) < 0.85), "MILL", ""),
                     location_type=np.where(sig.freeway_merge_location.values, "FREEWAY_ON_RAMP", ""),
                     narrative=np.where(sig.sudden_stop_narrative.values,
                                        "Vehicle ahead braked suddenly while merging onto {road}; insured could not stop and rear-ended it.", ""),
                     pd_sev_mult=rng.uniform(1.2, 1.8, n), loss_metro=m, reported_by="THIRD_PARTY",
                     report_lag=rng.uniform(0.3, 6, n), zone="FRONT", want_pd=True, want_coll=True)
        c = fac.create(spec, tag=name)
        W.genuine_rules.append((c.claim_id.values, ["BI"], 0.0))
        W.genuine_rules.append((c.claim_id.values, ["PD"], 0.35))
        W.truth_add(name, "CLAIM", c.claim_id.values, sig.iloc[:len(c)], ring_id=ring, role="staged_claim_innocent_insured")
        W.truth_add_raw(name, "PARTY", list(prov.values()) + [att], ring, role="ring_provider_or_attorney")
        W.truth_add_raw(name, "VIN", cvins, ring, role="crew_vehicle")
        W.storylines[ring] = {"title": f"{R.METROS[m][1]} swoop-and-squat crew", "scenario": name, "parties": list(prov.values()) + [att]}


def glass_ring(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    vt, hh = W.t["vt"], W.t["households"]
    has_comp = ~np.isnan(vt.comp_deductible.values)
    w0, w1 = d2i(sc["window"][0]), d2i(sc["window"][1])
    months = (w1 - w0) / 30.4
    per_vendor = _n(W, sc["extra_claims_per_month"] * months / len(sc["geo"]))
    for m in sc["geo"]:
        ring = f"RING-{m[:3]}-GLASS"
        vendor = new_parties(W, "GLASS", m, 1, ring)[0]
        zips = rng.choice(W.geo.zips[m], 3, replace=False)
        hzip = hh.zip.values[vt._hh.values]
        cand_all = np.where((vt.metro.values == m) & has_comp)[0]
        cand_zip = np.where((vt.metro.values == m) & has_comp & np.isin(hzip, zips))[0]
        n = per_vendor
        sig = W.signals(name, n)
        days = rng.integers(w0, w1, n)
        vi = np.where(sig.door_to_door_cluster_zip.values, sample_active(W, cand_zip, days), sample_active(W, cand_all, days))
        # repeat customers: reuse a previous victim vehicle a few months later
        rep = sig.repeat_glass_claim.values
        first = np.where(~rep & (vi >= 0))[0]
        for j in np.where(rep)[0]:
            if len(first) and j > 0:
                src = first[rng.integers(0, max(1, (first < j).sum()))] if (first < j).any() else first[0]
                cands = np.where(vt.vehicle_id.values[cand_all] == vt.vehicle_id.values[vi[src]])[0] if vi[src] >= 0 else []
                if len(cands):
                    vi[j] = sample_active(W, cand_all[cands], days[j:j + 1])[0]
                    sig.loc[j, "repeat_glass_claim"] = vi[j] >= 0
        ok = vi >= 0
        vi, days, sig = vi[ok], days[ok], sig[ok].reset_index(drop=True)
        n = len(vi)
        spec = _spec(vi, days, "GLASS", loss_hour=rng.integers(9, 18, n), shop_id=vendor,
                     reported_by=np.where(sig.vendor_reported.values, "VENDOR", "INSURED"),
                     report_lag=rng.uniform(0, 1.2, n), sev_mult=rng.uniform(1.25, 1.9, n),
                     narrative=np.where(sig.vendor_reported.values, "Glass vendor reports windshield damage; insured assigned benefits to vendor.", ""))
        c = fac.create(spec, tag=name)
        W.genuine_rules.append((c.claim_id.values, None, 0.15))
        W.glass_adas.extend(list(c.claim_id.values[sig.adas_calibration_on_non_adas_vehicle.values[:len(c)]]))
        W.truth_add(name, "CLAIM", c.claim_id.values, sig.iloc[:len(c)], ring_id=ring, role="solicited_glass_claim")
        W.truth_add_raw(name, "PARTY", [vendor], ring, role="glass_vendor")
        W.storylines[ring] = {"title": f"{R.METROS[m][1]} windshield solicitation vendor", "scenario": name, "parties": [vendor]}


def cat_events(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    vt = W.t["vt"]
    has_comp = ~np.isnan(vt.comp_deductible.values)
    cause = "WEATHER" if "HAIL" in name else "FLOOD"
    for ev in sc["events"]:
        m, d0 = ev["metro"], d2i(ev["start"])
        act = np.where((vt.metro.values == m) & has_comp & (vt.term_start.values <= d0) & (vt.exp_end.values > d0))[0]
        n = int(len(act) * ev["vehicle_hit_rate"])
        vi = rng.choice(act, n, replace=False)
        days = d0 + rng.integers(0, ev["days"], n)
        code = f"CAT-{cause[:4]}-{m[:3]}-{ev['start'][2:4]}{ev['start'][5:7]}"
        spec = _spec(vi, days, cause, loss_hour=rng.integers(12, 22, n), cat_code=code,
                     report_lag=rng.exponential(6, n) + 0.3, sev_mult=rng.uniform(0.9, 1.4, n), zone="TOP")
        c = fac.create(spec, tag=name)
        W.truth_add(name, "CLAIM", c.claim_id.values, None, ring_id=code, role="catastrophe_claim")
        W.storylines[code] = {"title": f"{'Hail' if cause == 'WEATHER' else 'Flood'} event {R.METROS[m][1]} {ev['start']}", "scenario": name}


def theft_wave(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    vt = W.t["vt"]
    w0, w1 = d2i(sc["window"][0]), d2i(sc["window"][1])
    m = (np.isin(vt.metro.values, sc["geo"]) & np.isin(vt.make.values, ["Kia", "Hyundai"]) &
         (vt.model_year.values >= sc["model_years"][0]) & (vt.model_year.values <= sc["model_years"][1]) &
         ~np.isnan(vt.comp_deductible.values))
    idx = np.where(m)[0]
    s = np.maximum(vt.term_start.values[idx], w0); e = np.minimum(vt.exp_end.values[idx], w1)
    ok = e > s
    idx, s, e = idx[ok], s[ok], e[ok]
    k = rng.poisson(sc["annual_theft_rate"] * (e - s) / 365)
    vi = np.repeat(idx, k)
    days = np.repeat(s, k) + (rng.random(len(vi)) * np.repeat(e - s, k)).astype(int)
    n = len(vi)
    spec = _spec(vi, days, "THEFT", loss_hour=_hours(W, n, night=True), theft_recovered=(rng.random(n) < 0.68).astype(float),
                 cat_code="TREND-KIAHYU-THEFT",
                 narrative="Vehicle stolen from {loc}; steering column broken and ignition tampered (USB-start method).")
    c = fac.create(spec, tag=name)
    W.truth_add(name, "CLAIM", c.claim_id.values, None, ring_id="TREND-KIAHYU-THEFT", role="theft_trend_claim")
    W.storylines["TREND-KIAHYU-THEFT"] = {"title": "Kia/Hyundai theft wave (genuine)", "scenario": name}


def pileups(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    vt = W.t["vt"]
    for ev in sc["events"]:
        m, d0 = ev["metro"], d2i(ev["start"])
        act = np.where((vt.metro.values == m) & (vt.term_start.values <= d0) & (vt.exp_end.values > d0))[0]
        n = min(ev["vehicles"], len(act))
        vi = rng.choice(act, n, replace=False)
        code = f"EVT-PILEUP-{m[:3]}-{ev['start'][2:4]}{ev['start'][5:7]}"
        pr = f"PR-{rng.integers(0, 10 ** 9):09d}"
        road = {"MINNEAPOLIS": "I-94", "BUFFALO": "I-90", "DETROIT": "I-75"}.get(m, "I-80")
        cause = np.where(rng.random(n) < 0.5, "AF_MULTI", "NAF")
        spec = _spec(vi, np.full(n, d0), cause, loss_hour=np.full(n, 7), cat_code=code, location_type="HIGHWAY",
                     n_tp_injured=np.where(cause == "AF_MULTI", rng.binomial(1, 0.3, n), 0),
                     n_ins_injured=rng.binomial(1, 0.35, n),
                     narrative=f"Chain-reaction pileup in whiteout conditions on {road}; multiple vehicles involved.")
        c = fac.create(spec, tag=name)
        W.pileup_reports[code] = (c.claim_id.values, pr, ev["vehicles"] + rng.integers(3, 15))
        W.truth_add(name, "CLAIM", c.claim_id.values, None, ring_id=code, role="pileup_claim")
        W.storylines[code] = {"title": f"Winter pileup {R.METROS[m][1]} {ev['start']}", "scenario": name}


def duplicates(W, fac, name):
    rng, sc = W.rng, _sc(W, name)
    C, F = W.table("claims"), W.table("features")
    vt = W.t["vt"]
    base = C[C._tag == "BASELINE"]
    ef = F[(F.coverage.isin(["COLL"]) | ((F.coverage == "COMP") & F.subtype.isin(["WEATHER", "VANDALISM"])))
           & F.claim_id.isin(base.claim_id)]
    ef = ef.drop_duplicates("claim_id")
    n = int(len(ef) * sc["prevalence"])
    src = ef.sample(n, random_state=int(rng.integers(1e9)))
    sig = W.signals(name, n)
    cpos = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(src.claim_id).values
    oday = C.loss_datetime.values[cpos].astype("datetime64[D]").astype(int)
    gap = np.where(sig.within_180_days.values, rng.integers(20, 180, n), rng.integers(181, 420, n))
    days = oday + gap
    veh = C.vehicle_id.values[cpos]
    d = pd.DataFrame({"i": np.arange(len(vt)), "veh": vt.vehicle_id.values, "s": vt.term_start.values, "e": vt.exp_end.values})
    d = d[d.veh.isin(veh)]
    vi = np.full(n, -1)
    for j in range(n):
        dd = d[(d.veh == veh[j]) & (d.s <= days[j]) & (d.e > days[j])]
        if len(dd):
            vi[j] = dd.i.values[0]
    ok = vi >= 0
    src, sig, vi, days, cpos = src[ok], sig[ok].reset_index(drop=True), vi[ok], days[ok], cpos[ok]
    n = len(vi)
    cause = C.loss_cause.values[cpos]
    desc = np.where(sig.similar_narrative.values, C.description.values[cpos], "")
    desc = np.array([x.replace("{", "(").replace("}", ")") for x in desc], dtype=object)
    shop = np.where(sig.different_shop.values, "", src.repairer_party_id.values)
    spec = _spec(vi, days, cause, loss_hour=_hours(W, n), narrative=desc, shop_id=shop, n_tp_injured=0, n_ins_injured=0,
                 want_pd=False, want_coll=True)
    c = fac.create(spec, tag=name)
    mark_genuine(W, c.claim_id.values)
    W.dup_pairs = list(zip(c.claim_id.values, src.feature_id.values[:len(c)], sig.same_damage_lines.values[:len(c)]))
    W.truth_add(name, "CLAIM", c.claim_id.values, sig.iloc[:len(c)], role="duplicate_of_" + "prior_claim",
                original_claim_id=src.claim_id.values[:len(c)])


# =============================================================================
# MUTATE (genuine claims inflated)
# =============================================================================
def _recalc(L, m):
    ns = m & (L.operation.values != "SUBLET")
    L.loc[ns, "line_amount"] = np.round(L.loc[ns, "part_amount"] + L.loc[ns, "body_labor_hours"] * L.loc[ns, "labor_rate"]
                                        + L.loc[ns, "refinish_hours"] * (L.loc[ns, "paint_rate"] + 38), 2)


def _zone_map(L):
    return L[L.zone.isin(list(R.PARTS))].drop_duplicates("feature_id").set_index("feature_id").zone


def _new_lines(W, L, fids, zones, k, supplement, delay):
    rng = W.rng
    zones = np.array([z if z in R.PARTS else rng.choice(["FRONT", "REAR", "LEFT", "RIGHT"]) for z in zones], dtype=object)
    rows = []
    ref = L.drop_duplicates("feature_id").set_index("feature_id")
    for f, z, kk, sp, dl in zip(fids, zones, k, supplement, delay):
        P = R.PARTS[z]
        sel = rng.choice(len(P), min(kk, len(P)), replace=False)
        lr = ref.labor_rate.get(f, 60.0)
        lr = 60.0 if pd.isna(lr) else lr
        wd = ref.written_date.get(f)
        for i in sel:
            p = P[i]
            rows.append((f, ref.claim_id.get(f), z, "REPLACE", p[0], "OEM", p[3] * rng.uniform(0.9, 1.3), p[4] * rng.uniform(0.9, 1.2),
                         p[1] * rng.uniform(0.95, 1.35), lr, round(lr * 0.95), sp, wd + np.timedelta64(int(dl), "D") if sp else wd))
    if not rows:
        return L
    N = pd.DataFrame(rows, columns=["feature_id", "claim_id", "zone", "operation", "part_name", "part_type", "body_labor_hours",
                                    "refinish_hours", "part_amount", "labor_rate", "paint_rate", "is_supplement", "written_date"])
    N["vendor_party_id"] = ""; N["quantity"] = 1; N["_genuine_amount"] = 0.0; N["_tl"] = False
    N["line_amount"] = N.part_amount + N.body_labor_hours * N.labor_rate + N.refinish_hours * (N.paint_rate + 38)
    for c in ("body_labor_hours", "refinish_hours"):
        N[c] = N[c].round(1)
    N["line_amount"] = N.line_amount.round(2); N["part_amount"] = N.part_amount.round(2)
    return pd.concat([L, N], ignore_index=True)


def _inflate(W, L, fids, sig, labor_mult=(1.3, 1.7)):
    rng = W.rng
    m = L.feature_id.isin(fids).values
    sfeat = pd.DataFrame(sig.values, index=fids, columns=sig.columns)
    if "replace_not_repair" in sig:
        rr = m & (L.operation.values == "REPAIR") & sfeat.replace_not_repair.reindex(L.feature_id).fillna(False).values.astype(bool)
        if rr.any():
            price = {p[0]: p[1] for z in R.PARTS.values() for p in z}
            L.loc[rr, "operation"] = "REPLACE"
            L.loc[rr, "part_type"] = "OEM"
            L.loc[rr, "part_amount"] = L.loc[rr, "part_name"].map(price).fillna(400).values * rng.uniform(0.95, 1.35, rr.sum())
            _recalc(L, rr)
    if "inflated_labor_hours" in sig:
        ih = m & (L.operation.values != "SUBLET") & sfeat.inflated_labor_hours.reindex(L.feature_id).fillna(False).values.astype(bool) & (rng.random(len(L)) < 0.6)
        L.loc[ih, "body_labor_hours"] = np.round(L.loc[ih, "body_labor_hours"] * rng.uniform(*labor_mult, ih.sum()), 1)
        _recalc(L, ih)
    return L


def mutate(W):
    rng = W.rng
    L, F, C, B = W.table("estimate_lines"), W.table("features"), W.table("claims"), W.table("medical_bills")
    L["_genuine_amount"] = L.line_amount.values
    B["_genuine_allowed"] = B.allowed_amount.values
    F["_gd_genuine"] = F._gd.values
    fraud_claims = set()
    for t in W.truth:
        if len(t) and t.entity_type.iloc[0] == "CLAIM" and t.layer.iloc[0] == "FRAUD":
            fraud_claims.update(t.entity_id.values)
    # duplicate loss: copy the original lines
    for new_c, src_f, same in getattr(W, "dup_pairs", []):
        if not same:
            continue
        nf = F[(F.claim_id == new_c) & F.coverage.isin(["COLL", "COMP"])].feature_id.values
        if not len(nf):
            continue
        cp = L[L.feature_id == src_f].copy()
        L = L[L.feature_id != nf[0]]
        cp["feature_id"] = nf[0]; cp["claim_id"] = new_c
        cp["written_date"] = C.loc[C.claim_id == new_c, "loss_datetime"].values[0].astype("datetime64[D]") + np.timedelta64(3, "D")
        cp["_genuine_amount"] = 0.0
        L = pd.concat([L, cp], ignore_index=True)
    # glass ring ADAS calibration on vehicles without ADAS
    ga = set(getattr(W, "glass_adas", []))
    if ga:
        gf = F[F.claim_id.isin(ga) & (F.subtype == "GLASS")]
        has_cal = set(L[(L.part_name == "ADAS calibration") & L.feature_id.isin(gf.feature_id)].feature_id)
        need = gf[~gf.feature_id.isin(has_cal)]
        N = pd.DataFrame({"feature_id": need.feature_id.values, "claim_id": need.claim_id.values, "zone": "SUBLET", "operation": "SUBLET",
                          "part_name": "ADAS calibration", "part_type": "", "body_labor_hours": 0.0, "refinish_hours": 0.0,
                          "part_amount": np.round(rng.uniform(380, 520, len(need)), 2), "labor_rate": np.nan, "paint_rate": np.nan,
                          "vendor_party_id": "", "quantity": 1, "is_supplement": False, "_genuine_amount": 0.0, "_tl": False})
        N["line_amount"] = N.part_amount
        N["written_date"] = L.drop_duplicates("feature_id").set_index("feature_id").written_date.reindex(N.feature_id).values
        L = pd.concat([L, N], ignore_index=True)
    # pileups share one police report
    for code, (cids, pr, nveh) in getattr(W, "pileup_reports", {}).items():
        mm = C.claim_id.isin(cids)
        C.loc[mm, ["police_report_flag", "police_report_number", "vehicles_involved"]] = [True, pr, nveh]
    W.t["estimate_lines"], W.t["claims"] = L, C
    if _on(W, "RING_BODYSHOP_HOUSTON"):
        bodyshop_ring(W, fraud_claims)
    if _on(W, "RING_TOW_STORAGE_PHILLY"):
        tow_ring(W, fraud_claims)
    if _on(W, "SOFT_ESTIMATE_PADDING"):
        padding(W, fraud_claims)
    if _on(W, "SOFT_PRIOR_DAMAGE"):
        prior_damage(W, fraud_claims)
    if _on(W, "SOFT_INJURY_BUILDUP"):
        buildup(W, fraud_claims)
    if _on(W, "BENIGN_LATE_REPORT_HOSPITALIZED"):
        late_report(W, fraud_claims)
    apply_genuine_rules(W)


def apply_genuine_rules(W):
    F = W.table("features")
    for cids, covs, mult in getattr(W, "genuine_rules", []):
        m = F.claim_id.isin(cids).values.copy()
        if covs is not None:
            m &= F.coverage.isin(covs).values
        if mult == 0.0:
            F.loc[m, "_fraud_full"] = True
        else:
            F.loc[m, "_genuine_mult"] = mult
    W.t["features"] = F


def _eligible_features(W, covs, fraud_claims, subtypes=None, metro=None, window=None):
    F, C = W.table("features"), W.table("claims")
    m = (F.coverage.isin(covs).values & ~F.claim_id.isin(fraud_claims).values).copy()
    if subtypes is not None:
        m &= F.subtype.isin(subtypes).values
    if metro is not None or window is not None:
        ci = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(F.claim_id).values
        if metro is not None:
            m &= np.isin(C._metro.values[ci], metro)
        if window is not None:
            d = C.loss_datetime.values[ci].astype("datetime64[D]").astype(int)
            m &= (d >= d2i(window[0])) & (d <= d2i(window[1]))
    return F[m]


def padding(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "SOFT_ESTIMATE_PADDING"), "SOFT_ESTIMATE_PADDING"
    L = W.table("estimate_lines")
    E = _eligible_features(W, ["COLL", "PD"], fraud_claims)
    E = E[E.feature_id.isin(L.feature_id) & (E.subtype != "PROPERTY")]
    n = int(len(E) * sc["prevalence"])
    sel = E.sample(n, random_state=int(rng.integers(1e9)))
    sig = W.signals(name, n)
    none = ~sig.any(axis=1)
    sig.loc[none, "unrelated_lines"] = True
    fids = sel.feature_id.values
    L = _inflate(W, L, fids, sig)
    z0 = _zone_map(L).reindex(fids).fillna("FRONT").values
    other = np.array([rng.choice([z for z in ("FRONT", "REAR", "LEFT", "RIGHT") if z != a]) for a in z0], dtype=object)
    add = sig.unrelated_lines.values | sig.late_supplement.values
    L = _new_lines(W, L, fids[add], np.where(sig.unrelated_lines.values[add], other[add], z0[add]),
                   rng.integers(1, 4, add.sum()), sig.late_supplement.values[add], rng.integers(9, 26, add.sum()))
    W.t["estimate_lines"] = L
    W.truth_add(name, "FEATURE", fids, sig, role="padded_estimate")


def prior_damage(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "SOFT_PRIOR_DAMAGE"), "SOFT_PRIOR_DAMAGE"
    L, F, C = W.table("estimate_lines"), W.table("features"), W.table("claims")
    E = _eligible_features(W, ["COLL", "COMP"], fraud_claims)
    E = E[(E.coverage == "COLL") | (E.subtype == "WEATHER")]
    E = E[E.feature_id.isin(L.feature_id) & ~E.feature_id.isin(W.truth[-1].entity_id if W.truth else [])]
    n = int(len(E) * sc["prevalence"])
    sel = E.sample(n, random_state=int(rng.integers(1e9)))
    sig = W.signals(name, n)
    fids = sel.feature_id.values
    zmap = _zone_map(L)
    z0 = zmap.reindex(fids).values
    # same-zone prior claim: vehicle had an earlier claim; reuse that claim's zone
    cpos = pd.Series(np.arange(len(C)), index=C.claim_id)
    veh = C.vehicle_id.values[cpos.reindex(sel.claim_id).values]
    ld = C.loss_datetime.values[cpos.reindex(sel.claim_id).values]
    prev = C[C.vehicle_id.isin(veh)][["claim_id", "vehicle_id", "loss_datetime"]]
    pf = F[F.claim_id.isin(prev.claim_id)][["claim_id", "feature_id"]].merge(prev, on="claim_id")
    pf["zone"] = zmap.reindex(pf.feature_id).values
    z2 = np.array([rng.choice([z for z in ("FRONT", "REAR", "LEFT", "RIGHT", "TOP") if z != a]) for a in z0], dtype=object)
    has_prior = np.zeros(n, bool)
    for j in np.where(sig.same_zone_prior_claim.values)[0]:
        q = pf[(pf.vehicle_id == veh[j]) & (pf.loss_datetime < ld[j]) & pf.zone.notna() & (pf.zone != "SUBLET") & (pf.zone != "GLASS")]
        if len(q):
            z2[j] = q.zone.values[-1]; has_prior[j] = True
    sig["same_zone_prior_claim"] = has_prior
    add = sig.second_impact_zone.values | has_prior
    sig.loc[~add, "second_impact_zone"] = True
    L = _new_lines(W, L, fids, z2, rng.integers(2, 5, n), np.zeros(n, bool), np.zeros(n))
    wear = sig.wear_language_in_notes.values
    cids = sel.claim_id.values
    zone_word = {"FRONT": "front end", "REAR": "rear", "LEFT": "driver side", "RIGHT": "passenger side", "TOP": "roof"}
    note = pd.Series([f" Insured also reports {zone_word.get(z, 'additional')} damage from same incident." +
                      (" Appraiser noted rust/oxidation at damaged area." if w else "") for z, w in zip(z2, wear)], index=cids)
    mm = C.claim_id.isin(cids)
    C.loc[mm, "description"] = C.loc[mm, "description"].values + note.reindex(C.loc[mm, "claim_id"]).values
    W.t["estimate_lines"], W.t["claims"] = L, C
    W.truth_add(name, "FEATURE", fids, sig, role="prior_damage_added")


def buildup(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "SOFT_INJURY_BUILDUP"), "SOFT_INJURY_BUILDUP"
    F, B, C, L = W.table("features"), W.table("medical_bills"), W.table("claims"), W.table("estimate_lines")
    E = _eligible_features(W, ["BI", "PIP", "UMBI"], fraud_claims)
    E = E[E.feature_id.isin(B.feature_id)]
    n = int(len(E) * sc["prevalence"])
    sel = E.sample(n, random_state=int(rng.integers(1e9)))
    sig = W.signals(name, n)
    sig.loc[~sig.any(axis=1), "excess_chiro_pt"] = True
    fids = sel.feature_id.values
    fpos = pd.Series(F.index, index=F.feature_id)
    # early attorney
    ea = sig.early_attorney.values
    idx = fpos.reindex(fids[ea]).values
    noatt = F.loc[idx, "attorney_party_id"].values == ""
    from .claims import ClaimFactory
    fac = ClaimFactory(W)
    cpos = pd.Series(np.arange(len(C)), index=C.claim_id)
    metro = C._metro.values[cpos.reindex(F.loc[idx, "claim_id"]).values]
    newatt = fac._party("ATTORNEY", metro)
    F.loc[idx, "attorney_party_id"] = np.where(noatt, newatt, F.loc[idx, "attorney_party_id"].values)
    F.loc[idx, "_att_days"] = rng.uniform(1, 6, len(idx))
    bi_new = idx[noatt & np.isin(F.loc[idx, "coverage"].values, ["BI", "UMBI"])]
    F.loc[bi_new, "_gd"] = F.loc[bi_new, "_gd"].values * W.cfg["severity"]["attorney_severity_mult"] ** 0.5
    # extra therapy, MRI on soft tissue
    rows = []
    last = B.groupby("feature_id").service_date.max()
    prov = B.drop_duplicates(["feature_id"]).set_index("feature_id").provider_party_id
    clm = F.set_index("feature_id").claim_id
    cl = F.set_index("feature_id").claimant_id
    for f, ex, mri in zip(fids, sig.excess_chiro_pt.values, sig.mri_soft_tissue.values):
        d0 = last.get(f)
        if ex:
            k = rng.integers(10, 24)
            code = "CHIRO" if rng.random() < 0.6 else "PT"
            lo, hi = R.MED_SERVICES[code][1], R.MED_SERVICES[code][2]
            for j in range(k):
                rows.append((f, code, R.MED_SERVICES[code][0], d0 + np.timedelta64(int(3 + j * rng.integers(2, 4)), "D"), rng.uniform(lo, hi) * 1.15))
        if mri:
            rows.append((f, "MRI", R.MED_SERVICES["MRI"][0], d0 + np.timedelta64(int(rng.integers(5, 20)), "D"), rng.uniform(1400, 2800)))
    if rows:
        N = pd.DataFrame(rows, columns=["feature_id", "service_code", "service_desc", "service_date", "billed_amount"])
        N["billed_amount"] = N.billed_amount.round(2)
        N["allowed_amount"] = np.round(N.billed_amount * np.where(F.set_index("feature_id").coverage.reindex(N.feature_id).values == "PIP", rng.uniform(0.75, 0.92, len(N)), 1.0), 2)
        N["provider_party_id"] = prov.reindex(N.feature_id).values
        tp = N.service_code.map({k: v[3] for k, v in R.MED_SERVICES.items()})
        same_type = B.drop_duplicates(["feature_id", "service_code"]).set_index(["feature_id", "service_code"]).provider_party_id
        sp = same_type.reindex(pd.MultiIndex.from_arrays([N.feature_id, N.service_code])).values
        newp = fac._party("CHIRO", C._metro.values[cpos.reindex(clm.reindex(N.feature_id)).values])
        N["provider_party_id"] = np.where(pd.isna(sp), newp, sp)
        N["claim_id"] = clm.reindex(N.feature_id).values
        N["claimant_id"] = cl.reindex(N.feature_id).values
        N["units"] = 1
        N["diagnosis_group"] = F.set_index("feature_id").injury_type.reindex(N.feature_id).values
        N["_genuine_allowed"] = 0.0
        B = pd.concat([B, N], ignore_index=True)
    # treatment gap: push later visits out
    tg = set(fids[sig.treatment_gap.values])
    mm = B.feature_id.isin(tg) & B.service_code.isin(["CHIRO", "PT", "EM"])
    B = B.sort_values(["feature_id", "service_date"], kind="stable")
    rank = B.groupby("feature_id").cumcount()
    shift = mm & (rank >= 2)
    B.loc[shift, "service_date"] = B.loc[shift, "service_date"] + pd.to_timedelta(
        pd.Series(rng.integers(35, 70, len(B)), index=B.index).groupby(B.feature_id).transform("first")[shift], "D")
    # low impact, high injury: property damage on the same claim is minor
    lih = sel.claim_id.values[sig.low_impact_high_injury.values]
    lm = L.feature_id.isin(F[F.claim_id.isin(lih) & F.coverage.isin(["COLL", "PD", "UMPD"])].feature_id)
    for c in ("part_amount", "body_labor_hours", "refinish_hours"):
        L.loc[lm, c] = np.round(L.loc[lm, c] * 0.35, 2)
    L.loc[lm, "line_amount"] = np.round(L.loc[lm, "line_amount"] * 0.35, 2)
    L.loc[lm, "_genuine_amount"] = L.loc[lm, "line_amount"]
    W.t["features"], W.t["medical_bills"], W.t["estimate_lines"] = F, B, L
    W.truth_add(name, "FEATURE", fids, sig, role="injury_buildup")


def bodyshop_ring(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "RING_BODYSHOP_HOUSTON"), "RING_BODYSHOP_HOUSTON"
    m = sc["geo"][0]
    ring = "RING-HOU-BODYSHOP"
    shops = new_parties(W, "BODY_SHOP", m, sc["shops"], ring, labor_rate=79.0)
    tow = new_parties(W, "TOW", m, 1, ring)[0]
    E_ = W.t["employees"]
    cand = E_[(E_.office_metro == m) & (E_.role == "ADJUSTER")]
    if not len(cand):
        cand = E_[(E_.office_state == R.METROS[m][0]) & (E_.role == "ADJUSTER")]
    appraiser = cand.employee_id.values[0]
    L, F, C = W.table("estimate_lines"), W.table("features"), W.table("claims")
    E = _eligible_features(W, ["COLL", "PD"], fraud_claims, metro=[m], window=sc["window"])
    E = E[E.feature_id.isin(L.feature_id) & (E.subtype != "PROPERTY")]
    cpos = pd.Series(np.arange(len(C)), index=C.claim_id)
    d = C.loss_datetime.values[cpos.reindex(E.claim_id).values].astype("datetime64[D]").astype(int)
    w0, w1 = d2i(sc["window"][0]), d2i(sc["window"][1])
    ramp = 0.25 + 1.5 * (d - w0) / (w1 - w0)            # the shop's share grows over the window
    steer = rng.random(len(E)) < sc["steer_share"] * ramp
    sel = E[steer]
    n = len(sel)
    sig = W.signals(name, n)
    fids = sel.feature_id.values
    F.loc[F.feature_id.isin(fids), "repairer_party_id"] = pd.Series(shops[rng.integers(0, len(shops), n)], index=fids).reindex(
        F.loc[F.feature_id.isin(fids), "feature_id"]).values
    lm = L.feature_id.isin(fids) & (L.operation != "SUBLET")
    L.loc[lm, "labor_rate"] = 79.0; L.loc[lm, "paint_rate"] = 77.0
    _recalc(L, lm.values)
    L = _inflate(W, L, fids, sig.rename(columns={}), labor_mult=(1.4, 1.9))
    sp = sig.supplement.values
    z0 = _zone_map(L).reindex(fids).values
    L = _new_lines(W, L, fids[sp], z0[sp], rng.integers(2, 6, sp.sum()), np.ones(sp.sum(), bool), rng.integers(7, 30, sp.sum()))
    at = sig.affiliated_tow.values
    tm = L.feature_id.isin(fids[at]) & L.part_name.isin(["Towing", "Storage (per day)"])
    L.loc[tm, "vendor_party_id"] = tow
    st = L.feature_id.isin(fids[at]) & (L.part_name == "Storage (per day)")
    L.loc[st, "quantity"] = rng.integers(9, 30, st.sum())
    L.loc[st, "line_amount"] = np.round(L.loc[st, "quantity"] * rng.uniform(65, 95, st.sum()), 2)
    L.loc[st, "part_amount"] = L.loc[st, "line_amount"]
    ap = sel.claim_id.values[sig.same_appraiser.values]
    C.loc[C.claim_id.isin(ap), "adjuster_id"] = appraiser
    W.t["estimate_lines"], W.t["features"], W.t["claims"] = L, F, C
    W.truth_add(name, "FEATURE", fids, sig, ring_id=ring, role="steered_inflated_repair")
    W.truth_add_raw(name, "PARTY", list(shops) + [tow], ring, role="ring_shop_or_tow")
    W.truth_add_raw(name, "EMPLOYEE", [appraiser], ring, role="colluding_appraiser")
    W.storylines[ring] = {"title": "Houston body-shop ring with an inside appraiser", "scenario": name, "parties": list(shops) + [tow],
                          "employee": appraiser}


def tow_ring(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "RING_TOW_STORAGE_PHILLY"), "RING_TOW_STORAGE_PHILLY"
    m = sc["geo"][0]
    ring = "RING-PHI-TOW"
    tows = new_parties(W, "TOW", m, sc["tow_companies"], ring)
    shop = new_parties(W, "BODY_SHOP", m, 1, ring, labor_rate=74.0)[0]
    L, F = W.table("estimate_lines"), W.table("features")
    E = _eligible_features(W, ["COLL", "COMP"], fraud_claims, metro=[m], window=sc["window"])
    towed = set(L[L.part_name == "Towing"].feature_id)
    E = E[E.feature_id.isin(towed)]
    sel = E[rng.random(len(E)) < sc["capture_share"]]
    n = len(sel)
    sig = W.signals(name, n)
    fids = sel.feature_id.values
    tv = pd.Series(tows[rng.integers(0, len(tows), n)], index=fids)
    tm = L.feature_id.isin(fids) & L.part_name.isin(["Towing", "Storage (per day)"])
    L.loc[tm, "vendor_party_id"] = tv.reindex(L.loc[tm, "feature_id"]).values
    hi = L.feature_id.isin(fids[sig.above_market_tow_rate.values]) & (L.part_name == "Towing")
    L.loc[hi, "line_amount"] = np.round(L.loc[hi, "line_amount"] * rng.uniform(2.5, 4.2, hi.sum()), 2)
    L.loc[hi, "part_amount"] = L.loc[hi, "line_amount"]
    xs = fids[sig.excess_storage_days.values]
    st = L.feature_id.isin(xs) & (L.part_name == "Storage (per day)")
    L.loc[st, "quantity"] = rng.integers(15, 46, st.sum())
    L.loc[st, "line_amount"] = np.round(L.loc[st, "quantity"] * rng.uniform(85, 125, st.sum()), 2)
    L.loc[st, "part_amount"] = L.loc[st, "line_amount"]
    missing = set(xs) - set(L[st].feature_id)
    if missing:
        ref = L[L.feature_id.isin(missing) & (L.part_name == "Towing")].drop_duplicates("feature_id")
        N = ref.copy()
        N["part_name"] = "Storage (per day)"; N["quantity"] = rng.integers(15, 46, len(N))
        N["line_amount"] = np.round(N.quantity * rng.uniform(85, 125, len(N)), 2); N["part_amount"] = N.line_amount
        N["_genuine_amount"] = 0.0
        L = pd.concat([L, N], ignore_index=True)
    un = fids[sig.unauthorized_tow_to_affiliate_shop.values]
    F.loc[F.feature_id.isin(un), "repairer_party_id"] = shop
    lm = L.feature_id.isin(un) & (L.operation != "SUBLET")
    L.loc[lm, "labor_rate"] = 74.0
    L.loc[lm, "body_labor_hours"] = np.round(L.loc[lm, "body_labor_hours"] * 1.2, 1)
    _recalc(L, lm.values)
    W.t["estimate_lines"], W.t["features"] = L, F
    W.truth_add(name, "FEATURE", fids, sig, ring_id=ring, role="captured_tow")
    W.truth_add_raw(name, "PARTY", list(tows) + [shop], ring, role="ring_tow_or_shop")
    W.storylines[ring] = {"title": "Philadelphia tow-and-storage ring", "scenario": name, "parties": list(tows) + [shop]}


def late_report(W, fraud_claims):
    rng, sc, name = W.rng, _sc(W, "BENIGN_LATE_REPORT_HOSPITALIZED"), "BENIGN_LATE_REPORT_HOSPITALIZED"
    F, C = W.table("features"), W.table("claims")
    late_ok = C[C.loss_datetime < np.datetime64(W.cfg["run"]["as_of_date"]) - np.timedelta64(45, "D")].claim_id
    cids = F[F.coverage.isin(["PIP", "MEDPAY", "UMBI"]) & ~F.claim_id.isin(fraud_claims) & F.claim_id.isin(late_ok)].claim_id.unique()
    n = int(len(cids) * sc["prevalence"])
    sel = rng.choice(cids, n, replace=False)
    m = C.claim_id.isin(sel)
    lag = rng.uniform(10, 40, m.sum())
    C.loc[m, "report_datetime"] = C.loc[m, "loss_datetime"].values + (lag * 1440).astype(int).astype("timedelta64[m]")
    C.loc[m, "description"] = C.loc[m, "description"].values + " Insured was hospitalized and reported the claim after discharge."
    W.t["claims"] = C
    W.truth_add(name, "CLAIM", sel, None, role="late_report_hospitalized")


# =============================================================================
# POST-SETTLE leakage
# =============================================================================
def post_settle(W):
    rng = W.rng
    F = W.table("features")
    if _on(W, "LEAK_DEDUCTIBLE_NOT_APPLIED"):
        sc = _sc(W, "LEAK_DEDUCTIBLE_NOT_APPLIED")
        e = F.index[F.coverage.isin(["COLL", "COMP"]) & (F.deductible_applied > 0) & (F._paid_full > 0)]
        s = rng.choice(e, int(len(e) * sc["prevalence"]), replace=False)
        F["_leak_deductible"] = False
        F.loc[s, "_leak_deductible"] = True
        W.truth_add("LEAK_DEDUCTIBLE_NOT_APPLIED", "FEATURE", F.loc[s, "feature_id"].values, ["deductible_zero_on_paid"] * len(s),
                    excess_amount=F.loc[s, "deductible_applied"].values)
    if _on(W, "LEAK_MISSED_SUBROGATION"):
        sc = _sc(W, "LEAK_MISSED_SUBROGATION")
        e = F.index[F.subrogation_potential & (F._paid_full > 0)]
        s = rng.choice(e, int(len(e) * sc["prevalence"]), replace=False)
        sig = W.signals("LEAK_MISSED_SUBROGATION", len(s))
        F["_leak_subro"] = False
        F.loc[s, "_leak_subro"] = True
        lost = np.where(F.loc[s, "subrogation_recovery"].values > 0, F.loc[s, "subrogation_recovery"].values,
                        np.round(F.loc[s, "_paid_full"].values * 0.85, 2))
        W.truth_add("LEAK_MISSED_SUBROGATION", "FEATURE", F.loc[s, "feature_id"].values, sig, excess_amount=lost)
    if _on(W, "LEAK_SALVAGE_NOT_RECOVERED"):
        sc = _sc(W, "LEAK_SALVAGE_NOT_RECOVERED")
        e = F.index[F.salvage_recovery > 0]
        s = rng.choice(e, int(len(e) * sc["prevalence"]), replace=False)
        F["_leak_salvage"] = False
        F.loc[s, "_leak_salvage"] = True
        W.truth_add("LEAK_SALVAGE_NOT_RECOVERED", "FEATURE", F.loc[s, "feature_id"].values, ["total_loss_no_salvage"] * len(s),
                    excess_amount=F.loc[s, "salvage_recovery"].values)
    W.t["features"] = F


# =============================================================================
# POST-PAY
# =============================================================================
def post_pay(W):
    rng = W.rng
    Pm = W.t["payments"]
    if _on(W, "LEAK_DUPLICATE_PAYMENT"):
        sc = _sc(W, "LEAK_DUPLICATE_PAYMENT")
        e = Pm.index[(Pm.status != "VOIDED") & (Pm.amount > 150)]
        s = rng.choice(e, int(len(e) * sc["prevalence"]), replace=False)
        sig = W.signals("LEAK_DUPLICATE_PAYMENT", len(s))
        D = Pm.loc[s].copy()
        D["payment_id"] = W.ids.take("PAY", len(D), 9)
        D["issue_date"] = D.issue_date.values + np.where(sig.within_14_days.values, rng.integers(1, 15, len(D)), rng.integers(15, 45, len(D))).astype("timedelta64[D]")
        D["issue_date"] = np.minimum(D.issue_date.values.astype("datetime64[D]"), np.datetime64(W.cfg["run"]["as_of_date"]))
        Pm = pd.concat([Pm, D], ignore_index=True)
        W.truth_add("LEAK_DUPLICATE_PAYMENT", "PAYMENT", D.payment_id.values, sig, excess_amount=D.amount.values,
                    original_payment_id=Pm.loc[s, "payment_id"].values)
    if _on(W, "INTERNAL_ADJUSTER_DIVERSION"):
        sc = _sc(W, "INTERNAL_ADJUSTER_DIVERSION")
        m = sc["geo"][0]
        E = W.t["employees"]
        cand = E[(E.office_metro == m) & (E.role == "ADJUSTER")]
        if not len(cand):
            cand = E[(E.office_state == R.METROS[m][0]) & (E.role == "ADJUSTER")]
        emp = cand.iloc[0]
        linked = rng.random() < sc["signals"]["vendor_linked_to_employee"]
        vendor = new_parties(W, "VENDOR", m, 1, "INTERNAL-DAL")[0]
        P = W.t["parties"]
        vi = P.index[P.party_id == vendor]
        P.loc[vi, "established_date"] = pd.to_datetime(sc["window"][0]) - pd.Timedelta(days=21)
        if linked:
            P.loc[vi, ["address", "zip"]] = [emp.home_address, emp.home_zip]
        C, F = W.table("claims"), W.table("features")
        d = C.loss_datetime.values.astype("datetime64[D]").astype(int)
        pool = C[(C._metro == m) & (d >= d2i(sc["window"][0])) & (d <= d2i(sc["window"][1])) & (C.claim_status != "DENIED")]
        n = _n(W, sc["payments"])
        chosen = pool.sample(min(n * 2 // 3, len(pool)), random_state=int(rng.integers(1e9))).claim_id.values
        C.loc[C.claim_id.isin(chosen), "adjuster_id"] = emp.employee_id
        Pm.loc[Pm.claim_id.isin(chosen), ["issued_by"]] = emp.employee_id
        cl = rng.choice(chosen, n)
        sig = W.signals("INTERNAL_ADJUSTER_DIVERSION", n)
        sig["vendor_linked_to_employee"] = linked
        sig["new_vendor_low_volume"] = True
        lim = emp.authority_limit
        amt = np.where(sig.just_below_authority.values, lim * rng.uniform(0.86, 0.995, n), rng.uniform(1800, 9500, n))
        cp = pd.Series(np.arange(len(C)), index=C.claim_id).reindex(cl).values
        rep = C.report_datetime.values[cp].astype("datetime64[D]")
        clo = C.closed_date.values[cp]
        after = sig.payment_after_closure.values & ~pd.isna(clo)
        base = np.where(after, pd.to_datetime(clo).values.astype("datetime64[D]"), rep)
        dates = base + rng.integers(5, 60, n).astype("timedelta64[D]")
        dates = np.minimum(dates, np.datetime64(W.cfg["run"]["as_of_date"]))
        fid = F.drop_duplicates("claim_id").set_index("claim_id").feature_id.reindex(cl).values
        D = pd.DataFrame({"payment_id": W.ids.take("PAY", n, 9), "claim_id": cl, "feature_id": fid, "payee_type": "VENDOR",
                          "payee_id": vendor, "amount": np.round(amt, 2), "issue_date": dates, "payment_method": "EFT",
                          "payee_bank_account_token": P.loc[vi, "bank_account_token"].values[0], "payee_name": P.loc[vi, "name"].values[0],
                          "payment_category": "EXPENSE", "issued_by": emp.employee_id, "approved_by": emp.employee_id, "status": "CLEARED"})
        Pm = pd.concat([Pm, D], ignore_index=True)
        W.t["claims"] = C
        W.truth_add("INTERNAL_ADJUSTER_DIVERSION", "PAYMENT", D.payment_id.values, sig, ring_id="INTERNAL-DAL",
                    excess_amount=D.amount.values)
        W.truth_add_raw("INTERNAL_ADJUSTER_DIVERSION", "EMPLOYEE", [emp.employee_id], "INTERNAL-DAL", role="diverting_adjuster")
        W.truth_add_raw("INTERNAL_ADJUSTER_DIVERSION", "PARTY", [vendor], "INTERNAL-DAL", role="shell_vendor")
        W.storylines["INTERNAL-DAL"] = {"title": "Dallas adjuster paying a shell vendor", "scenario": "INTERNAL_ADJUSTER_DIVERSION",
                                        "employee": emp.employee_id, "parties": [vendor]}
    W.t["payments"] = Pm
