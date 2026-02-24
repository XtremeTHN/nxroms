def is_all_zero(_bytes: bytes):
    return _bytes.count(0) == len(_bytes)


def media_to_bytes(media):
    return media * 0x200
