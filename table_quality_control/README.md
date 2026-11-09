# Универсальная система контроля качества табличных данных

Веб-приложение на Python/Streamlit для анализа CSV и XLSX, проверки структуры и значений по JSON/YAML-правилам, формирования Excel-отчётов и безопасной подготовки очищенной копии данных.

## Возможности

- CSV: UTF-8, UTF-8-SIG, CP1251, Latin-1; разделители `,`, `;`, табуляция и автоопределение.
- XLSX: выбор листа, настройка заголовка и номера строки заголовка.
- Проверки структуры: обязательные/лишние/неизвестные/повторяющиеся столбцы, минимальный набор полей, типы.
- Проверки значений: полнота, обязательные значения, дубликаты строк и ключей, даты, числа, email, категории, диапазоны, запрет отрицательных значений, межполевая дата.
- Правила в JSON/YAML без изменения кода.
- Отчёт Excel с листами `Summary`, `Issues`, `Completeness`, `Checked data`.
- Очистка только копии: пробелы, безопасное преобразование типов/дат, удаление полных дубликатов только по подтверждению.
- Набор из шести тестовых CSV и автоматические тесты.
- Необязательное сохранение истории в PostgreSQL через `DATABASE_URL`.

## Запуск

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Откройте URL, который покажет Streamlit (обычно http://localhost:8501).

## Правила

В интерфейсе можно загрузить JSON/YAML или выбрать `config/default_rules.yaml`.
Пример:

```yaml
name: Student registry
required_columns: [student_id, age, email, group, start_date, end_date]
allow_extra_columns: false
min_columns: 5
types:
  student_id: string
  age: integer
  start_date: date
  end_date: date
required_values: [student_id, group]
unique:
  - [student_id]
email_columns: [email]
date_columns: [start_date, end_date]
numeric_ranges:
  age: {min: 16, max: 100}
non_negative: [age]
categories:
  group: [A, B, C]
date_order:
  - start: start_date
    end: end_date
```

Поддерживаемые типы: `string`, `integer`, `number`, `date`, `boolean`.
`date_formats` можно задать для отдельных столбцов, например:
`date_formats: {start_date: "%d.%m.%Y"}`.

## PostgreSQL (необязательно)

Задайте переменную окружения `DATABASE_URL`, например:

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/data_quality"
```

При наличии переменной приложение создаёт таблицу `validation_runs` и сохраняет сводку каждой проверки. Если БД недоступна, анализ не прерывается — приложение показывает предупреждение.

## Структура

```text
app.py
dq/
  loader.py       # чтение CSV/XLSX
  rules.py        # загрузка и проверка конфигурации
  validator.py    # проверки качества
  cleaner.py      # безопасная очистка копии
  reporting.py    # Excel-отчёт
  history.py      # необязательная история PostgreSQL
config/default_rules.yaml
sample_data/      # 6 демонстрационных CSV
tests/
```

## Запуск тестов

```bash
pytest -q
```

## Важные оговорки

- Номер строки в отчёте соответствует строке исходного файла (для таблицы с заголовком первая запись обычно начинается со строки 2).
- Пустыми считаются `NaN`, пустые строки и строки из пробелов.
- Для неоднозначных исправлений автоматическое изменение не выполняется. Очистка не перезаписывает исходный файл.
- Интегральный индекс качества рассчитывается как `100 × (1 − взвешенная доля нарушений)`, ограничивается диапазоном 0–100. Веса: critical=5, error=3, warning=1; знаменатель — число проверенных ячеек/строковых правил с минимальным значением 1. Индекс является диагностическим показателем, а не отраслевым стандартом.
