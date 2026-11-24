"""Entry point:  python -m motorsynth.generate [config.yaml] [--terms N] [--out DIR]"""
import argparse
import time
import yaml
import pandas as pd
from .world import World
from . import entities as E, baseline, scenarios as S, finance as Fi, siu, export, report


def run(cfg):
    t0 = time.time()
    def log(msg):
        print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)
    W = World(cfg)
    E.build_producers(W); E.build_employees(W); E.build_parties(W)
    E.build_households(W); log(f"households {len(W.t['households']):,}")
    E.build_drivers(W); E.build_vehicles(W); log(f"drivers {len(W.t['drivers']):,} vehicles {len(W.t['vehicles']):,}")
    S.pre_terms(W)
    E.build_terms(W); E.build_exposure(W); log(f"terms {len(W.t['terms']):,} vehicle-terms {len(W.t['vt']):,}")
    S.pre_claims(W); E.refresh_relativities(W)
    fac = baseline.generate(W); W.consolidate(); log(f"baseline claims {len(W.t['claims']):,}")
    S.add_claims(W, fac); W.consolidate(); log(f"claims after scenarios {len(W.t['claims']):,}")
    S.mutate(W); log("mutations applied")
    Fi.assign_adjusters(W)
    Fi.settle_amounts(W); Fi.add_rental(W)
    S.post_settle(W)
    siu.run(W); log(f"SIU referrals {len(W.t['siu']):,}")
    Fi.finalize(W)
    S.post_pay(W); Fi.rollup_claims(W)
    Fi.premium(W)
    # commission: charged back on cancelled genuine terms, kept in full on ghost policies
    T = W.t["terms"]
    rate = pd.Series(T.channel.values).map(cfg["book"]["commission_rate"]).fillna(0).values
    T["commission_amount"] = (T.written_premium * rate).where(T._ghost, T.earned_premium * rate).round(2)
    log(f"premium scale {W.premium_scale:.3f}")
    out = export.build(W)
    out, dq = export.data_quality(W, out)
    tc = siu.claim_truth_wide(W)
    TI = pd.concat(W.truth, ignore_index=True)
    Tt = W.t["terms"]
    pl = Tt[(Tt._earned_premium_true - Tt.earned_premium).abs() > 1][["term_id", "policy_number", "customer_id", "producer_id", "earned_premium", "_earned_premium_true"]]
    pl = pl.rename(columns={"_earned_premium_true": "earned_premium_if_truthful"})
    pl["premium_leakage"] = (pl.earned_premium_if_truthful - pl.earned_premium).round(2)
    cat = pd.DataFrame([{"scenario": k, **{kk: (str(vv) if isinstance(vv, (list, dict)) else vv) for kk, vv in v.items()}} for k, v in cfg["scenarios"].items()])
    truth = {"truth_instances": TI, "truth_claims": tc, "truth_policy_premium": pl, "data_quality_log": dq, "scenario_catalog": cat}
    folder = cfg["run"]["output_dir"]
    sizes = export.write(W, out, truth, folder)
    log("written: " + ", ".join(f"{k}={v:,}" for k, v in sizes.items()))
    r = report.compute(W, out, tc)
    report.write(W, r, folder)
    report.story(W, r, folder)
    log(f"loss ratio {r['loss_ratio']:.3f}; claim fraud {r['share_claim_fraud']:.2%}; fraud excess ${r['fraud_excess']/1e6:,.1f}M")
    return W, out, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default="config.yaml")
    ap.add_argument("--terms", type=int)
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--no-csv", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config, encoding="utf-8"))
    if a.terms:
        cfg["run"]["target_policy_terms"] = a.terms
    if a.out:
        cfg["run"]["output_dir"] = a.out
    if a.seed:
        cfg["run"]["seed"] = a.seed
    if a.no_csv:
        cfg["run"]["write_csv"] = False
    run(cfg)


if __name__ == "__main__":
    main()
