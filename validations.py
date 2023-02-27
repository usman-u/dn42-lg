import ipaddress

def is_valid_address(addr):
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False

def is_valid_network(addr):
    try:
        ipaddress.ip_network(addr)
        return True
    except ValueError:
        return False