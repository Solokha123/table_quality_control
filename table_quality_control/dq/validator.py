from __future__ import annotations
import re
import pandas as pd
from collections import Counter

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")

def _empty(v):
    return pd.isna(v) or (isinstance(v, str) and not v.strip())

def _issue(row, column, rule, message, severity="error"):
    return {"row": row, "column": column, "rule": rule, "severity": severity, "message": message}

def _to_number(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")

def validate_dataframe(df: pd.DataFrame, rules: dict):
    issues = []
    cols = list(df.columns)
    col_counts = Counter(str(c) for c in cols)

    # Structure
    for c in rules.get("required_columns", []):
        if c not in cols:
            issues.append(_issue(None, c, "required_column", f"Отсутствует обязательный столбец: {c}", "critical"))
    duplicates = [c for c, n in col_counts.items() if n > 1]
    for c in duplicates:
        issues.append(_issue(None, c, "duplicate_header", f"Повторяющийся заголовок: {c}", "critical"))
    if len(cols) < int(rules.get("min_columns", 1)):
        issues.append(_issue(None, None, "min_columns", f"Ожидалось минимум {rules['min_columns']} столбцов, найдено {len(cols)}", "critical"))
    if not rules.get("allow_extra_columns", True):
        extra = [c for c in cols if c not in rules.get("required_columns", []) and c not in rules.get("types", {})]
        for c in extra:
            issues.append(_issue(None, c, "extra_column", f"Лишний столбец: {c}", "warning"))

    # Column type checks
    for col, expected in rules.get("types", {}).items():
        if col not in df.columns:
            continue
        for i, v in df[col].items():
            if _empty(v): continue
            ok = True
            if expected == "string": ok = isinstance(v, str)
            elif expected == "integer":
                n = pd.to_numeric(str(v).replace(",", "."), errors="coerce")
                ok = pd.notna(n) and float(n).is_integer()
            elif expected == "number":
                ok = pd.notna(pd.to_numeric(str(v).replace(",", "."), errors="coerce"))
            elif expected == "date":
                ok = pd.notna(pd.to_datetime(v, errors="coerce", dayfirst=True))
            elif expected == "boolean":
                ok = str(v).strip().lower() in {"true", "false", "1", "0", "да", "нет", "yes", "no"}
            else:
                issues.append(_issue(None, col, "invalid_rule_type", f"Неизвестный тип правила: {expected}", "warning"))
                break
            if not ok:
                issues.append(_issue(int(i)+2, col, "type", f"Ожидался тип {expected}, получено: {v!r}"))

    # Completeness and required values
    completeness = {}
    for col in cols:
        missing = df[col].map(_empty)
        completeness[str(col)] = round(float((~missing).mean() * 100), 2) if len(df) else 100.0
        for i in df.index[missing]:
            issues.append(_issue(int(i)+2, col, "empty", "Пустое значение"))
    for col in rules.get("required_values", []):
        if col in df.columns:
            for i in df.index[df[col].map(_empty)]:
                issues.append(_issue(int(i)+2, col, "required_value", "Обязательное значение отсутствует", "critical"))

    # Duplicate rows and key uniqueness
    dup_mask = df.duplicated(keep=False)
    for i in df.index[dup_mask]:
        issues.append(_issue(int(i)+2, None, "duplicate_row", "Полностью повторяющаяся строка", "warning"))
    for key_cols in rules.get("unique", []):
        if isinstance(key_cols, str): key_cols = [key_cols]
        missing_cols = [c for c in key_cols if c not in df.columns]
        if missing_cols:
            issues.append(_issue(None, ",".join(missing_cols), "invalid_unique_rule", "Ключевые столбцы правила уникальности отсутствуют", "warning"))
            continue
        mask = df.duplicated(subset=key_cols, keep=False)
        for i in df.index[mask]:
            issues.append(_issue(int(i)+2, ",".join(key_cols), "duplicate_key", f"Дубликат по ключу: {', '.join(key_cols)}"))

    # Email, dates, categories
    for col in rules.get("email_columns", []):
        if col in df.columns:
            for i, v in df[col].items():
                if not _empty(v) and not EMAIL_RE.match(str(v).strip()):
                    issues.append(_issue(int(i)+2, col, "email", f"Некорректный email: {v!r}"))
    for col in rules.get("date_columns", []):
        if col in df.columns:
            for i, v in df[col].items():
                if not _empty(v) and pd.isna(pd.to_datetime(v, errors="coerce", dayfirst=True)):
                    issues.append(_issue(int(i)+2, col, "date", f"Некорректная дата: {v!r}"))
    for col, allowed in rules.get("categories", {}).items():
        if col in df.columns:
            allowed_norm = {str(x).strip().casefold() for x in allowed}
            for i, v in df[col].items():
                if not _empty(v) and str(v).strip().casefold() not in allowed_norm:
                    issues.append(_issue(int(i)+2, col, "category", f"Недопустимое значение {v!r}; разрешено: {', '.join(map(str, allowed))}"))

    # Numeric ranges and non-negative
    for col, bounds in rules.get("numeric_ranges", {}).items():
        if col not in df.columns: continue
        nums = _to_number(df[col])
        for i, v in nums.items():
            if _empty(df.at[i, col]): continue
            if pd.isna(v):
                issues.append(_issue(int(i)+2, col, "number", f"Ожидалось число, получено: {df.at[i, col]!r}"))
            else:
                if bounds.get("min") is not None and v < bounds["min"]:
                    issues.append(_issue(int(i)+2, col, "min_value", f"Значение {v} меньше минимума {bounds['min']}"))
                if bounds.get("max") is not None and v > bounds["max"]:
                    issues.append(_issue(int(i)+2, col, "max_value", f"Значение {v} больше максимума {bounds['max']}"))
    for col in rules.get("non_negative", []):
        if col in df.columns:
            nums = _to_number(df[col])
            for i, v in nums.items():
                if not _empty(df.at[i, col]) and pd.notna(v) and v < 0:
                    issues.append(_issue(int(i)+2, col, "negative", "Отрицательное значение запрещено"))

    # Cross-field date order
    for rule in rules.get("date_order", []):
        start, end = rule.get("start"), rule.get("end")
        if start not in df.columns or end not in df.columns:
            issues.append(_issue(None, f"{start}/{end}", "invalid_date_order_rule", "Столбцы правила сравнения дат отсутствуют", "warning"))
            continue
        starts = pd.to_datetime(df[start], errors="coerce", dayfirst=True)
        ends = pd.to_datetime(df[end], errors="coerce", dayfirst=True)
        for i in df.index[starts.notna() & ends.notna() & (ends < starts)]:
            issues.append(_issue(int(i)+2, end, "date_order", f"{end} не может быть раньше {start}"))

    issue_df = pd.DataFrame(issues, columns=["row", "column", "rule", "severity", "message"])
    bad_rows = issue_df["row"].dropna().nunique() if not issue_df.empty else 0
    duplicates_count = int(df.duplicated(keep=False).sum())
    checked_cells = max(1, len(df) * max(1, len(cols)))
    weighted = sum({"critical": 5, "error": 3, "warning": 1}.get(s, 3) for s in issue_df["severity"]) if not issue_df.empty else 0
    quality = round(max(0, 100 * (1 - weighted / checked_cells)), 2)
    summary = {
        "records": len(df), "columns": len(cols), "rows_with_errors": int(bad_rows),
        "duplicate_rows": duplicates_count, "issues": len(issue_df),
        "quality_score": quality,
        "overall_completeness": round(sum(completeness.values()) / len(completeness), 2) if completeness else 100.0,
        "by_severity": issue_df["severity"].value_counts().to_dict() if not issue_df.empty else {},
        "by_rule": issue_df["rule"].value_counts().to_dict() if not issue_df.empty else {}
    }
    return {"issues": issue_df, "completeness": completeness, "summary": summary}
