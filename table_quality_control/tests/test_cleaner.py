from dq.cleaner import clean_dataframe

def test_cleaner_does_not_mutate_source(valid_df):
    original = valid_df.copy(deep=True)
    cleaned = clean_dataframe(valid_df, {"types": {}}, trim_spaces=True)
    assert valid_df.equals(original)
    assert cleaned is not valid_df

def test_trim_and_remove_duplicates():
    import pandas as pd
    df = pd.DataFrame({"name": [" A ", " A "]})
    out = clean_dataframe(df, {}, trim_spaces=True, remove_duplicates=True)
    assert len(out) == 1
    assert out.iloc[0, 0] == "A"
