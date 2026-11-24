import numpy as np
import pandas as pd
from . import refdata as R

EPOCH = np.datetime64("1970-01-01")


def d2i(s):
    """ISO date string -> int days since epoch."""
    return int((np.datetime64(s) - EPOCH).astype(int))


def i2d(a):
    """int days (array) -> datetime64[D]."""
    return EPOCH + np.asarray(a).astype("timedelta64[D]")


def pick(rng, mapping, n):
    keys = list(mapping.keys())
    p = np.array(list(mapping.values()), dtype=float)
    p = p / p.sum()
    return np.array(keys, dtype=object)[rng.choice(len(keys), size=n, p=p)]


def band_lookup(bands, values):
    """bands like {'16-20': 2.3, ...}; values int array -> factor array."""
    out = np.ones(len(values))
    for k, v in bands.items():
        lo, hi = (int(x) for x in str(k).split("-"))
        out[(values >= lo) & (values <= hi)] = v
    return out


def lognormal(rng, mean, sigma, n):
    mu = np.log(mean) - sigma ** 2 / 2
    return rng.lognormal(mu, sigma, n)


class IdGen:
    def __init__(self):
        self.c = {}

    def take(self, prefix, n, width=8):
        start = self.c.get(prefix, 0)
        self.c[prefix] = start + n
        return np.array([f"{prefix}{i:0{width}d}" for i in range(start + 1, start + n + 1)], dtype=object)


# ---------------------------------------------------------------- geography
class Geo:
    def __init__(self, rng):
        self.rng = rng
        self.keys = list(R.METROS.keys())
        self.w = np.array([R.METROS[k][2] for k in self.keys]); self.w = self.w / self.w.sum()
        self.zips, self.zip_factor = {}, {}
        for k in self.keys:
            pre = R.METROS[k][5]
            pool = sorted({p + f"{rng.integers(1, 99):02d}" for p in pre for _ in range(14)})
            self.zips[k] = np.array(pool, dtype=object)
            self.zip_factor[k] = rng.uniform(0.86, 1.16, len(pool))

    def state(self, metro):
        return np.array([R.METROS[m][0] for m in metro], dtype=object)

    def city(self, metro):
        return np.array([R.METROS[m][1] for m in metro], dtype=object)

    def territory(self, metro):
        return np.array([R.METROS[m][3] for m in metro])

    def sample_metros(self, n):
        return np.array(self.keys, dtype=object)[self.rng.choice(len(self.keys), n, p=self.w)]

    def sample_zip(self, metro):
        metro = np.asarray(metro, dtype=object)
        z = np.empty(len(metro), dtype=object); f = np.ones(len(metro))
        for m in np.unique(metro):
            idx = np.where(metro == m)[0]
            j = self.rng.integers(0, len(self.zips[m]), len(idx))
            z[idx] = self.zips[m][j]; f[idx] = self.zip_factor[m][j]
        return z, f

    def phone(self, metro):
        metro = np.asarray(metro, dtype=object)
        out = np.empty(len(metro), dtype=object)
        for m in np.unique(metro):
            idx = np.where(metro == m)[0]
            ac = np.array(R.METROS[m][4])[self.rng.integers(0, len(R.METROS[m][4]), len(idx))]
            num = self.rng.integers(0, 10000, len(idx))
            out[idx] = [f"({a}) 555-{x:04d}" for a, x in zip(ac, num)]
        return out

    def street(self, n):
        num = self.rng.integers(10, 9990, n)
        st = np.array(R.STREET_NAMES, dtype=object)[self.rng.integers(0, len(R.STREET_NAMES), n)]
        sf = np.array(R.STREET_SUFFIX, dtype=object)[self.rng.integers(0, len(R.STREET_SUFFIX), n)]
        unit = np.where(self.rng.random(n) < 0.18, [f" Apt {x}" for x in self.rng.integers(1, 450, n)], "")
        return np.array([f"{a} {b} {c}{u}" for a, b, c, u in zip(num, st, sf, unit)], dtype=object)


# ---------------------------------------------------------------- VIN
_TRANS = {**{str(i): i for i in range(10)},
          **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))), "P": 7, "R": 9,
          **dict(zip("STUVWXYZ", range(2, 10)))}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
_VIN_CHARS = np.array(list("ABCDEFGHJKLMNPRSTUVWXYZ0123456789"))


def vin_check_digit(v):
    s = sum(_TRANS[c] * w for c, w in zip(v, _WEIGHTS))
    r = s % 11
    return "X" if r == 10 else str(r)


def make_vins(rng, wmi, years):
    n = len(wmi)
    vds = rng.choice(_VIN_CHARS, size=(n, 5))
    plant = rng.choice(_VIN_CHARS[:23], size=n)
    serial = rng.integers(100000, 999999, n)
    out = np.empty(n, dtype=object)
    for i in range(n):
        body = f"{wmi[i]}{''.join(vds[i])}0{R.VIN_YEAR_CODES[int(years[i])]}{plant[i]}{serial[i]}"
        out[i] = body[:8] + vin_check_digit(body) + body[9:]
    return out


def break_vin(rng, v):
    """Return a VIN whose check digit no longer validates."""
    cd = v[8]
    alt = [c for c in "0123456789X" if c != cd]
    return v[:8] + alt[rng.integers(len(alt))] + v[9:]


def vin_valid(v):
    try:
        return len(v) == 17 and vin_check_digit(v) == v[8]
    except KeyError:
        return False


def token(rng, prefix, n, digits=10):
    return np.array([f"{prefix}{x:0{digits}d}" for x in rng.integers(0, 10 ** digits, n, dtype=np.int64)], dtype=object)
