from django.apps import AppConfig

from .utils import check_config


class MainConfig(AppConfig):
    name = "main"

    def ready(self):
        check_config()
