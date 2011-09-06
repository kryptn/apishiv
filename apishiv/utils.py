def mask_check(accessmask, bit):
    """ Returns a bool indicating if the bit is set in the accessmask """
    mask = 1 << bit
    return (accessmask & mask) > 0

