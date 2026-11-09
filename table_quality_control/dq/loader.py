from __future__ import annotations
from pathlib import Path
import csv
import pandas as pd

SUPPORTED = {".csv", ".xlsx"}

def load_table(file, *, sheet_name=None, has_header=True, header_row=1,
               encoding="auto", delimiter="auto"):
    """Read an uploaded file or path. header_row is 1-based."""
    name = getattr(file, "name", str(file))
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Неподдерживаемый формат: {suffix or 'без расширения'}. Допустимы CSV и XLSX.")
    if suffix == ".xlsx":
        try:
            book = pd.ExcelFile(file)
            sheets = book.sheet_names
            selected = sheet_name or sheets[0]
            if selected not in sheets:
                raise ValueError(f"Лист '{selected}' не найден. Доступные листы: {', '.join(sheets)}")
            header = header_row - 1 if has_header else None
            df = pd.read_excel(book, sheet_name=selected, header=header, dtype=object)
            if not has_header:
                df.columns = [f"column_{i+1}" for i in range(len(df.columns))]
            return df, {"format": "XLSX", "sheet": selected, "encoding": None, "delimiter": None}
        except Exception as exc:
            raise ValueError(f"Не удалось прочитать XLSX: {exc}") from exc

    encodings = [encoding] if encoding != "auto" else ["utf-8-sig", "utf-8", "cp1251", "latin-1"]
    separators = [delimiter] if delimiter != "auto" else [",", ";", "\t"]
    last_error = None
    for enc in encodings:
        try:
            file.seek(0)
            raw = file.read()
            if isinstance(raw, bytes):
                text = raw.decode(enc)
            else:
                text = raw
            sep = delimiter
            if sep == "auto":
                try:
                    sep = csv.Sniffer().sniff(text[:10000], delimiters=",;\t").delimiter
                except csv.Error:
                    sep = ","
            from io import StringIO
            df = pd.read_csv(StringIO(text), sep=sep, header=0 if has_header else None, dtype=object)
            if not has_header:
                df.columns = [f"column_{i+1}" for i in range(len(df.columns))]
            return df, {"format": "CSV", "sheet": None, "encoding": enc, "delimiter": repr(sep)}
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Не удалось прочитать CSV. Проверьте кодировку и разделитель. Последняя ошибка: {last_error}")
