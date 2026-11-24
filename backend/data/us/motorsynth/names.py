"""Name generation.

People: US Census frequency lists (1990 first names, 88,799 surnames) shipped with the
`names` package. Weights are *tempered* (w**alpha, alpha<1) so the head (James, Mary,
Tom, Jerry, Smith, Johnson ...) still dominates while the long tail is used far more,
which keeps full names close to unique at 1M+ people. A small, configurable rate of
genuine same-name collisions is kept on purpose: real books have two different
"Michael J Brown"s, and entity resolution should have to cope with that.
"""
import os
import numpy as np
import names as _names_pkg
from . import refdata as R

_DIR = os.path.dirname(_names_pkg.__file__)


def _load(fname):
    n, w = [], []
    for line in open(os.path.join(_DIR, fname)):
        parts = line.split()
        if len(parts) >= 2:
            n.append(parts[0]); w.append(float(parts[1]))
    w = np.array(w); w[w <= 0] = 0.0005
    return np.array(n, dtype=object), w


def _fix_case(s):
    s = s.title()
    if s.startswith("Mc") and len(s) > 2:
        s = "Mc" + s[2:].capitalize()
    elif s.startswith("Mac") and len(s) > 5 and s not in ("Mack", "Macy", "Mace", "Macon"):
        s = "Mac" + s[3:].capitalize()
    elif s.startswith("O") and len(s) > 3 and s[1:3] in ("Br", "Co", "Do", "Ma", "Ne", "Ha", "Ke"):
        pass
    return s


class NameFactory:
    def __init__(self, rng, alpha_first=0.70, alpha_last=0.55, allowed_dup_rate=0.0015):
        self.rng = rng
        self.alpha_last = alpha_last
        self.allowed_dup_rate = allowed_dup_rate
        mf, mw = _load("dist.male.first")
        ff, fw = _load("dist.female.first")
        ln, lw = _load("dist.all.last")
        self.first = {"M": (mf, self._p(mw, alpha_first)), "F": (ff, self._p(fw, alpha_first))}
        mod_w = np.linspace(1.0, 0.35, 20)
        self.modern = {"M": (np.array(R.MODERN_MALE, dtype=object), mod_w / mod_w.sum()),
                       "F": (np.array(R.MODERN_FEMALE, dtype=object), mod_w / mod_w.sum())}
        self.last_names, self.last_p = ln, self._p(lw, alpha_last)
        self._seen = {}

    @staticmethod
    def _p(w, a):
        w = np.power(w, a)
        return w / w.sum()

    def surnames(self, n):
        return self.rng.choice(self.last_names, size=n, p=self.last_p)

    def _firsts(self, gender, birth_year):
        n = len(gender)
        out = np.empty(n, dtype=object)
        for g in ("M", "F"):
            idx = np.where(gender == g)[0]
            if len(idx) == 0:
                continue
            nm, p = self.first[g]
            out[idx] = self.rng.choice(nm, size=len(idx), p=p)
            young = idx[(birth_year[idx] >= 1995) & (self.rng.random(len(idx)) < 0.28)]
            if len(young):
                mn, mp = self.modern[g]
                out[young] = self.rng.choice(mn, size=len(young), p=mp)
        return out

    def people(self, gender, birth_year, surname=None):
        """Return (first, middle, last, suffix) arrays; full names unique except a tiny allowed rate."""
        n = len(gender)
        gender = np.asarray(gender); birth_year = np.asarray(birth_year)
        first = self._firsts(gender, birth_year)
        middle = self._firsts(gender, birth_year)
        no_mid = self.rng.random(n) < 0.18
        middle[no_mid] = ""
        same = middle == first
        middle[same] = self._firsts(gender[same], birth_year[same])
        last = self.surnames(n) if surname is None else np.asarray(surname, dtype=object).copy()
        suffix = np.where((gender == "M") & (self.rng.random(n) < 0.012),
                          self.rng.choice(["Jr", "Sr", "II", "III"], size=n, p=[0.55, 0.2, 0.1, 0.15]), "")
        # uniqueness pass (first + middle initial + last); keep a small genuine-collision rate
        for _ in range(6):
            keys = [f"{a}|{b[:1]}|{c}" for a, b, c in zip(first, middle, last)]
            dup = np.zeros(n, dtype=bool)
            for i, k in enumerate(keys):
                if k in self._seen:
                    dup[i] = True
                else:
                    self._seen[k] = 1
            keep = self.rng.random(n) < (self.allowed_dup_rate * 4)
            redo = np.where(dup & ~keep)[0]
            if len(redo) == 0:
                break
            middle[redo] = self._firsts(gender[redo], birth_year[redo])
            if surname is None:
                last[redo] = self.surnames(len(redo))
            else:
                first[redo] = self._firsts(gender[redo], birth_year[redo])
        f = np.array([_fix_case(x) for x in first], dtype=object)
        m = np.array([_fix_case(x) if x else "" for x in middle], dtype=object)
        l = np.array([_fix_case(x) for x in last], dtype=object)
        return f, m, l, suffix


class BizNameFactory:
    def __init__(self, rng, name_factory):
        self.rng = rng
        self.nf = name_factory
        self.used = set()

    def make(self, kind, city):
        tmpls = R.BIZ_TEMPLATES[kind]
        for attempt in range(30):
            t = tmpls[self.rng.integers(len(tmpls))]
            s, s2 = (_fix_case(x) for x in self.nf.surnames(2))
            f = _fix_case(self.nf.first["M" if self.rng.random() < 0.6 else "F"][0][self.rng.integers(200)])
            w = R.BIZ_WORDS[self.rng.integers(len(R.BIZ_WORDS))]
            name = t.format(s=s, s2=s2, w=w, f=f)
            if attempt > 10:
                name = f"{name} of {city}"
            if name not in self.used:
                self.used.add(name)
                return name
        name = f"{name} #{len(self.used)}"
        self.used.add(name)
        return name
