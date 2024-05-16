import unicodedata

# from https://bugs.python.org/msg145523
W = {
'F': 2,  # full-width, width 2, compatibility character for a narrow char
'H': 1,  # half-width, width 1, compatibility character for a narrow char
'W': 2,  # wide, width 2
'Na': 1, # narrow, width 1
'A': 1,  # ambiguous; width 2 in Asian context, width 1 in non-Asian context
'N': 1,  #neutral; not used in Asian text, so has no width. Practically, width can be considered as 1
}

def get_width(s):
    # TODO:
    # - Handle embedded attributes
    return sum(W[unicodedata.east_asian_width(ch)] for ch in s)

def crop(s, width):
    '''Crop a string to a certain visual length.'''
    # TODO:
    # - Handle embedded attributes
    # - Ellipsis … ?
    o = 0
    l = 0
    for ch in s:
        w = W[unicodedata.east_asian_width(ch)]
        if l + w > width:
            break
        l += w
        o += 1

    return (s[0:o], l)

def pad(s, width, align):
    # TODO:
    # - Handle embedded attributes
    s, swidth = crop(s, width)
    padding = width - swidth
    if align == Align.LEFT:
        return s + (' ' * padding)
    elif align == Align.RIGHT:
        return (' ' * padding) + s
    elif align == Align.CENTER:
        return (' ' * (padding // 2)) + s + (' ' * ((padding + 1) // 2))
