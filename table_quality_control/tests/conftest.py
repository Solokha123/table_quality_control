import pandas as pd
import pytest

@pytest.fixture
def valid_df():
    return pd.DataFrame({
        "student_id": ["1", "2"], "age": ["20", "21"],
        "email": ["a@example.com", "b@example.com"], "group": ["A", "B"],
        "start_date": ["01.09.2024", "02.09.2024"],
        "end_date": ["10.09.2024", "12.09.2024"]
    })
