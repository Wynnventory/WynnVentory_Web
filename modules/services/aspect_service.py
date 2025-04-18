from modules.routes.api import wynncraft_api

class AspectService:
    def fetch_aspect(self, class_name: str, aspect_name: str) -> dict:
        return wynncraft_api.get_aspect_by_name(class_name, aspect_name)