from instruments.database.captain_col import CaptainCollection
from instruments.database.settings_col import SettingsCollection
from instruments.database.user_col import UserCollection


class DatabaseManager:
    def __init__(self):
        self.user = UserCollection()
        self.captain = CaptainCollection()
        self.settings = SettingsCollection()