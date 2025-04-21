from modules.routes.api import wynncraft_api


def fetch_aspect(class_name: str, aspect_name: str) -> dict:
    return wynncraft_api.get_aspect_by_name(class_name, aspect_name)
