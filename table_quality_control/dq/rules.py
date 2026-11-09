from pathlib import Path
import json
import yaml

DEFAULT_RULES = {
    "name": "Без шаблона", "required_columns": [], "allow_extra_columns": True,
    "min_columns": 1, "types": {}, "required_values": [], "unique": [],
    "email_columns": [], "date_columns": [], "numeric_ranges": {},
    "non_negative": [], "categories": {}, "date_order": []
}

def load_rules(source):
    if isinstance(source, dict):
        data = source
    else:
        name = getattr(source, "name", str(source))
        text = source.read()
        if isinstance(text, bytes):
            text = text.decode("utf-8-sig")
        suffix = Path(name).suffix.lower()
        if suffix == ".json":
            data = json.loads(text)
        elif suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text) or {}
        else:
            raise ValueError("Файл правил должен иметь расширение JSON, YAML или YML.")
    if not isinstance(data, dict):
        raise ValueError("Корень конфигурации правил должен быть объектом.")
    rules = {**DEFAULT_RULES, **data}
    for key in ("required_columns", "required_values", "email_columns", "date_columns", "non_negative", "unique", "date_order"):
        if rules.get(key) is None:
            rules[key] = []
    if not isinstance(rules["types"], dict) or not isinstance(rules["numeric_ranges"], dict):
        raise ValueError("Поля types и numeric_ranges должны быть объектами.")
    return rules
