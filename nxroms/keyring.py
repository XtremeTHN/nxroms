from typing import TypeVar
from pathlib import Path
from io import TextIOWrapper

PROD_KEYS_PATH = Path.home() / ".switch/prod.keys"

T = TypeVar("Keyring")


class KeysNotFound(Exception):
    pass


class InvalidKeys(Exception):
    pass


class Keyring:
    _instance: T = None

    key_area_application: list[str] = []
    key_area_ocean: list[str] = []
    key_area_system: list = []

    def __init__(self, key_path=None):
        if key_path:
            self.key_file = open(key_path, "r")
        else:
            if PROD_KEYS_PATH.exists() is False:
                raise KeysNotFound(
                    "Put your keys in ~/.switch/prod.keys before using this project"
                )

            if PROD_KEYS_PATH.is_file() is False:
                raise InvalidKeys("Invalid keys")

            self.key_file = PROD_KEYS_PATH.open()

        self.prod = self.parse(self.key_file)

    @classmethod
    def get_default(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def parse(self, file: TextIOWrapper):
        res = {}

        for line in file.readlines():
            key, val = line.split("=")

            if key.startswith("key_area_key_application_"):
                self.key_area_application.append(val)
                continue

            if key.startswith("key_area_key_ocean_"):
                self.key_area_ocean.append(val)
                continue

            if key.startswith("key_area_key_system_"):
                self.key_area_system.append(val)
                continue

            res[key.strip()] = val.strip()

        return res
