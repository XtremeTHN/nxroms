def media_to_bytes(media):
    return media * 0x200


def is_zeroes(data: bytes):
    return not any(data)


def bytes_default(data: bytes, default=None):
    return default if is_zeroes(data) else data
