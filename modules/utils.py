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
        "necklace.png": "icons/necklace.webp"
    }
    return mapping.get(icon_name, icon_name)
