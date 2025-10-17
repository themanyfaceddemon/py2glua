from .realm import Realm


class PY2GLUA_DEBUG:
    """Переменная отвечающая за дебаг сборку"""

    value = False


__all__ = ["Realm", "PY2GLUA_DEBUG"]
