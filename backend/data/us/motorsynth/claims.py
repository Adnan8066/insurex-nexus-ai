"""ClaimFactory: turns a table of claim *specs* into claims, claimants, features,
repair-estimate lines and medical bills. Baseline (genuine) claims and every scenario
injector go through the same factory, so planted claims are structurally identical to
real ones; only the statistics differ."""
import numpy as np
import pandas as pd
from . import refdata as R
from .util import lognormal, pick, i2d, make_vins

VEH_DAMAGE = {"COLL", "PD", "UMPD", "COMP"}
INJURY = {"BI", "PIP", "MEDPAY", "UMBI"}

ZONE_BY_CAUSE = {
    "AF_MULTI": {"FRONT": 0.70, "LEFT": 0.12, "RIGHT": 0.13, "REAR": 0.05},
    "AF_SINGLE": {"FRONT": 0.58, "LEFT": 0.15, "RIGHT": 0.17, "TOP": 0.10},
    "NAF": {"REAR": 0.52, "LEFT": 0.20, "RIGHT": 0.20, "FRONT": 0.08},
    "NAF_UNINSURED": {"REAR": 0.45, "LEFT": 0.22, "RIGHT": 0.23, "FRONT": 0.10},
    "TP_VEHICLE": {"REAR": 0.60, "LEFT": 0.17, "RIGHT": 0.18, "FRONT": 0.05},
    "WEATHER": {"TOP": 1.0}, "ANIMAL": {"FRONT": 0.85, "RIGHT": 0.15}, "VANDALISM": {"LEFT": 0.5, "RIGHT": 0.5},
    "FIRE": {"FRONT": 1.0}, "FLOOD": {"FRONT": 1.0}, "THEFT": {"LEFT": 0.4, "RIGHT": 0.3, "FRONT": 0.3},
}
LOCATION_BY_CAUSE = {
    "AF_MULTI": {"INTERSECTION": 0.38, "ARTERIAL_ROAD": 0.30, "HIGHWAY": 0.17, "PARKING_LOT": 0.10, "RESIDENTIAL_STREET": 0.05},
    "AF_SINGLE": {"RESIDENTIAL_STREET": 0.30, "ARTERIAL_ROAD": 0.25, "HIGHWAY": 0.20, "PARKING_LOT": 0.15, "RURAL_ROAD": 0.10},
    "NAF": {"INTERSECTION": 0.40, "ARTERIAL_ROAD": 0.25, "HIGHWAY": 0.15, "PARKING_LOT": 0.15, "RESIDENTIAL_STREET": 0.05},
    "COMP": {"RESIDENCE": 0.55, "PARKING_LOT": 0.20, "WORKPLACE": 0.12, "ARTERIAL_ROAD": 0.08, "HIGHWAY": 0.05},
}
NARRATIVES = {
    "AF_MULTI": ["Insured rear-ended other vehicle in stop-and-go traffic on {road}.",
                 "Insured failed to yield making a left turn at {road} and struck other vehicle.",
                 "Insured changed lanes on {road} and sideswiped vehicle in adjacent lane.",
                 "Insured ran a red light at {road}; collided with crossing vehicle.",
                 "Insured backing out of parking space struck passing vehicle."],
    "AF_SINGLE": ["Insured lost control on wet pavement on {road} and struck a guardrail.",
                  "Insured struck a utility pole while avoiding debris on {road}.",
                  "Insured hit a curb and fence turning onto {road}.",
                  "Insured slid off the roadway on {road} into a ditch."],
    "NAF": ["Other vehicle rear-ended insured while stopped at light on {road}.",
            "Other driver ran stop sign at {road} and struck insured's passenger side.",
            "Other vehicle merged into insured's lane on {road}.",
            "Insured legally parked; other vehicle struck it and left a note."],
    "NAF_UNINSURED": ["Other driver struck insured at {road}; other driver had no insurance.",
                      "Hit and run on {road}; other vehicle fled the scene."],
    "GLASS": ["Rock chip from truck on {road} cracked windshield.", "Windshield crack spread after cold morning.",
              "Debris on {road} struck windshield."],
    "THEFT": ["Vehicle stolen from {loc} overnight.", "Vehicle taken from {loc}; insured had both keys.",
              "Insured returned to {loc} and vehicle was gone."],
    "WEATHER": ["Hail damage to roof, hood and trunk while parked at {loc}.", "Tree limb fell on vehicle during storm at {loc}."],
    "ANIMAL": ["Struck a deer on {road} at dusk.", "Hit an animal crossing {road}."],
    "VANDALISM": ["Vehicle keyed and mirror broken while parked at {loc}.", "Windows smashed and panels dented at {loc}."],
    "FIRE": ["Engine compartment fire while driving on {road}.", "Vehicle caught fire while parked at {loc}."],
    "FLOOD": ["Vehicle submerged by flash flooding at {loc}.", "Water entered cabin during street flooding near {loc}."],
}
ROADS = ["I-{n}", "US-{n}", "State Rte {n}", "{s} Ave", "{s} Blvd", "{s} St and {s2} St", "{s} Pkwy"]
LOCS = ["residence", "apartment complex lot", "shopping center lot", "workplace garage", "street in front of residence",
        "transit station lot", "gym parking lot"]
CAUSE_TO_COV = {"GLASS": "COMP", "THEFT": "COMP", "WEATHER": "COMP", "ANIMAL": "COMP", "VANDALISM": "COMP",
                "FIRE": "COMP", "FLOOD": "COMP"}

