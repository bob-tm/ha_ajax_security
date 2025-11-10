'''Get ip name from url.'''
def strip_ip(url: str):
    """Strip IP/Hostname from URL."""
    try:
        return url.split("/")[2].split(":")[0]
    except:
        return url
