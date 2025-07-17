from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    """
    Creates the TgBot object from environment variables.
    """

    token: str
    admin_ids: list[int]
    manager_ids: list[int]
    use_redis: bool

    @staticmethod
    def from_env(env: Env):
        """
        Creates the TgBot object from environment variables.
        """
        token = env.str("BOT_TOKEN")
        admin_ids = env.list("ADMIN_IDS", subcast=int)
        manager_ids = env.list("MANAGER_IDS", subcast=int)
        use_redis = env.bool("USE_REDIS")
        return TgBot(token=token,
                     admin_ids=admin_ids,
                     manager_ids=manager_ids,
                     use_redis=use_redis)


@dataclass
class Miscellaneous:
    """
    Miscellaneous configuration class.

    This class holds settings for various other parameters.
    It merely serves as a placeholder for settings that are not part of other categories.

    Attributes
    ----------
    other_params : str, optional
        A string used to hold other various parameters as required (default is None).
    """

    other_params: str = None


@dataclass
class Config:
    """
    The main configuration class that integrates all the other configuration classes.

    This class holds the other configuration classes, providing a centralized point of access for all settings.

    Attributes
    ----------
    tg_bot : TgBot
        Holds the settings related to the Telegram Bot.
    misc : Miscellaneous
        Holds the values for miscellaneous settings.
    """

    tg_bot: TgBot
    misc: Miscellaneous


def load_config(path: str = None) -> Config:
    """
    This function takes an optional file path as input and returns a Config object.
    :param path: The path of env file from where to load the configuration variables.
    It reads environment variables from a .env file if provided, else from the process environment.
    :return: Config object with attributes set as per environment variables.
    """

    # Create an Env object.
    # The Env object will be used to read environment variables.
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot.from_env(env),
        misc=Miscellaneous(),
    )
