"""Book of business: producers, employees, service providers, households, drivers,
vehicles, policy terms, and the vehicle-term exposure table claims are drawn from."""
import numpy as np
import pandas as pd
from . import refdata as R
from .util import d2i, pick, band_lookup, make_vins, token


def build_producers(W):
    rng, cfg = W.rng, W.cfg
    n_agents = max(60, int(cfg["run"]["target_policy_terms"] / 900))
    metro = W.geo.sample_metros(n_agents)
    kind = np.where(rng.random(n_agents) < 0.5, "CAPTIVE_AGENT", "INDEPENDENT_AGENT")
    g = np.where(rng.random(n_agents) < 0.55, "M", "F")
    by = rng.integers(1955, 1995, n_agents)
    f, m, l, s = W.names.people(g, by)
    agency = [W.biz.make("AGENCY", R.METROS[mm][1]) for mm in metro]
    df = pd.DataFrame({
        "producer_id": W.ids.take("PRD", n_agents, 5), "channel": kind,
        "agency_name": agency, "agent_first_name": f, "agent_last_name": l,
        "metro": metro, "state": W.geo.state(metro), "city": W.geo.city(metro),
        "phone": W.geo.phone(metro),
        "appointed_date": pd.to_datetime("2000-01-01") + pd.to_timedelta(rng.integers(0, 8400, n_agents), "D"),
        "status": "ACTIVE",
    })
    direct = pd.DataFrame({"producer_id": ["PRD-DIRECT", "PRD-CALLCTR"], "channel": ["DIRECT_ONLINE", "CALL_CENTER"],
                           "agency_name": [f"{cfg['company']['short']} Direct (web/app)", f"{cfg['company']['short']} Call Center"],
                           "agent_first_name": "", "agent_last_name": "", "metro": "", "state": "", "city": "",
                           "phone": "(800) 555-0142", "appointed_date": pd.to_datetime("1987-01-01"), "status": "ACTIVE"})
    W.t["producers"] = pd.concat([direct, df], ignore_index=True)


def build_employees(W):
    rng = W.rng
    n = max(80, int(W.cfg["run"]["target_policy_terms"] / 1700))
    metro = W.geo.sample_metros(n)
    role = pick(rng, {"CLAIMS_REP": 0.38, "ADJUSTER": 0.34, "SENIOR_ADJUSTER": 0.16, "CLAIMS_MANAGER": 0.06, "SIU_INVESTIGATOR": 0.06}, n)
    limit = pd.Series(role).map({"CLAIMS_REP": 7500, "ADJUSTER": 25000, "SENIOR_ADJUSTER": 75000,
                                 "CLAIMS_MANAGER": 250000, "SIU_INVESTIGATOR": 0}).values
    g = np.where(rng.random(n) < 0.5, "M", "F")
    f, m, l, s = W.names.people(g, rng.integers(1960, 2000, n))
    z, _ = W.geo.sample_zip(metro)
    W.t["employees"] = pd.DataFrame({
        "employee_id": W.ids.take("EMP", n, 5), "first_name": f, "last_name": l, "role": role,
        "office_metro": metro, "office_state": W.geo.state(metro), "authority_limit": limit,
        "hire_date": pd.to_datetime("2004-01-01") + pd.to_timedelta(rng.integers(0, 7000, n), "D"),
        "home_address": W.geo.street(n), "home_zip": z,
    })


PARTY_DENSITY = {  # parties per metro = base + weight * scale
    "BODY_SHOP": (6, 700), "TOW": (3, 260), "GLASS": (2, 70), "HOSPITAL": (2, 60), "IMAGING": (2, 70),
    "ORTHO": (2, 90), "CHIRO": (3, 150), "PT": (2, 110), "PAIN_MGMT": (1, 40), "PHARMACY": (1, 30),
    "ATTORNEY": (4, 320), "RENTAL": (2, 20),
}


