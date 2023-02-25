import ipaddress

def is_valid_address(addr):
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False