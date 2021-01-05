import logging

from pymongo import MongoClient

from instruments.tools import MetaSingleton
from settings import settings

module_logger = logging.getLogger('my_bot')


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class Database(metaclass=MetaSingleton):
    """
    Connect with Mongo Database
    """
    _cluster = None

    def _connect(self):
        if not self._cluster:
            module_logger.debug('Initialisation database.')
            self._cluster = MongoClient(settings.BD_STRING)[settings.CLUSTER_NAME]
            module_logger.debug('Database connected.')
        return self._cluster

    @property
    def database(self):
        return self._connect()


