from datetime import datetime, timedelta


####################################################################################################
# Change icon names to match the ones in the icons folder
####################################################################################################
def map_local_icons(icon_name):
    mapping = {
        "helmet.png": "icons/helmet_diamond.webp",
        "leggings.png": "icons/leggings_diamond.webp",
        "boots.png": "icons/boots_diamond.webp",
        "chestplate.png": "icons/chestplate_diamond.webp",
        "ring.png": "icons/ring.webp",
        "bracelet.png": "icons/bracelet.webp",
        "necklace.png": "icons/necklace.webp",
        "helmet": "icons/helmet_diamond.webp",
        "leggings": "icons/leggings_diamond.webp",
        "boots": "icons/boots_diamond.webp",
        "chestplate": "icons/chestplate_diamond.webp",
        "ring": "icons/ring.webp",
        "bracelet": "icons/bracelet.webp",
        "necklace": "icons/necklace.webp"
    }
    return mapping.get(icon_name, icon_name)



def get_lootpool_week():
    """ Get the current Wynn week number and year. Lootpool resets every Friday at 6 PM Heroku time
    """
    now = datetime.utcnow() 
    reset_day = 4  # Friday
    reset_hour = 18  # 8 PM Switzerland, 6 PM Heroku

    days_since_reset = (now.weekday() - reset_day) % 7
    last_reset = now - timedelta(days=days_since_reset)

    if last_reset.weekday() == reset_day and now.hour < reset_hour:
        last_reset -= timedelta(days=7)

    last_reset = last_reset.replace(hour=reset_hour, minute=0, second=0, microsecond=0)

    wynn_week = last_reset.isocalendar().week
    wynn_year = last_reset.year

    print(f"Last reset: {last_reset}")
    print(f"Wynn week: {wynn_week}")
    print(f"Wynn year: {wynn_year}")
    return wynn_year, wynn_week