class Config:

    ENVIRONMENT = ''

    # Database URIs
    PROD_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/"
    DEV_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/wynnventory_DEV"

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI

    @classmethod
    def set_environment(cls, env):
        if env not in ["prod", "dev"]:
            raise ValueError("Environment must be either 'prod' or 'dev'")
        cls.ENVIRONMENT = env