def build_parties(W):
    rng = W.rng
    rows = []
    scale = W.cfg["run"]["target_policy_terms"] / 1_000_000
    for metro in W.geo.keys:
        st, city, w = R.METROS[metro][0], R.METROS[metro][1], R.METROS[metro][2]
        for kind, (base, k) in PARTY_DENSITY.items():
            n = int(base + w * k * scale)
            for _ in range(n):
                rows.append((kind, W.biz.make(kind, city), metro, st, city))
    df = pd.DataFrame(rows, columns=["party_type", "name", "metro", "state", "city"])
    n = len(df)
    df.insert(0, "party_id", W.ids.take("PTY", n, 6))
    df["address"] = W.geo.street(n)
    df["zip"], _ = W.geo.sample_zip(df["metro"].values)
    df["phone"] = W.geo.phone(df["metro"].values)
    df["tax_id"] = [f"{a:02d}-{b:07d}" for a, b in zip(rng.integers(10, 99, n), rng.integers(0, 9999999, n))]
    df["bank_account_token"] = token(rng, "BA", n, 10)
    df["drp_flag"] = np.where(df.party_type == "BODY_SHOP", rng.random(n) < 0.28, False)
    df["labor_rate"] = np.where(df.party_type == "BODY_SHOP",
                                np.round(rng.uniform(52, 72, n) * W.geo.territory(df.metro.values) ** 0.5, 0), np.nan)
    df["established_date"] = pd.to_datetime("1975-01-01") + pd.to_timedelta(rng.integers(0, 16000, n), "D")
    # hidden volume weight (DRP shops and big hospitals get more traffic)
    vol = rng.lognormal(0, 0.6, n)
    vol = np.where(df.drp_flag, vol * 3.5, vol)
    df["_volume"] = vol
    df["_ring"] = ""
    W.t["parties"] = df


def build_households(W):
    rng, cfg = W.rng, W.cfg
    ws, we = d2i(cfg["run"]["window_start"]), d2i(cfg["run"]["window_end"])
    r = cfg["book"]["retention"]
    share = cfg["book"]["initial_book_share"]
    target = cfg["run"]["target_policy_terms"]
    est = share * (1 + r + r * r) + (1 - share) * 1.75
    H = int(target / est * 1.10)
    initial = rng.random(H) < share
    first = np.where(initial, ws + rng.integers(0, 365, H),
                     ws + (np.sqrt(rng.random(H)) * (we - ws)).astype(int))  # mild growth in new business
    max_k = (we - first) // 365 + 1
    k = np.minimum(max_k, rng.geometric(1 - r, H))
    order = rng.permutation(H)
    cum = np.cumsum(k[order])
    keep = order[cum <= target]
    keep.sort()
    initial, first, k, max_k = initial[keep], first[keep], k[keep], max_k[keep]
    H = len(keep)

    metro = W.geo.sample_metros(H)
    zipc, zf = W.geo.sample_zip(metro)
    ni_age = np.clip(rng.normal(47, 15, H), 18, 88).astype(int)
    birth_year = 2023 - ni_age
    g = np.where(rng.random(H) < 0.52, "F", "M")
    f, m, l, s = W.names.people(g, birth_year)
    channel = pick(rng, cfg["book"]["channel_mix"], H)
    prods = W.t["producers"]
    prod = np.where(channel == "DIRECT_ONLINE", "PRD-DIRECT", np.where(channel == "CALL_CENTER", "PRD-CALLCTR", ""))
    for ch in ("CAPTIVE_AGENT", "INDEPENDENT_AGENT"):
        pool = prods[prods.channel == ch]
        for mm in np.unique(metro):
            idx = np.where((channel == ch) & (metro == mm))[0]
            cand = pool[pool.metro == mm].producer_id.values
            if len(cand) == 0:
                cand = pool.producer_id.values
            prod[idx] = cand[rng.integers(0, len(cand), len(idx))]
    email_dom = np.array(R.EMAIL_DOMAINS, dtype=object)[rng.integers(0, len(R.EMAIL_DOMAINS), H)]
    email = [f"{a.lower()}.{c.lower().replace(' ', '')}{(n % 97) if n % 3 else ''}@{d}"
             for a, c, n, d in zip(f, l, rng.integers(0, 10000, H), email_dom)]
    hh = pd.DataFrame({
        "customer_id": W.ids.take("CUS", H, 7),
        "first_name": f, "middle_name": m, "last_name": l, "suffix": s, "gender": g,
        "date_of_birth": pd.to_datetime(birth_year.astype(str)) + pd.to_timedelta(rng.integers(0, 365, H), "D"),
        "address": W.geo.street(H), "city": W.geo.city(metro), "state": W.geo.state(metro), "zip": zipc,
        "phone": W.geo.phone(metro), "email": email,
        "credit_tier": pick(rng, cfg["book"]["credit_tier_mix"], H),
        "homeowner": rng.random(H) < cfg["book"]["homeowner_share"],
        "customer_since": pd.NaT, "channel": channel, "producer_id": prod, "metro": metro,
    })
    tenure = np.where(initial, np.clip(rng.geometric(0.16, H), 1, 25), 0)
    hh["customer_since"] = pd.to_datetime("1970-01-01") + pd.to_timedelta(first - tenure * 365, "D")
    hh["_first_start"] = first; hh["_n_terms"] = k; hh["_max_terms"] = max_k; hh["_tenure"] = tenure
    hh["_zip_factor"] = zf
    hh["_true_zip_factor"] = zf
    hh["_frailty"] = rng.gamma(cfg["frequency"]["household_heterogeneity_shape"],
                               1 / cfg["frequency"]["household_heterogeneity_shape"], H)
    hh["_true_metro"] = metro
    hh["_missed_payments"] = rng.poisson(0.25, H)
    # household coverage choices (persist across renewals)
    st = hh.state.values
    bi = pick(rng, cfg["book"]["bi_limit_mix"], H)
    bi = np.where(bi == "STATE_MIN", [R.STATES[x][2] for x in st], bi)
    hh["bi_limit"] = bi
    pd_map = {"10/20": 10000, "15/30": 15000, "25/50": 25000, "30/60": 25000, "50/100": 50000, "100/300": 100000, "250/500": 100000}
    hh["pd_limit"] = np.maximum([pd_map[b] for b in bi], [R.STATES[x][3] for x in st])
    nf = np.array([R.STATES[x][0] for x in st])
    hh["pip_limit"] = [R.STATES[x][1][rng.integers(len(R.STATES[x][1]))] for x in st]
    hh["medpay_limit"] = np.where(~nf & (rng.random(H) < 0.45), 5000, 0)
    hh["um_flag"] = rng.random(H) < 0.72
    hh["payment_plan"] = pick(rng, {"PAID_IN_FULL": 0.28, "MONTHLY_EFT": 0.52, "MONTHLY_CARD": 0.20}, H)
    hh["prior_carrier"] = np.where(initial, "", pick(rng, {"Carrier A": 0.2, "Carrier B": 0.2, "Carrier C": 0.15,
                                                          "Carrier D": 0.15, "Other": 0.2, "NONE": 0.10}, H))
    hh["prior_lapse_days"] = np.where(initial, 0, np.where(rng.random(H) < 0.14, rng.integers(1, 120, H), 0))
    W.t["households"] = hh


def build_drivers(W):
    rng, cfg = W.rng, W.cfg
    hh = W.t["households"]
    H = len(hh)
    ni = pd.DataFrame({"customer_id": hh.customer_id.values, "relationship": "NAMED_INSURED",
                       "first_name": hh.first_name.values, "middle_name": hh.middle_name.values,
                       "last_name": hh.last_name.values, "suffix": hh.suffix.values, "gender": hh.gender.values,
                       "date_of_birth": hh.date_of_birth.values})
    n_extra = pick(rng, cfg["book"]["extra_drivers"], H).astype(int)
    ni_age = 2023 - hh.date_of_birth.dt.year.values
    rows_hh = np.repeat(np.arange(H), n_extra)
    pos = np.concatenate([np.arange(k) for k in n_extra]) if len(rows_hh) else np.array([], int)
    a = ni_age[rows_hh]
    rel = np.where((pos == 0) & (a >= 22) & (rng.random(len(rows_hh)) < 0.78), "SPOUSE",
                   np.where(a >= 38, "CHILD", "OTHER"))
    age = np.where(rel == "SPOUSE", np.clip(a + rng.integers(-6, 7, len(a)), 18, 90),
                   np.where(rel == "CHILD", rng.integers(16, 26, len(a)), rng.integers(18, 80, len(a))))
    by = 2023 - age
    gni = hh.gender.values[rows_hh]
    gx = np.where(rel == "SPOUSE", np.where(gni == "M", "F", "M"), np.where(rng.random(len(a)) < 0.5, "M", "F"))
    share_surname = (rel == "CHILD") | ((rel == "SPOUSE") & (rng.random(len(a)) < 0.80))
    sur = np.where(share_surname, hh.last_name.values[rows_hh].astype(str), W.names.surnames(len(a)))
    sur = np.array([x.upper() for x in sur], dtype=object)
    f, m, l, s = W.names.people(gx, by, surname=sur)
    ex = pd.DataFrame({"customer_id": hh.customer_id.values[rows_hh], "relationship": rel, "first_name": f,
                       "middle_name": m, "last_name": l, "suffix": s, "gender": gx,
                       "date_of_birth": pd.to_datetime(by.astype(str)) + pd.to_timedelta(rng.integers(0, 365, len(a)), "D")})
    dr = pd.concat([ni, ex], ignore_index=True).sort_values(["customer_id", "relationship"], kind="stable")
    n = len(dr)
    dr.insert(0, "driver_id", W.ids.take("DRV", n, 7))
    st_map = hh.set_index("customer_id").state
    dr["license_state"] = st_map.reindex(dr.customer_id).values
    dr["license_number"] = token(rng, "DL", n, 9)
    age16 = dr.date_of_birth + pd.to_timedelta(rng.integers(16 * 365, 19 * 365, n), "D")
    dr["first_licensed_date"] = age16
    young = (2023 - dr.date_of_birth.dt.year.values) < 25
    dr["violations_3yr"] = rng.poisson(np.where(young, 0.35, 0.14))
    dr["at_fault_accidents_3yr"] = rng.poisson(np.where(young, 0.18, 0.07))
    dr["marital_status"] = np.where(dr.relationship == "SPOUSE", "MARRIED", pick(rng, {"MARRIED": 0.5, "SINGLE": 0.42, "DIVORCED": 0.08}, n))
    dr["_listed"] = True
    dr["_address"] = ""
    W.t["drivers"] = dr.reset_index(drop=True)


def build_vehicles(W):
    rng, cfg = W.rng, W.cfg
    hh = W.t["households"]
    H = len(hh)
    nveh = pick(rng, cfg["book"]["vehicles_per_household"], H).astype(int)
    rows = np.repeat(np.arange(H), nveh)
    n = len(rows)
    vw = np.array([v[7] for v in R.VEHICLES]); vw = vw / vw.sum()
    mi = rng.choice(len(R.VEHICLES), n, p=vw)
    age = np.minimum(np.round(rng.gamma(2.0, 3.4, n)), 20).astype(int)
    year = np.clip(2024 - age, 2004, 2025)
    V = R.VEHICLES
    make = np.array([V[i][0] for i in mi], dtype=object); model = np.array([V[i][1] for i in mi], dtype=object)
    body = np.array([V[i][2] for i in mi], dtype=object); seg = np.array([V[i][3] for i in mi], dtype=object)
    msrp = np.array([V[i][4] for i in mi]) * (1 - 0.022 * (2025 - year)) * rng.uniform(0.9, 1.2, n)
    wmi = np.array([V[i][5] for i in mi], dtype=object); adas = np.array([V[i][6] for i in mi])
    vins = make_vins(rng, wmi, year)
    vage = 2024 - year
    lien_p = np.select([vage <= 3, vage <= 7], [0.72, 0.45], 0.08)
    usage = pick(rng, {"COMMUTE": 0.56, "PLEASURE": 0.34, "BUSINESS": 0.10}, n)
    miles = np.round(np.clip(rng.lognormal(np.log(11000), 0.38, n), 2000, 40000), -2)
    ve = pd.DataFrame({
        "vehicle_id": W.ids.take("VEH", n, 7), "customer_id": hh.customer_id.values[rows], "vin": vins,
        "model_year": year, "make": make, "model": model, "body_type": body,"segment": seg,
        "msrp": np.round(msrp, -2), "adas_equipped": year >= adas, "lienholder_flag": rng.random(n) < lien_p,
        "declared_usage": usage, "declared_annual_miles": miles.astype(int),
        "garaging_zip": hh.zip.values[rows],
    })
    ve["_true_usage"] = ve.declared_usage
    ve["_true_miles"] = ve.declared_annual_miles
    ve["_odo_miles"] = ve.declared_annual_miles
    ve["_hh"] = rows
    # coverage
    fc = rng.random(n) < np.where(ve.lienholder_flag, 1.0, (cfg["book"]["full_coverage_share"] - 0.30) / 0.70 + 0.05 - 0.02 * vage)
    co = (~fc) & (rng.random(n) < cfg["book"]["comp_only_share"] / 0.3)
    ve["coll_deductible"] = np.where(fc, pick(rng, cfg["book"]["coll_deductible_mix"], n).astype(float), np.nan)
    ve["comp_deductible"] = np.where(fc | co, pick(rng, cfg["book"]["comp_deductible_mix"], n).astype(float), np.nan)
    ve["rental_coverage"] = fc & (rng.random(n) < 0.45)
    ve["towing_coverage"] = (fc | co) & (rng.random(n) < 0.55)
    W.t["vehicles"] = ve


