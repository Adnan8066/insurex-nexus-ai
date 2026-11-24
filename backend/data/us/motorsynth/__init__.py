import pandas as pd

# keep plain object strings (numpy-friendly) on pandas >= 3
try:
    pd.set_option("future.infer_string", False)
except Exception:
    pass
