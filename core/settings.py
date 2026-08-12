import json
import os


def _settings_path() -> str:
    app_data = os.path.join(os.path.expanduser("~"), ".zhuibook")
    os.makedirs(app_data, exist_ok=True)
    return os.path.join(app_data, "settings.json")


_DEFAULT_SETTINGS = {
    "bg_image_path": "",
    "bg_image_alpha": 0.18,
    "private_password_hash": "",
}


def load_settings() -> dict:
    path = _settings_path()
    data = dict(_DEFAULT_SETTINGS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data.update(loaded)
        except Exception:
            pass
    if "bg_image_alpha" in data:
        try:
            a = float(data["bg_image_alpha"])
            a = max(0.0, min(1.0, a))
            data["bg_image_alpha"] = a
        except Exception:
            data["bg_image_alpha"] = 0.18
    if "bg_image_path" not in data:
        data["bg_image_path"] = ""
    return data


def save_settings(**kwargs) -> dict:
    current = load_settings()
    for k, v in kwargs.items():
        if k == "bg_image_alpha":
            try:
                v = float(v)
                v = max(0.0, min(1.0, v))
            except Exception:
                continue
        current[k] = v
    path = _settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return current
