from colorama import Fore, Style


def color(string, color):
    return color + str(string) + Fore.RESET


def colored(*msg, color=Fore.GREEN, level=""):
    print(color + Style.BRIGHT + str(level) + Style.RESET_ALL, *msg)


def color_ctx(prefix):
    def wrapper(*msg, color=Fore.GREEN, level=""):
        colored(*msg, color=color, level=str(prefix) + str(level))

    return wrapper


def info(*msg):
    colored(*msg, level="INFO")


def is_all_zero(_bytes: bytes):
    return _bytes.count(0) == len(_bytes)


def media_to_bytes(media):
    return media * 0x200
