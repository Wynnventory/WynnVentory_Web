class Config:

    ENVIRONMENT = ''
    MIN_SUPPORTED_VERSION = ''

    # Database URIs
    PROD_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/wynnventory"
    DEV_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/wynnventory_DEV"
    ADMIN_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/wynnventory_admin"

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI
