"""Genuine claim events drawn from the exposure table."""
import numpy as np
import pandas as pd
from .claims import ClaimFactory


def sample_days(rng, start, end, season, n_try=6):
    span = np.maximum(end - start, 1)
    day = start + (rng.random(len(start)) * span).astype(int)
    smax = max(season)
    s = np.array(season)
    for _ in range(n_try):
        m = ((day.astype("datetime64[D]").astype("datetime64[M]").astype(int)) % 12)
        rej = rng.random(len(day)) > s[m] / smax
        if not rej.any():
            break
        day[rej] = start[rej] + (rng.random(rej.sum()) * span[rej]).astype(int)
    return day


def hours(rng, profile, n, night=None):
    p = np.array(profile, dtype=float); p /= p.sum()
    h = rng.choice(24, n, p=p)
    if night is not None and night.any():
        night_p = np.array([3, 3, 2.5, 2, 1, .5, .3, .3, .3, .3, .3, .3, .3, .3, .3, .5, .6, .8, 1, 1.5, 2, 2.5, 3, 3.2])
        h[night] = rng.choice(24, night.sum(), p=night_p / night_p.sum())
    return h


def generate(W):
    rng, cfg = W.rng, W.cfg
    fq = cfg["frequency"]
    vt = W.t["vt"]
    n = len(vt)
    e = vt.exp_years.values
    fr = vt.frailty.values
    up_l = vt["_uplift_liab"].values if "_uplift_liab" in vt else np.ones(n)
    up_c = vt["_uplift_coll"].values if "_uplift_coll" in vt else np.ones(n)
    has_comp = ~np.isnan(vt.comp_deductible.values)
    specs = []

    def draw(rate, kind):
        k = rng.poisson(rate)
        idx = np.repeat(np.arange(n), k)
        return idx

    af = draw(fq["at_fault_accident"] * vt.rel_liab.values * fr * up_l * e, "AF")
    naf = draw(fq["not_at_fault_accident"] * vt.rel_liab.values ** 0.6 * fr ** 0.5 * up_c * e, "NAF")
    comp = {}
    for c, key, rel in [("GLASS", "comp_glass", vt.rel_comp.values), ("THEFT", "comp_theft", vt.rel_theft.values),
                        ("WEATHER", "comp_weather", vt.rel_comp.values), ("ANIMAL", "comp_animal", 1 / np.maximum(vt.rel_comp.values, 0.6)),
                        ("VANDALISM", "comp_vandalism", vt.rel_comp.values ** 1.5), ("FIRE", "comp_fire", np.ones(n)),
                        ("FLOOD", "comp_flood", np.ones(n))]:
        comp[c] = draw(fq[key] * rel * np.where(has_comp, 1.0, 0.0) * e, c)

    def base_spec(idx, cause):
        m = len(idx)
        d = sample_days(rng, vt.term_start.values[idx], vt.exp_end.values[idx], fq["monthly_seasonality"])
        return pd.DataFrame({"vt_idx": idx, "cause": cause, "loss_day": d,
                             "loss_hour": hours(rng, fq["hourly_profile"], m, night=np.isin(cause, ["THEFT", "VANDALISM"]) if isinstance(cause, np.ndarray) else None)})

    multi = rng.random(len(af)) < fq["at_fault_multi_vehicle_share"]
    s = base_spec(af, np.where(multi, "AF_MULTI", "AF_SINGLE"))
    s["n_tp_injured"] = np.where(multi & (rng.random(len(s)) < fq["tp_bi_given_multi_vehicle"]), 1 + rng.binomial(2, 0.22, len(s)), 0)
    s["n_ins_injured"] = np.where(rng.random(len(s)) < fq["insured_injury_given_accident"] * np.where(multi, 1, 0.7), 1 + rng.binomial(2, 0.12, len(s)), 0)
    s["want_pd"] = multi | (rng.random(len(s)) < 0.30)
    s["want_coll"] = rng.random(len(s)) < 0.92
    specs.append(s)
    unins = rng.random(len(naf)) < fq["uninsured_other_party"]
    s = base_spec(naf, np.where(unins, "NAF_UNINSURED", "NAF"))
    s["n_ins_injured"] = np.where(rng.random(len(s)) < fq["insured_injury_given_accident"], 1 + rng.binomial(2, 0.12, len(s)), 0)
    s["want_coll"] = unins | (rng.random(len(s)) < fq["nafa_first_party_claim_prob"])
    specs.append(s)
    for c, idx in comp.items():
        s = base_spec(idx, np.array([c] * len(idx), dtype=object))
        specs.append(s)
    spec = pd.concat(specs, ignore_index=True)
    spec = apply_policy_overrides(W, spec)
    fac = ClaimFactory(W)
    # chunk to keep memory flat
    out = []
    for lo in range(0, len(spec), 60000):
        out.append(fac.create(spec.iloc[lo:lo + 60000], tag="BASELINE"))
    return fac


def apply_policy_overrides(W, spec):
    """Claims on misrepresented policies carry the scenario's fingerprints (operator, timing, passengers)."""
    rng = W.rng
    vt = W.t["vt"]
    v = vt.iloc[spec.vt_idx.values]
    acc = spec.cause.isin(["AF_MULTI", "AF_SINGLE", "NAF", "NAF_UNINSURED"]).values
    # unlisted driver operates a share of the accident claims
    if "_unlisted_driver" in vt:
        ud = v._unlisted_driver.values
        m = acc & (ud != "") & (rng.random(len(spec)) < 0.58)
        spec["operator_unlisted"] = m
        spec["_unlisted_driver"] = np.where(m, ud, "")
    # rideshare vehicles: night/weekend losses, paying passengers, venue/airport locations
    if "_rideshare_sig" in vt:
        rs = v._rideshare_sig.values
        m = acc & (rs != "")
        if m.any():
            night = m & np.array(["night_weekend_loss" in x for x in rs])
            spec.loc[night, "loss_hour"] = hours(rng, W.cfg["frequency"]["hourly_profile"], night.sum(), night=np.ones(night.sum(), bool))
            pas = m & np.array(["unrelated_passengers" in x for x in rs])
            spec["n_occupants"] = np.where(pas, rng.integers(2, 5, len(spec)), np.nan)
            spec.loc[pas, "n_ins_injured"] = np.where(rng.random(pas.sum()) < 0.45, rng.integers(1, 3, pas.sum()), spec.loc[pas, "n_ins_injured"])
            ven = m & np.array(["airport_or_venue_location" in x for x in rs])
            spec["location_type"] = np.where(ven, np.where(rng.random(len(spec)) < 0.5, "AIRPORT_PICKUP_ZONE", "ENTERTAINMENT_VENUE"), "")
    # garaging misrep: some losses happen near the declared garage
    if "_garaging_sig" in vt:
        gs = v._garaging_sig.values
        m = (gs != "") & np.array(["loss_far_from_garaging" not in x for x in gs])
        spec["loss_metro"] = np.where(m, v.metro_declared.values, "")
    return spec