def build_terms(W):
    rng, cfg = W.rng, W.cfg
    hh = W.t["households"]
    H = len(hh)
    k = hh._n_terms.values
    hrow = np.repeat(np.arange(H), k)
    seq = np.concatenate([np.arange(x) for x in k])
    start = hh._first_start.values[hrow] + seq * 365
    end = start + 365
    n = len(hrow)
    last = seq == (k[hrow] - 1)
    lapsed = last & (k[hrow] < hh._max_terms.values[hrow])  # left before the window ended
    midterm = lapsed & (rng.random(n) < 0.32)
    cancel = np.where(midterm, start + rng.integers(25, 330, n), -1)
    reason = np.where(midterm, pick(rng, {"NONPAY": 0.55, "INSURED_REQUEST": 0.35, "UNDERWRITING": 0.10}, n), "").astype(object)
    if "_force_cancel" in hh:
        fc = hh._force_cancel.values[hrow].astype(float)
        m = ~np.isnan(fc) & (seq == 0)
        cancel = np.where(m, start + np.nan_to_num(fc).astype(int), cancel)
        reason[m] = "NONPAY"
    ghost = hh["_ghost"].fillna(False).astype(bool).values[hrow] if "_ghost" in hh else np.zeros(n, bool)
    rseq = hh._tenure.values[hrow] + seq
    pnum = np.array([f"{cfg['company']['policy_prefix']}-{s}-{i:07d}" for s, i in
                     zip(hh.state.values, np.arange(1, H + 1))], dtype=object)
    t = pd.DataFrame({
        "term_id": W.ids.take("TRM", n, 8), "policy_number": pnum[hrow], "customer_id": hh.customer_id.values[hrow],
        "renewal_seq": rseq, "new_business_flag": rseq == 0,
        "term_start": start, "term_end": end, "cancel_date": cancel, "cancel_reason": reason,
        "channel": hh.channel.values[hrow], "producer_id": hh.producer_id.values[hrow],
        "state": hh.state.values[hrow], "garaging_zip": hh.zip.values[hrow],
        "bi_limit": hh.bi_limit.values[hrow], "pd_limit": hh.pd_limit.values[hrow],
        "pip_limit": hh.pip_limit.values[hrow], "medpay_limit": hh.medpay_limit.values[hrow],
        "um_flag": hh.um_flag.values[hrow], "payment_plan": hh.payment_plan.values[hrow],
        "prior_carrier": np.where(seq == 0, hh.prior_carrier.values[hrow], cfg["company"]["short"]),
        "prior_lapse_days": np.where(seq == 0, hh.prior_lapse_days.values[hrow], 0),
    })
    bind_hour = np.where(t.channel == "DIRECT_ONLINE", rng.choice(24, n, p=np.array(cfg["frequency"]["hourly_profile"]) / sum(cfg["frequency"]["hourly_profile"])),
                         rng.integers(8, 19, n))
    t["bind_datetime"] = start - np.where(t.new_business_flag, rng.integers(0, 12, n), rng.integers(10, 40, n))
    if "_bind_hour_force" in hh:
        bf = hh._bind_hour_force.fillna(-1).values[hrow].astype(int)
        bind_hour = np.where((bf >= 0) & (seq == 0), bf, bind_hour)
    t["_bind_hour"] = bind_hour
    t["_ghost"] = ghost
    t["_hh"] = hrow
    W.t["terms"] = t