SPEC_DEFAULTS = {"sev_mult": 1.0, "report_lag": np.nan, "reported_by": "", "loss_metro": "", "location_type": "",
                 "operator_driver_id": "", "operator_unlisted": False, "operator_age": np.nan, "shop_id": "",
                 "tow_id": "", "attorney_id": "", "provider_set": "", "treatment": "", "tp_vin": "",
                 "tp_vehicle_desc": "", "tp_claimant_ids": None, "cat_code": "", "narrative": "",
                 "n_occupants": np.nan, "total_loss_force": False, "theft_recovered": np.nan,
                 "odometer": np.nan, "zone": "", "passenger_ids": None, "want_coll": True, "want_pd": True,
                 "n_tp_injured": 0, "n_ins_injured": 0, "adjuster_id": "", "pd_sev_mult": 1.0, "inj_sev_mult": 1.0}


class ClaimFactory:
    def __init__(self, W):
        self.W = W
        self.rng = W.rng
        p = W.t["parties"]
        self.by_type_metro = {k: g for k, g in p[p._ring == ""].groupby(["party_type", "metro"])}

    # ---------------------------------------------------------------- helpers
    def _party(self, kind, metros, drp_pref=0.0):
        out = np.empty(len(metros), dtype=object)
        metros = np.asarray(metros, dtype=object)
        for m in np.unique(metros):
            idx = np.where(metros == m)[0]
            g = self.by_type_metro.get((kind, m))
            if g is None or len(g) == 0:
                g = self.W.t["parties"][(self.W.t["parties"].party_type == kind) & (self.W.t["parties"]._ring == "")]
            w = g._volume.values.copy()
            if drp_pref:
                w = np.where(g.drp_flag.values, w * (1 + drp_pref * 4), w)
            out[idx] = g.party_id.values[self.rng.choice(len(g), len(idx), p=w / w.sum())]
        return out

    def _road(self, n):
        rng = self.rng
        s = np.array(R.STREET_NAMES, dtype=object)
        t = rng.integers(0, len(ROADS), n)
        return [ROADS[i].format(n=rng.integers(5, 99), s=s[rng.integers(len(s))], s2=s[rng.integers(len(s))]) for i in t]

    def _narr(self, cause, style, n):
        rng = self.rng
        road, loc = self._road(n), np.array(LOCS, dtype=object)[rng.integers(0, len(LOCS), n)]
        out = np.empty(n, dtype=object)
        for i in range(n):
            if style[i]:
                txt = style[i]
            else:
                c = cause[i]
                opts = NARRATIVES.get(c, NARRATIVES["AF_MULTI"])
                txt = opts[rng.integers(len(opts))]
            out[i] = txt.format(road=road[i], loc=loc[i])
        return out

    # ---------------------------------------------------------------- main entry
    def create(self, spec, tag=""):
        W, rng = self.W, self.rng
        spec = spec.reset_index(drop=True).copy()
        for k, v in SPEC_DEFAULTS.items():
            if k not in spec:
                spec[k] = [v] * len(spec) if v is None else v
            elif v is not None and not (isinstance(v, float) and np.isnan(v)):
                col = spec[k]
                if col.isna().any():
                    spec[k] = col.astype(object).where(col.notna(), v).infer_objects(copy=False)
        for k in ("want_coll", "want_pd", "operator_unlisted", "total_loss_force"):
            spec[k] = spec[k].astype(bool)
        for k in ("n_tp_injured", "n_ins_injured"):
            spec[k] = spec[k].astype(int)
        n = len(spec)
        if n == 0:
            return pd.DataFrame()
        vt = W.t["vt"].iloc[spec.vt_idx.values].reset_index(drop=True)
        cause = spec.cause.values.astype(object)
        loss_metro = np.where(spec.loss_metro.values != "", spec.loss_metro.values, vt.metro.values)
        travel = (spec.loss_metro.values == "") & (rng.random(n) < 0.04)
        loss_metro = np.where(travel, W.geo.sample_metros(n), loss_metro)
        lzip, _ = W.geo.sample_zip(loss_metro)
        loss_day = spec.loss_day.values.astype(int)
        hour = spec.loss_hour.values.astype(int)
        minute = rng.integers(0, 60, n)
        lag = np.where(np.isnan(spec.report_lag.values.astype(float)),
                       rng.exponential(W.cfg["frequency"]["report_lag_days_mean"], n)
                       * np.where(np.isin(cause, ["THEFT"]), 0.4, 1.0),
                       spec.report_lag.values.astype(float))
        loss_ts = i2d(loss_day).astype("datetime64[m]") + (hour * 60 + minute).astype("timedelta64[m]")
        rep_ts = loss_ts + (lag * 1440).astype(int).astype("timedelta64[m]") + rng.integers(20, 240, n).astype("timedelta64[m]")
        comp_cause = np.isin(cause, list(CAUSE_TO_COV))
        loc_type = np.where(spec.location_type.values != "", spec.location_type.values,
                            np.where(comp_cause, pick(rng, LOCATION_BY_CAUSE["COMP"], n),
                                     np.where(cause == "AF_SINGLE", pick(rng, LOCATION_BY_CAUSE["AF_SINGLE"], n),
                                              np.where(np.isin(cause, ["NAF", "NAF_UNINSURED"]), pick(rng, LOCATION_BY_CAUSE["NAF"], n),
                                                       pick(rng, LOCATION_BY_CAUSE["AF_MULTI"], n)))))
        # operator
        dr = W.t["drivers"]
        drl = dr[dr._listed]
        cust = W.t["households"].customer_id.values[vt._hh.values]
        op = spec.operator_driver_id.values.astype(object).copy()
        need = (op == "") & ~spec.operator_unlisted.values.astype(bool) & ~comp_cause
        if need.any():
            g = drl.groupby("customer_id").driver_id.apply(list)
            lists = g.reindex(cust[need]).values
            op[need] = [l[0] if (rng.random() < 0.62 or len(l) == 1) else l[rng.integers(1, len(l))] for l in lists]
        dob = dr.set_index("driver_id").date_of_birth
        op_age = np.where(np.isnan(spec.operator_age.values.astype(float)),
                          np.where(op != "", ((loss_day - dob.reindex(op).values.astype("datetime64[D]").astype(int)) / 365.25), np.nan),
                          spec.operator_age.values.astype(float))
        # unlisted operators (name/age come from the hidden driver record)
        unl = spec.operator_unlisted.values.astype(bool)
        opf = np.full(n, "", dtype=object); opl = np.full(n, "", dtype=object); opa = np.full(n, "", dtype=object)
        if "_unlisted_driver" in spec and unl.any():
            hid = spec._unlisted_driver.values.astype(object)
            sel = unl & (hid != "")
            d = dr.set_index("driver_id")
            opf[sel] = d.first_name.reindex(hid[sel]).values
            opl[sel] = d.last_name.reindex(hid[sel]).values
            opa[sel] = d._address.reindex(hid[sel]).values
            op_age = op_age.astype(float)
            op_age[sel] = (loss_day[sel] - d.date_of_birth.reindex(hid[sel]).values.astype("datetime64[D]").astype(int)) / 365.25
        # odometer
        ve = W.t["vehicles"].set_index("vehicle_id")
        miles = ve._odo_miles.reindex(vt.vehicle_id).values
        vyear = vt.model_year.values
        age_y = np.maximum(0.3, (1970 + loss_day / 365.25) - vyear + 0.5)
        odo = np.where(np.isnan(spec.odometer.values.astype(float)), np.round(miles * age_y * rng.uniform(0.85, 1.15, n), -1),
                       spec.odometer.values.astype(float))
        occ = np.where(np.isnan(spec.n_occupants.values.astype(float)),
                       1 + rng.binomial(3, 0.18, n), spec.n_occupants.values.astype(float)).astype(int)
        occ = np.maximum(occ, spec.n_ins_injured.values.astype(int))
        cid = W.ids.take("CLM", n, 8)
        year = (1970 + loss_day / 365.25).astype(int)
        cnum = np.array([f"{W.cfg['company']['claim_prefix']}-{y}-{c[3:]}" for y, c in zip(year, cid)], dtype=object)
        n_veh = np.where(np.isin(cause, ["AF_MULTI", "NAF", "NAF_UNINSURED"]), 2 + (rng.random(n) < 0.08), 1)
        police = np.where(np.isin(cause, ["AF_MULTI", "NAF", "NAF_UNINSURED", "THEFT", "AF_SINGLE"]),
                          rng.random(n) < np.where(cause == "THEFT", 0.97, 0.62), rng.random(n) < 0.08)
        claims = pd.DataFrame({
            "claim_id": cid, "claim_number": cnum, "term_id": vt.term_id.values,
            "customer_id": cust, "vehicle_id": vt.vehicle_id.values,
            "operator_driver_id": op, "operator_listed": (op != "") | comp_cause,
            "operator_first_name": opf, "operator_last_name": opl, "operator_address": opa,
            "operator_age": np.round(op_age.astype(float), 0),
            "loss_datetime": loss_ts, "report_datetime": rep_ts,
            "reported_by": np.where(spec.reported_by.values != "", spec.reported_by.values,
                                    pick(rng, {"INSURED": 0.80, "AGENT": 0.10, "THIRD_PARTY": 0.07, "OTHER": 0.03}, n)),
            "report_channel": pick(rng, {"APP": 0.38, "PHONE": 0.42, "WEB": 0.14, "AGENT": 0.06}, n),
            "loss_cause": cause, "loss_state": W.geo.state(loss_metro), "loss_city": W.geo.city(loss_metro),
            "loss_zip": lzip, "loss_location_type": loc_type,
            "fault_indicator": np.select([np.isin(cause, ["AF_MULTI", "AF_SINGLE"]), np.isin(cause, ["NAF", "NAF_UNINSURED"])],
                                         ["AT_FAULT", "NOT_AT_FAULT"], "NO_FAULT_EVENT"),
            "vehicles_involved": n_veh, "occupants_in_vehicle": occ,
            "police_report_flag": police,
            "police_report_number": np.where(police, [f"PR-{x:09d}" for x in rng.integers(0, 10 ** 9, n)], ""),
            "odometer_at_loss": odo, "catastrophe_code": spec.cat_code.values,
            "description": self._narr(cause, spec.narrative.values, n),
            "adjuster_id": spec.adjuster_id.values,
        })
        claims["_metro"] = loss_metro
        claims["_vt_idx"] = spec.vt_idx.values
        claims["_tag"] = tag
        # ---------------------------------------------------------- features
        has_coll = ~np.isnan(vt.coll_deductible.values)
        has_comp = ~np.isnan(vt.comp_deductible.values)
        nf = vt.pip_limit.values > 0
        um = vt.um_flag.values.astype(bool)
        mp = vt.medpay_limit.values > 0
        want_coll = spec.want_coll.values.astype(bool)
        rows = []  # (claim_idx, coverage, claimant_kind, subtype)
        for i in range(n):
            c = cause[i]
            if c in CAUSE_TO_COV:
                if has_comp[i]:
                    rows.append((i, "COMP", "INSURED_OWNER", c))
                continue
            if c in ("AF_MULTI", "AF_SINGLE", "NAF") and has_coll[i] and want_coll[i]:
                rows.append((i, "COLL", "INSURED_OWNER", c))
            if c == "NAF_UNINSURED":
                if has_coll[i]:
                    rows.append((i, "COLL", "INSURED_OWNER", c))
                elif um[i]:
                    rows.append((i, "UMPD", "INSURED_OWNER", c))
            if c == "AF_MULTI" and spec.want_pd.values[i]:
                rows.append((i, "PD", "TP_OWNER", "VEHICLE"))
            if c == "AF_SINGLE" and spec.want_pd.values[i]:
                rows.append((i, "PD", "TP_PROPERTY", "PROPERTY"))
            for _ in range(int(spec.n_tp_injured.values[i])):
                rows.append((i, "BI", "TP_INJURED", ""))
            for _ in range(int(spec.n_ins_injured.values[i])):
                if nf[i]:
                    rows.append((i, "PIP", "INSURED_INJURED", ""))
                elif c == "NAF_UNINSURED" and um[i]:
                    rows.append((i, "UMBI", "INSURED_INJURED", ""))
                elif mp[i]:
                    rows.append((i, "MEDPAY", "INSURED_INJURED", ""))
        F = pd.DataFrame(rows, columns=["ci", "coverage", "claimant_kind", "subtype"])
        nF = len(F)
        F["feature_id"] = W.ids.take("FEA", nF, 8)
        F["claim_id"] = cid[F.ci.values]
        # claimants
        F = self._claimants(F, claims, spec, vt, op)
        # severity targets
        F = self._targets(F, spec, vt, claims, loss_day)
        # parties
        fm = loss_metro[F.ci.values]
        dmg = F.coverage.isin(["COLL", "UMPD", "PD"]) & (F.subtype != "PROPERTY") | \
              ((F.coverage == "COMP") & F.subtype.isin(["WEATHER", "ANIMAL", "VANDALISM", "FIRE", "FLOOD", "THEFT"]))
        F["repairer_party_id"] = ""
        shop_force = spec.shop_id.values[F.ci.values]
        sh = self._party("BODY_SHOP", fm, drp_pref=0.6)
        F.loc[dmg, "repairer_party_id"] = np.where(shop_force[dmg.values] != "", shop_force[dmg.values], sh[dmg.values])
        gl = (F.coverage == "COMP") & (F.subtype == "GLASS")
        F.loc[gl, "repairer_party_id"] = np.where(shop_force[gl.values] != "", shop_force[gl.values], self._party("GLASS", fm[gl.values]))
        inj = F.coverage.isin(list(INJURY))
        att_p = np.where(F.coverage == "BI", W.cfg["severity"]["attorney_rate_bi"], 0.22)
        att_force = spec.attorney_id.values[F.ci.values]
        has_att = inj & ((rng.random(nF) < att_p) | (att_force != ""))
        F["attorney_party_id"] = ""
        F.loc[has_att, "attorney_party_id"] = np.where(att_force[has_att.values] != "", att_force[has_att.values],
                                                       self._party("ATTORNEY", fm[has_att.values]))
        F["_att_days"] = np.where(has_att, rng.exponential(25, nF) + 2, np.nan)
        F["_gd_genuine"] = np.nan
        F["_fraud_full"] = False
        F["_genuine_mult"] = 1.0
        self._pending_L = None; self._pending_B = None
        self._estimates(F[dmg | gl], vt, spec, claims, loss_day)
        info = self._bills(F[inj], spec, claims, loss_day)
        F["injury_type"] = ""
        F["_gd"] = np.nan
        if info is not None:
            F.loc[inj.values, "injury_type"] = pd.Series(info.injury_type.values, index=info.feature_id).reindex(F.feature_id[inj]).values
            F.loc[inj.values, "_gd"] = pd.Series(info.gd.values, index=info.feature_id).reindex(F.feature_id[inj]).values
        # claims not yet reported at the valuation date are IBNR: they do not exist in the data
        asof = np.datetime64(W.cfg["run"]["as_of_date"]) + np.timedelta64(1, "D")
        reported = rep_ts < asof.astype("datetime64[m]")
        keep = np.isin(np.arange(n), F.ci.values) & reported
        F = F[keep[F.ci.values]]
        kept_f = set(F.feature_id)
        claims = claims[keep].reset_index(drop=True)
        W.append("claims", claims)
        W.append("features", F)
        for name, attr in (("estimate_lines", "_pending_L"), ("medical_bills", "_pending_B")):
            df = getattr(self, attr, None)
            if df is not None:
                W.append(name, df[df.feature_id.isin(kept_f)])
                setattr(self, attr, None)
        return claims

    # ---------------------------------------------------------------- claimants
    def _claimants(self, F, claims, spec, vt, op):
        W, rng = self.W, self.rng
        nF = len(F)
        ci = F.ci.values
        kind = F.claimant_kind.values
        metro = claims._metro.values[ci]
        dr = W.t["drivers"].set_index("driver_id")
        hhdf = W.t["households"].set_index("customer_id")
        cid_ins = claims.customer_id.values[ci]
        cl_id = np.empty(nF, dtype=object)
        new_rows = []
        # insured owner -> the named insured
        own = kind == "INSURED_OWNER"
        cl_id[own] = "INS-" + cid_ins[own]
        # insured injured: first injured is operator (if listed), rest passengers
        inj = np.where(kind == "INSURED_INJURED")[0]
        order = pd.Series(ci[inj]).groupby(ci[inj]).cumcount().values
        pass_force = spec.passenger_ids.values
        for j, k in zip(inj, order):
            c = ci[j]
            forced = pass_force[c]
            if forced is not None and isinstance(forced, (list, tuple)) and k < len(forced):
                cl_id[j] = forced[k]
            elif k == 0 and op[c] != "":
                cl_id[j] = "DRV-" + op[c]
            else:
                cl_id[j] = None
        tp = np.isin(kind, ["TP_OWNER", "TP_INJURED", "TP_PROPERTY"])
        tp_force = spec.tp_claimant_ids.values
        tp_idx = np.where(tp)[0]
        inj_tp = tp_idx[kind[tp_idx] == "TP_INJURED"]
        inj_order = pd.Series(np.arange(len(inj_tp)), index=inj_tp)
        inj_order[:] = pd.Series(ci[inj_tp]).groupby(ci[inj_tp]).cumcount().values
        for j in tp_idx:
            forced = tp_force[ci[j]]
            if forced is not None and isinstance(forced, (list, tuple)) and len(forced):
                kk = 0 if kind[j] != "TP_INJURED" else int(inj_order[j])
                cl_id[j] = forced[kk] if kk < len(forced) else None
            else:
                cl_id[j] = None
        # TP owner and first TP injured are the same person when generated fresh
        need = np.array([x is None for x in cl_id])
        if need.any():
            idx = np.where(need)[0]
            # share a person between TP_OWNER and first TP_INJURED in same claim
            key = np.where(np.isin(kind[idx], ["TP_OWNER"]), 0, -1)
            m = len(idx)
            g = np.where(rng.random(m) < 0.5, "M", "F")
            by = rng.integers(1950, 2006, m)
            f, mi, l, s = W.names.people(g, by)
            z, _ = W.geo.sample_zip(metro[idx])
            pid = W.ids.take("CLT", m, 8)
            new = pd.DataFrame({"claimant_id": pid, "first_name": f, "middle_name": mi, "last_name": l, "gender": g,
                                "date_of_birth": pd.to_datetime(by.astype(str)) + pd.to_timedelta(rng.integers(0, 365, m), "D"),
                                "phone": W.geo.phone(metro[idx]), "address": W.geo.street(m), "zip": z,
                                "city": W.geo.city(metro[idx]), "state": W.geo.state(metro[idx])})
            cl_id[idx] = pid
            # merge TP owner + first TP injured in same claim into one person
            df = pd.DataFrame({"j": idx, "ci": ci[idx], "kind": kind[idx]})
            owners = df[df.kind == "TP_OWNER"].set_index("ci").j
            first_inj = df[df.kind == "TP_INJURED"].groupby("ci").j.first()
            both = owners.index.intersection(first_inj.index)
            both = both[rng.random(len(both)) < 0.85]
            cl_id[first_inj.loc[both].values] = cl_id[owners.loc[both].values]
            W.append("persons", new)
        F["claimant_id"] = cl_id
        F["claimant_role"] = np.select([kind == "INSURED_OWNER", kind == "INSURED_INJURED", kind == "TP_OWNER",
                                        kind == "TP_PROPERTY", kind == "TP_INJURED"],
                                       ["INSURED", np.where([str(x).startswith("DRV-") for x in cl_id], "INSURED_DRIVER", "INSURED_PASSENGER"),
                                        "THIRD_PARTY_DRIVER", "THIRD_PARTY_PROPERTY_OWNER", "THIRD_PARTY_OCCUPANT"], "")
        # third-party vehicle for TP features
        tpv = np.isin(kind, ["TP_OWNER", "TP_INJURED"])
        vin_force = spec.tp_vin.values[ci]
        desc_force = spec.tp_vehicle_desc.values[ci]
        F["tp_vehicle_vin"] = ""; F["tp_vehicle_desc"] = ""
        if tpv.any():
            idx = np.where(tpv)[0]
            ucl = np.unique(ci[idx])
            vw = np.array([v[7] for v in R.VEHICLES]); vw = vw / vw.sum()
            mi = rng.choice(len(R.VEHICLES), len(ucl), p=vw)
            yrs = rng.integers(2008, 2025, len(ucl))
            vins = make_vins(rng, np.array([R.VEHICLES[i][5] for i in mi], dtype=object), yrs)
            desc = np.array([f"{y} {R.VEHICLES[i][0]} {R.VEHICLES[i][1]}" for y, i in zip(yrs, mi)], dtype=object)
            mv = pd.Series(vins, index=ucl); md = pd.Series(desc, index=ucl)
            F.loc[tpv, "tp_vehicle_vin"] = np.where(vin_force[idx] != "", vin_force[idx], mv.reindex(ci[idx]).values)
            F.loc[tpv, "tp_vehicle_desc"] = np.where(desc_force[idx] != "", desc_force[idx], md.reindex(ci[idx]).values)
        return F

    # ---------------------------------------------------------------- severity targets
    def _targets(self, F, spec, vt, claims, loss_day):
        W, rng = self.W, self.rng
        sv = W.cfg["severity"]
        ci = F.ci.values
        nF = len(F)
        cov = F.coverage.values
        sub = F.subtype.values
        v = vt.iloc[ci]
        msrp = v.msrp.values
        age = np.maximum(0, (1970 + loss_day[ci] / 365.25) - v.model_year.values)
        acv = np.round(msrp * np.maximum(0.08, 0.83 * 0.885 ** age), -1)
        vf = (msrp / 36000) ** 0.45
        mult = spec.sev_mult.values[ci].astype(float)
        tgt = np.zeros(nF)
        def put(mask, key, extra=1.0):
            if mask.any():
                tgt[mask] = lognormal(rng, sv[key]["mean"], sv[key]["sigma"], mask.sum()) * extra[mask] if isinstance(extra, np.ndarray) else \
                    lognormal(rng, sv[key]["mean"], sv[key]["sigma"], mask.sum()) * extra
        put(cov == "COLL", "COLL", vf * np.where(sub == "AF_SINGLE", 1.15, 1.0))
        put(cov == "UMPD", "UMPD", vf)
        tp_vf = 1.0
        put((cov == "PD") & (sub == "VEHICLE"), "PD", spec.pd_sev_mult.values[ci].astype(float))
        put((cov == "PD") & (sub == "PROPERTY"), "PD", 0.55)
        put(cov == "BI", "BI", spec.inj_sev_mult.values[ci].astype(float))
        put(cov == "PIP", "PIP", spec.inj_sev_mult.values[ci].astype(float))
        put(cov == "MEDPAY", "MEDPAY")
        put(cov == "UMBI", "UMBI")
        put((cov == "COMP") & (sub == "GLASS"), "COMP_GLASS", vf ** 0.5)
        put((cov == "COMP") & (sub == "WEATHER"), "COMP_WEATHER", vf)
        put((cov == "COMP") & (sub == "ANIMAL"), "COMP_ANIMAL", vf)
        put((cov == "COMP") & (sub == "VANDALISM"), "COMP_VANDALISM", vf)
        # theft / fire / flood: mostly total losses
        th = (cov == "COMP") & (sub == "THEFT")
        rec = spec.theft_recovered.values[ci].astype(float)
        rec = np.where(np.isnan(rec), rng.random(nF) < 0.42, rec > 0.5)
        tgt[th & ~rec] = acv[th & ~rec] * 1.02
        tgt[th & rec] = lognormal(rng, 3600, 0.8, (th & rec).sum()) * vf[th & rec]
        fi = (cov == "COMP") & (sub == "FIRE")
        tgt[fi] = np.where(rng.random(fi.sum()) < 0.78, acv[fi] * 1.05, lognormal(rng, 4200, 0.7, fi.sum()))
        fl = (cov == "COMP") & (sub == "FLOOD")
        tgt[fl] = np.where(rng.random(fl.sum()) < 0.68, acv[fl] * 1.02, lognormal(rng, 6500, 0.6, fl.sum()))
        force_tl = spec.total_loss_force.values[ci].astype(bool) & np.isin(cov, ["COLL", "COMP"])
        tgt[force_tl] = np.maximum(tgt[force_tl], acv[force_tl] * rng.uniform(0.9, 1.3, force_tl.sum()))
        tgt = tgt * np.where(np.isin(cov, ["COLL", "COMP", "UMPD"]), mult, 1.0)
        F["acv"] = np.where(np.isin(cov, ["COLL", "COMP", "UMPD"]), acv, np.nan)
        F["theft_recovered"] = np.where(th, rec, False)
        F["_target"] = np.round(tgt, 2)
        F["_vehicle_factor"] = vf
        F["_adas"] = v.adas_equipped.values
        F["_model_year"] = v.model_year.values
        return F

    # ---------------------------------------------------------------- repair estimate lines
    def _estimates(self, F, vt, spec, claims, loss_day):
        W, rng = self.W, self.rng
        if len(F) == 0:
            return
        F = F.reset_index(drop=True)
        ci = F.ci.values
        sub = F.subtype.values
        cause = claims.loss_cause.values[ci]
        zone_force = spec.zone.values[ci]
        zone = np.empty(len(F), dtype=object)
        for c in np.unique(np.where(F.coverage.values == "PD", "TP_VEHICLE", cause)):
            m = np.where(F.coverage.values == "PD", "TP_VEHICLE", cause) == c
            zone[m] = pick(rng, ZONE_BY_CAUSE.get(c, ZONE_BY_CAUSE["AF_MULTI"]), m.sum())
        zone = np.where(zone_force != "", zone_force, zone)
        glass = sub == "GLASS"
        lab = W.t["parties"].set_index("party_id").labor_rate
        rate = lab.reindex(F.repairer_party_id.values).values
        rate = np.where(np.isnan(rate), 60.0, rate)
        tgt = F._target.values
        tl = tgt >= W.cfg["severity"]["total_loss_threshold"] * np.nan_to_num(F.acv.values, nan=1e12)
        est_tgt = np.where(tl, np.minimum(tgt, np.where(np.isnan(F.acv.values.astype(float)), tgt, F.acv.values.astype(float)) * rng.uniform(0.8, 1.25, len(F))), tgt)
        out = []
        for z in ("FRONT", "REAR", "LEFT", "RIGHT", "TOP"):
            m = np.where((zone == z) & ~glass)[0]
            if len(m) == 0:
                continue
            P = R.PARTS[z]
            w = np.array([p[5] for p in P])
            keys = -np.log(rng.random((len(m), len(P)))) / w
            order = np.argsort(keys, axis=1)
            k = np.clip(np.round(est_tgt[m] / 820 + rng.normal(0, 0.8, len(m))), 1, len(P)).astype(int)
            rr = np.repeat(np.arange(len(m)), k)
            pos = np.concatenate([np.arange(x) for x in k])
            pidx = order[rr, pos]
            fi = m[rr]
            price = np.array([P[i][1] for i in pidx]) * F._vehicle_factor.values[fi] * rng.uniform(0.85, 1.2, len(fi))
            rh = np.array([P[i][2] for i in pidx]); ph = np.array([P[i][3] for i in pidx]); fh = np.array([P[i][4] for i in pidx])
            repair = (rh > 0) & (rng.random(len(fi)) < 0.42)
            op = np.where(repair, "REPAIR", "REPLACE")
            hrs = np.where(repair, rh, ph) * rng.uniform(0.8, 1.25, len(fi))
            part_amt = np.where(repair, 0.0, price)
            ptype = np.where(repair, "", pick(rng, {"OEM": 0.62, "AFTERMARKET": 0.26, "LKQ_USED": 0.12}, len(fi)))
            part_amt = part_amt * np.where(ptype == "AFTERMARKET", 0.7, np.where(ptype == "LKQ_USED", 0.55, 1.0))
            ref = fh * rng.uniform(0.9, 1.2, len(fi))
            out.append(pd.DataFrame({"fi": fi, "zone": z, "operation": op, "part_name": [P[i][0] for i in pidx],
                                     "part_type": ptype, "body_labor_hours": hrs, "refinish_hours": ref,
                                     "part_amount": part_amt}))
        if glass.any():
            m = np.where(glass)[0]
            out.append(pd.DataFrame({"fi": m, "zone": "GLASS", "operation": "REPLACE", "part_name": "Windshield",
                                     "part_type": pick(rng, {"OEM": 0.45, "AFTERMARKET": 0.55}, len(m)),
                                     "body_labor_hours": 1.5, "refinish_hours": 0.0,
                                     "part_amount": est_tgt[m] * 0.82}))
        L = pd.concat(out, ignore_index=True)
        L["labor_rate"] = rate[L.fi.values]
        L["paint_rate"] = np.round(rate[L.fi.values] * 0.95, 0)
        L["line_amount"] = L.part_amount + L.body_labor_hours * L.labor_rate + L.refinish_hours * (L.paint_rate + 38)
        # scale toward target so frequencies x severities stay calibrated
        sums = L.groupby("fi").line_amount.sum()
        sc = np.clip(est_tgt[sums.index.values] / sums.values, 0.4, 3.5)
        s = pd.Series(sc, index=sums.index).reindex(L.fi.values).values
        L["part_amount"] *= s; L["body_labor_hours"] *= np.sqrt(s); L["refinish_hours"] *= np.sqrt(s)
        L["line_amount"] = L.part_amount + L.body_labor_hours * L.labor_rate + L.refinish_hours * (L.paint_rate + 38)
        # sublets
        sl = []
        adas = F._adas.values.astype(bool)
        need_cal = (adas & (np.isin(zone, ["FRONT", "REAR"]) | glass)) & (rng.random(len(F)) < 0.7)
        sl.append(pd.DataFrame({"fi": np.where(need_cal)[0], "part_name": "ADAS calibration", "line_amount": R.SUBLET["ADAS calibration"] * rng.uniform(0.85, 1.25, need_cal.sum())}))
        frame = (est_tgt > 11000) & (rng.random(len(F)) < 0.45) & ~glass
        sl.append(pd.DataFrame({"fi": np.where(frame)[0], "part_name": "Frame setup & pull", "line_amount": R.SUBLET["Frame setup & pull"] * rng.uniform(0.8, 1.4, frame.sum())}))
        towed = ((est_tgt > 5500) | tl | (cause[np.arange(len(F))] == "AF_SINGLE")) & ~glass & (F.coverage.values != "PD") & (rng.random(len(F)) < 0.72)
        tow_force = spec.tow_id.values[ci]
        tow_party = np.where(tow_force != "", tow_force, "")
        tp_need = towed & (tow_party == "")
        tow_party[tp_need] = self._party("TOW", claims._metro.values[ci][tp_need])
        tow_amt = R.SUBLET["Towing"] * rng.uniform(0.8, 1.5, len(F))
        st_days = np.where(tl, rng.integers(3, 18, len(F)), rng.integers(0, 4, len(F)))
        idx = np.where(towed)[0]
        sl.append(pd.DataFrame({"fi": idx, "part_name": "Towing", "line_amount": tow_amt[idx], "vendor_party_id": tow_party[idx],
                                "quantity": 1}))
        idx2 = idx[st_days[idx] > 0]
        sl.append(pd.DataFrame({"fi": idx2, "part_name": "Storage (per day)", "quantity": st_days[idx2],
                                "line_amount": st_days[idx2] * R.SUBLET["Storage (per day)"] * rng.uniform(0.9, 1.2, len(idx2)),
                                "vendor_party_id": tow_party[idx2]}))
        S = pd.concat(sl, ignore_index=True)
        S["zone"] = "SUBLET"; S["operation"] = "SUBLET"; S["part_type"] = ""
        S["body_labor_hours"] = 0.0; S["refinish_hours"] = 0.0; S["part_amount"] = S.line_amount
        S["labor_rate"] = np.nan; S["paint_rate"] = np.nan
        L["vendor_party_id"] = ""; L["quantity"] = 1
        L = pd.concat([L, S], ignore_index=True)
        L["vendor_party_id"] = L.vendor_party_id.fillna("")
        L["quantity"] = L.quantity.fillna(1).astype(int)
        L = L.sort_values(["fi", "zone"], kind="stable")
        L["feature_id"] = F.feature_id.values[L.fi.values]
        L["claim_id"] = F.claim_id.values[L.fi.values]
        L["line_no"] = L.groupby("fi").cumcount() + 1
        L["is_supplement"] = False
        L["written_date"] = i2d(loss_day[F.ci.values[L.fi.values]] + 2 + rng.integers(0, 6, len(L)))
        for c in ("body_labor_hours", "refinish_hours"):
            L[c] = np.round(L[c], 1)
        for c in ("part_amount", "line_amount"):
            L[c] = np.round(L[c], 2)
        L["line_amount"] = np.round(np.where(L.operation == "SUBLET", L.line_amount,
                                             L.part_amount + L.body_labor_hours * L.labor_rate + L.refinish_hours * (L.paint_rate + 38)), 2)
        L["_tl"] = tl[L.fi.values]
        L = L.drop(columns=["fi"])
        self._pending_L = L

    # ---------------------------------------------------------------- medical bills
    def _bills(self, F, spec, claims, loss_day):
        W, rng = self.W, self.rng
        if len(F) == 0:
            return
        F = F.reset_index(drop=True)
        n = len(F)
        ci = F.ci.values
        treat = spec.treatment.values[ci]
        mill = treat == "MILL"
        att = F.attorney_party_id.values != ""
        inj = pick(rng, R.INJURIES, n)
        inj = np.where(mill, np.where(rng.random(n) < 0.6, "SPRAIN_STRAIN_NECK", "SPRAIN_STRAIN_BACK"), inj)
        F["injury_type"] = inj
        frac = inj == "FRACTURE"
        cnt = {
            "ER": (rng.random(n) < np.where(mill, 0.25, 0.68)).astype(int),
            "XRAY": (rng.random(n) < np.where(mill, 0.55, 0.50)).astype(int),
            "MRI": (rng.random(n) < np.where(mill, 0.92, np.where(att, 0.30, 0.10))).astype(int),
            "EM": rng.poisson(np.where(mill, 3.0, 1.6)),
            "CHIRO": np.where(rng.random(n) < np.where(mill, 0.95, np.where(att, 0.42, 0.18)),
                              np.where(mill, rng.integers(22, 36, n), rng.integers(6, 16, n)), 0),
            "PT": np.where(rng.random(n) < np.where(mill, 0.85, 0.30), np.where(mill, rng.integers(14, 26, n), rng.integers(6, 16, n)), 0),
            "INJECT": (rng.random(n) < np.where(mill, 0.45, np.where(att, 0.08, 0.03))).astype(int),
            "SURG": (rng.random(n) < np.where(frac, 0.28, 0.006)).astype(int),
            "RX": rng.poisson(np.where(mill, 2.5, 1.0)),
        }
        tot = sum(cnt.values())
        cnt["EM"] = np.where(tot == 0, 1, cnt["EM"])
        provider_force = spec.provider_set.values[ci]
        rows = []
        for code, k in cnt.items():
            if k.sum() == 0:
                continue
            r = np.repeat(np.arange(n), k)
            seq = np.concatenate([np.arange(x) for x in k])
            rows.append(pd.DataFrame({"fi": r, "service_code": code, "seq": seq}))
        B = pd.concat(rows, ignore_index=True)
        lo = B.service_code.map({k: v[1] for k, v in R.MED_SERVICES.items()}).values
        hi = B.service_code.map({k: v[2] for k, v in R.MED_SERVICES.items()}).values
        B["billed_amount"] = rng.uniform(lo, hi)
        B["service_desc"] = B.service_code.map({k: v[0] for k, v in R.MED_SERVICES.items()})
        ptype = B.service_code.map({k: v[3] for k, v in R.MED_SERVICES.items()}).values
        metro = claims._metro.values[ci[B.fi.values]]
        prov = np.empty(len(B), dtype=object)
        # one provider per (feature, provider type)
        key = pd.DataFrame({"fi": B.fi.values, "pt": ptype, "metro": metro}).drop_duplicates(["fi", "pt"])
        key["pid"] = ""
        for pt in key.pt.unique():
            mm = key.pt == pt
            key.loc[mm, "pid"] = self._party(pt, key.metro[mm].values)
        # ring provider overrides
        rp = W.ring_providers
        forced = provider_force[key.fi.values]
        col = key.columns.get_loc("pid")
        for j in np.where(forced != "")[0]:
            fs, pt = forced[j], key.pt.values[j]
            if fs in rp and pt in rp[fs]:
                key.iat[j, col] = rp[fs][pt]
        pmap = key.set_index(["fi", "pt"]).pid
        prov = pmap.reindex(pd.MultiIndex.from_arrays([B.fi.values, ptype])).values
        B["provider_party_id"] = prov
        # service dates: ER day 0-1, imaging week 1-3, therapy spread over weeks
        start = loss_day[ci[B.fi.values]]
        gap = np.select([B.service_code == "ER", B.service_code == "XRAY", B.service_code == "MRI"],
                        [rng.integers(0, 2, len(B)), rng.integers(0, 10, len(B)), rng.integers(7, 30, len(B))],
                        rng.integers(3, 10, len(B)) + B.seq.values * rng.integers(2, 5, len(B)))
        B["service_date"] = i2d(start + gap)
        # scale to target specials
        tgt = F._target.values.copy()
        is_bi = F.coverage.values == "BI"
        gd = np.where(is_bi | (F.coverage.values == "UMBI"), rng.uniform(1.3, 2.2, n) * np.where(att, W.cfg["severity"]["attorney_severity_mult"] ** 0.5, 1.0), 1.0)
        tgt = tgt * np.where(att, W.cfg["severity"]["attorney_severity_mult"] ** 0.5, 1.0)
        specials = tgt / gd
        sums = B.groupby("fi").billed_amount.sum()
        sc = specials[sums.index.values] / sums.values
        sc = np.where(mill[sums.index.values], np.clip(sc, 0.9, 1.6), np.clip(sc, 0.25, 8.0))
        B["billed_amount"] = np.round(B.billed_amount * pd.Series(sc, index=sums.index).reindex(B.fi.values).values, 2)
        B["allowed_amount"] = np.round(B.billed_amount * np.where(F.coverage.values[B.fi.values] == "PIP", rng.uniform(0.72, 0.92, len(B)), 1.0), 2)
        B["feature_id"] = F.feature_id.values[B.fi.values]
        B["claim_id"] = F.claim_id.values[B.fi.values]
        B["claimant_id"] = F.claimant_id.values[B.fi.values]
        B["units"] = 1
        B["diagnosis_group"] = F.injury_type.values[B.fi.values]
        self._pending_B = B.drop(columns=["fi", "seq"])
        return pd.DataFrame({"feature_id": F.feature_id.values, "injury_type": inj, "gd": gd})
