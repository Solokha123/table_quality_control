import pandas as pd

def clean_dataframe(df, rules=None, *, trim_spaces=True, convert_types=True,
                    remove_duplicates=False):
    """Return a cleaned copy; the input dataframe is never modified."""
    out = df.copy(deep=True)
    rules = rules or {}
    if trim_spaces:
        for col in out.select_dtypes(include=["object"]).columns:
            out[col] = out[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    if convert_types:
        for col, typ in rules.get("types", {}).items():
            if col not in out.columns: continue
            if typ in ("integer", "number"):
                values = pd.to_numeric(out[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
                if typ == "integer":
                    valid = values.isna() | (values % 1 == 0)
                    out.loc[valid, col] = values[valid].astype("Int64").astype(object)
                else:
                    out[col] = values
            elif typ == "date":
                out[col] = pd.to_datetime(out[col], errors="coerce", dayfirst=True)
    if remove_duplicates:
        out = out.drop_duplicates().reset_index(drop=True)
    return out
