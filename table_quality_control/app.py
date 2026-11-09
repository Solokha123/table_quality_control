import json
from pathlib import Path
import streamlit as st
import pandas as pd
from dq.loader import load_table
from dq.rules import load_rules
from dq.validator import validate_dataframe
from dq.cleaner import clean_dataframe
from dq.reporting import build_excel_report, dataframe_to_xlsx
from dq.history import save_run

st.set_page_config(page_title="Контроль качества данных", page_icon="🔎", layout="wide")
st.title("🔎 Система контроля качества табличных данных")
st.caption("Проверка CSV/XLSX по настраиваемым правилам. Исходный файл не изменяется.")

with st.sidebar:
    st.header("1. Загрузка")
    uploaded = st.file_uploader("Выберите CSV или XLSX", type=["csv", "xlsx"])
    has_header = st.checkbox("Первая строка — заголовки", value=True)
    header_row = st.number_input("Номер строки заголовка (Excel/CSV)", min_value=1, value=1)
    encoding = st.selectbox("Кодировка CSV", ["auto", "utf-8-sig", "utf-8", "cp1251", "latin-1"])
    delimiter = st.selectbox("Разделитель CSV", ["auto", ",", ";", "\\t"])
    sheet_name = None
    if uploaded and uploaded.name.lower().endswith(".xlsx"):
        try:
            xls = pd.ExcelFile(uploaded)
            sheet_name = st.selectbox("Лист Excel", xls.sheet_names)
        except Exception as e:
            st.error(f"Не удалось прочитать список листов: {e}")
    st.divider()
    st.header("2. Правила")
    rule_file = st.file_uploader("Загрузить правила JSON/YAML", type=["json", "yaml", "yml"])
    use_default = st.checkbox("Использовать встроенный шаблон", value=False)

if not uploaded:
    st.info("Загрузите CSV или XLSX-файл в боковой панели.")
    st.stop()

try:
    uploaded.seek(0)
    df, meta = load_table(uploaded, sheet_name=sheet_name, has_header=has_header,
                          header_row=int(header_row), encoding=encoding, delimiter=delimiter)
    st.success(f"Файл прочитан: {meta['format']}; строк: {len(df)}; столбцов: {len(df.columns)}")
    with st.expander("Предпросмотр данных", expanded=True):
        st.dataframe(df.head(100), use_container_width=True)
except Exception as e:
    st.error(str(e))
    st.stop()

try:
    if rule_file:
        rules = load_rules(rule_file)
    elif use_default:
        rules = load_rules(Path("config/default_rules.yaml"))
    else:
        rules = load_rules({})
except Exception as e:
    st.error(f"Ошибка конфигурации правил: {e}")
    st.stop()

st.subheader(f"Шаблон: {rules.get('name', 'Без названия')}")
if st.button("▶ Запустить проверку", type="primary"):
    result = validate_dataframe(df, rules)
    st.session_state["dq_result"] = result
    st.session_state["dq_df"] = df.copy(deep=True)
    st.session_state["dq_rules"] = rules
    ok, msg = save_run(result["summary"], uploaded.name)
    if ok: st.success(msg)
    elif "не задан" not in msg: st.warning(msg)

if "dq_result" in st.session_state:
    result = st.session_state["dq_result"]
    summary = result["summary"]
    st.divider()
    st.subheader("Сводные показатели")
    c = st.columns(5)
    metrics = [
        ("Записей", summary["records"]), ("Столбцов", summary["columns"]),
        ("Строк с ошибками", summary["rows_with_errors"]),
        ("Дубликатов строк", summary["duplicate_rows"]), ("Качество", f"{summary['quality_score']}%")
    ]
    for box, (label, value) in zip(c, metrics): box.metric(label, value)
    st.metric("Средняя заполненность", f"{summary['overall_completeness']}%")
    st.subheader("Заполненность по столбцам")
    st.dataframe(pd.DataFrame([{"Столбец": k, "Заполненность, %": v}
                               for k, v in result["completeness"].items()]), use_container_width=True)
    st.subheader("Ошибки")
    issues = result["issues"]
    if issues.empty:
        st.success("Нарушений не обнаружено.")
    else:
        f1, f2, f3 = st.columns(3)
        severity = f1.multiselect("Критичность", sorted(issues["severity"].dropna().unique()), default=list(issues["severity"].dropna().unique()))
        columns = f2.multiselect("Столбцы", sorted(issues["column"].dropna().astype(str).unique()))
        rule_names = f3.multiselect("Правила", sorted(issues["rule"].dropna().unique()))
        filtered = issues[issues["severity"].isin(severity)]
        if columns: filtered = filtered[filtered["column"].astype(str).isin(columns)]
        if rule_names: filtered = filtered[filtered["rule"].isin(rule_names)]
        st.dataframe(filtered, use_container_width=True, height=350)
        st.download_button("Скачать список ошибок CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
                           file_name="quality_issues.csv", mime="text/csv")
    report_bytes = build_excel_report(st.session_state["dq_df"], result)
    st.download_button("📥 Скачать полный отчёт Excel", report_bytes,
                       file_name="quality_report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()
    st.subheader("Подготовка очищенной копии")
    st.warning("Будет создан отдельный файл. Исходная загрузка не изменяется.")
    a, b, c = st.columns(3)
    trim = a.checkbox("Удалить пробелы по краям", value=True)
    convert = b.checkbox("Преобразовать типы по правилам", value=True)
    remove_dups = c.checkbox("Удалить полные дубликаты", value=False)
    if remove_dups:
        st.error("Удаление строк необратимо для создаваемой копии. Подтвердите действие.")
        confirm = st.checkbox("Подтверждаю удаление полностью дублирующихся строк")
    else:
        confirm = False
    if st.button("Подготовить очищенный файл"):
        cleaned = clean_dataframe(st.session_state["dq_df"], st.session_state["dq_rules"],
                                  trim_spaces=trim, convert_types=convert,
                                  remove_duplicates=remove_dups and confirm)
        st.session_state["dq_cleaned"] = cleaned
        st.success(f"Подготовлена копия: {len(cleaned)} строк.")
    if "dq_cleaned" in st.session_state:
        st.download_button("📥 Скачать очищенную копию XLSX",
                           dataframe_to_xlsx(st.session_state["dq_cleaned"]),
                           file_name="cleaned_data.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
