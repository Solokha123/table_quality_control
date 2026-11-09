import pandas as pd
from dq.validator import validate_dataframe

RULES = {
    "required_columns": ["student_id", "age", "email", "group", "start_date", "end_date"],
    "allow_extra_columns": False, "min_columns": 6,
    "types": {"age": "integer", "start_date": "date", "end_date": "date"},
    "required_values": ["student_id", "group"], "unique": [["student_id"]],
    "email_columns": ["email"], "date_columns": ["start_date", "end_date"],
    "numeric_ranges": {"age": {"min": 16, "max": 100}},
    "non_negative": ["age"], "categories": {"group": ["A", "B", "C"]},
    "date_order": [{"start": "start_date", "end": "end_date"}]
}

def test_valid_file_has_no_issues(valid_df):
    result = validate_dataframe(valid_df, RULES)
    assert result["issues"].empty

def test_missing_required_value(valid_df):
    valid_df.loc[0, "student_id"] = ""
    result = validate_dataframe(valid_df, RULES)
    assert "required_value" in set(result["issues"]["rule"])

def test_duplicate_key(valid_df):
    valid_df.loc[1, "student_id"] = "1"
    result = validate_dataframe(valid_df, RULES)
    assert "duplicate_key" in set(result["issues"]["rule"])

def test_bad_email(valid_df):
    valid_df.loc[0, "email"] = "not-an-email"
    result = validate_dataframe(valid_df, RULES)
    assert "email" in set(result["issues"]["rule"])

def test_date_order(valid_df):
    valid_df.loc[0, "end_date"] = "01.01.2020"
    result = validate_dataframe(valid_df, RULES)
    assert "date_order" in set(result["issues"]["rule"])

def test_extra_column(valid_df):
    valid_df["unexpected"] = "x"
    result = validate_dataframe(valid_df, RULES)
    assert "extra_column" in set(result["issues"]["rule"])
