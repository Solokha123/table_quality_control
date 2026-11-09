from io import BytesIO
import pandas as pd

def build_excel_report(df, result):
    buffer = BytesIO()
    summary = result["summary"]
    summary_rows = [{"metric": k, "value": str(v)} for k, v in summary.items()]
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="Summary")
        result["issues"].to_excel(writer, index=False, sheet_name="Issues")
        pd.DataFrame([{"column": k, "completeness_percent": v}
                      for k, v in result["completeness"].items()]).to_excel(writer, index=False, sheet_name="Completeness")
        df.to_excel(writer, index=False, sheet_name="Checked data")
    buffer.seek(0)
    return buffer.getvalue()

def dataframe_to_xlsx(df, sheet="Cleaned data"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet[:31])
    buffer.seek(0)
    return buffer.getvalue()
