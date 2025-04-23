from modules.routes.api import wynncraft_api


def fetch_aspect(class_name: str, aspect_name: str) -> dict:
    """
    Fetch a single aspect by class name and aspect name from the Wynncraft API.

    Args:
        class_name (str): The name of the class (e.g., 'warrior', 'mage')
        aspect_name (str): The name of the aspect to fetch

    Returns:
        dict: The aspect data as a dictionary
    """
    return wynncraft_api.get_aspect_by_name(class_name, aspect_name)
