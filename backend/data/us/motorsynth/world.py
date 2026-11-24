import numpy as np
import pandas as pd
from .util import Geo, IdGen
from .names import NameFactory, BizNameFactory


class World:
    """Holds config, RNG, factories, all tables and the hidden ground truth."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg["run"]["seed"])
        self.geo = Geo(self.rng)
        self.names = NameFactory(self.rng)
        self.biz = BizNameFactory(self.rng, self.names)
        self.ids = IdGen()
        self.t = {}
        self.truth = []           # list of DataFrames: one row per (instance, entity)
        self.ring_providers = {}  # provider_set key -> {party_type: party_id}
        self.storylines = {}
        self.genuine_rules = []   # (claim_ids, coverages|None, genuine multiplier)
        self.glass_adas = []
        self.pileup_reports = {}
        self.dup_pairs = []

    # tables that grow in chunks
    def append(self, name, df):
        cur = self.t.get(name)
        if cur is None:
            self.t[name] = [df]
        elif isinstance(cur, list):
            cur.append(df)
        else:
            self.t[name] = [cur, df]

    def table(self, name):
        cur = self.t.get(name)
        if isinstance(cur, list):
            cur = pd.concat(cur, ignore_index=True) if cur else pd.DataFrame()
            self.t[name] = cur
        return cur

    def consolidate(self):
        for k, v in list(self.t.items()):
            if isinstance(v, list):
                self.table(k)

    def truth_add(self, scenario, entity_type, entity_ids, signals=None, ring_id="", role="", instance_ids=None, **extra):
        sc = self.cfg["scenarios"][scenario]
        entity_ids = np.asarray(entity_ids, dtype=object)
        n = len(entity_ids)
        if n == 0:
            return
        if instance_ids is None:
            instance_ids = self.ids.take(f"INS-{scenario[:4]}-", n, 6)
        if signals is None:
            sig = [""] * n
        elif isinstance(signals, pd.DataFrame):
            cols = list(signals.columns)
            vals = signals.values
            sig = [";".join(c for c, v in zip(cols, row) if v) for row in vals]
        else:
            sig = list(signals)
        df = pd.DataFrame({"instance_id": instance_ids, "scenario": scenario, "layer": sc["layer"], "family": sc["family"],
                           "entity_type": entity_type, "entity_id": entity_ids, "role": role, "ring_id": ring_id,
                           "signals": sig})
        for k, v in extra.items():
            df[k] = v
        self.truth.append(df)

    def truth_add_raw(self, scenario, entity_type, entity_ids, ring_id, role=""):
        """Entities that participate in a scenario (parties, people, employees) without their own fingerprints."""
        sc = self.cfg["scenarios"].get(scenario, {"layer": "FRAUD", "family": "ORGANIZED_RING"})
        ids = np.asarray(entity_ids, dtype=object)
        if len(ids) == 0:
            return
        self.truth.append(pd.DataFrame({"instance_id": self.ids.take(f"INS-{scenario[:4]}-", len(ids), 6), "scenario": scenario,
                                        "layer": sc["layer"], "family": sc["family"], "entity_type": entity_type,
                                        "entity_id": ids, "role": role, "ring_id": ring_id, "signals": ""}))

    def signals(self, scenario, n):
        """Independently sample each fingerprint of a scenario -> boolean DataFrame (n x signals)."""
        sig = self.cfg["scenarios"][scenario].get("signals", {})
        return pd.DataFrame({k: self.rng.random(n) < p for k, p in sig.items()})