def build_exposure(W):
    """Vehicle x term rows with exposure years and true frequency relativity."""
    cfg = W.cfg
    t, ve, hh, dr = W.t["terms"], W.t["vehicles"], W.t["households"], W.t["drivers"]
    asof = d2i(cfg["run"]["as_of_date"])
    vt = t[["term_id", "_hh", "term_start", "term_end", "cancel_date", "state", "pip_limit", "medpay_limit", "um_flag",
            "bi_limit", "pd_limit", "new_business_flag", "producer_id", "channel"]].merge(
        ve[["vehicle_id", "_hh", "segment", "model_year", "msrp", "coll_deductible", "comp_deductible",
            "rental_coverage", "towing_coverage", "lienholder_flag", "make", "model", "adas_equipped"]], on="_hh")
    end = np.where(vt.cancel_date > 0, vt.cancel_date, vt.term_end)
    vt["exp_end"] = np.minimum(end, asof)
    vt["exp_years"] = np.clip(vt.exp_end - vt.term_start, 0, None) / 365.0
    vt = vt[vt.exp_years > 0].reset_index(drop=True)
    h = vt._hh.values
    vt["metro"] = hh._true_metro.values[h]
    vt["zip_factor"] = hh._true_zip_factor.values[h]
    vt["frailty"] = hh._frailty.values[h]
    # youngest listed driver age at term start, violations
    dr2 = dr[dr._listed].copy()
    dr2["by"] = dr2.date_of_birth.dt.year
    agg = dr2.groupby("customer_id").agg(max_by=("by", "max"), viol=("violations_3yr", "sum"), af=("at_fault_accidents_3yr", "sum"))
    cid = hh.customer_id.values[h]
    year_start = 1970 + vt.term_start.values / 365.25
    vt["youngest_age"] = (year_start - agg.max_by.reindex(cid).values).astype(int)
    vt["_true_youngest_age"] = vt["youngest_age"].values
    vt["violations"] = agg.viol.reindex(cid).values + agg.af.reindex(cid).values
    vt["credit_tier"] = hh.credit_tier.values[h]
    vt["homeowner"] = hh.homeowner.values[h]
    vt["n_vehicles"] = vt.groupby("term_id").vehicle_id.transform("count")
    W.t["vt"] = vt
    refresh_relativities(W)


def refresh_relativities(W):
    cfg = W.cfg
    vt = W.t["vt"]
    pr = cfg["pricing"]
    terr = W.geo.territory(vt.metro.values) * vt.zip_factor.values
    st = np.array([R.STATES[s][4] for s in vt.state.values])
    age_f = band_lookup(pr["youngest_driver_factor"], vt.youngest_age.values)
    cr = pd.Series(vt.credit_tier.values).map(pr["credit_factor"]).values
    viol = pr["violation_factor_each"] ** np.minimum(vt.violations.values, 4)
    seg = np.array([R.SEGMENT_REL[s] for s in vt.segment.values])
    ve = W.t["vehicles"].set_index("vehicle_id")
    miles = ve._true_miles.reindex(vt.vehicle_id).values
    use = ve._true_usage.reindex(vt.vehicle_id).values
    mf = np.where(miles < 7500, 0.85, np.where(miles > 15000, 1.0 + (miles - 15000) / 30000, 1.0))
    uf = np.where(use == "RIDESHARE", 1.0, np.where(use == "BUSINESS", 1.1, np.where(use == "PLEASURE", 0.92, 1.0)))
    base = terr * st * age_f ** 0.85 * cr ** 0.6 * viol * mf * uf
    e = vt.exp_years.values
    if not hasattr(W, "_rel_norm"):   # normalise once so base frequencies in config are book averages
        W._rel_norm = {}
    def norm(name, x):
        if name not in W._rel_norm:
            W._rel_norm[name] = (x * e).sum() / e.sum()
        return x / W._rel_norm[name]
    vt["rel_liab"] = norm("liab", base)
    vt["rel_coll"] = norm("coll", base * seg[:, 0])
    vt["rel_comp"] = norm("comp", (terr ** 0.8) * st * seg[:, 1] * cr ** 0.3)
    vt["rel_theft"] = norm("theft", (terr ** 1.3) * seg[:, 2])
    W.t["vt"] = vt
