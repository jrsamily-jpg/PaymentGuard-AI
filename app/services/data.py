"""Load portable analytics artifacts; DB remains the source of investigation state."""

import json
from functools import lru_cache
import pandas as pd
from app.utils.config import DATA


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    file = DATA / "transactions.csv"
    if not file.exists():
        raise FileNotFoundError("Run python -m scripts.bootstrap first")
    return pd.read_csv(file, keep_default_na=False)


@lru_cache(maxsize=1)
def model_results() -> dict:
    return json.loads((DATA / "results.json").read_text())
