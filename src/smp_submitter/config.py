import logging
import os
import sys

from .consts import DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT


LOG = logging.getLogger(__name__)


class Config:
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', None)
    GITHUB_NAME = os.environ.get('GITHUB_NAME', None)
    GITHUB_EMAIL = os.environ.get('GITHUB_EMAIL', None)
    API_TOKEN = os.environ.get('API_TOKEN', None)
    LOG_LEVEL = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL)
    LOG_FORMAT = os.environ.get('LOG_FORMAT', DEFAULT_LOG_FORMAT)

    @classmethod
    def check(cls):
        if cls.GITHUB_TOKEN is None:
            print('GITHUB_TOKEN env variable is missing!')
            sys.exit(1)
        if cls.GITHUB_NAME is None:
            print('GITHUB_NAME env variable is missing!')
            sys.exit(1)
        if cls.GITHUB_EMAIL is None:
            print('GITHUB_EMAIL env variable is missing!')
            sys.exit(1)

    @classmethod
    def apply_logging(cls):
        logging.basicConfig(
            level=cls.LOG_LEVEL,
            format=cls.LOG_FORMAT,
        )
        LOG.debug('Logging configured...')
