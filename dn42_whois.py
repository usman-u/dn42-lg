import subprocess
import ipaddress
import re


def hostname_regex(inp):
    if bool(
        re.match(
            r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$",
            inp,
        )
    ):
        return True
    return False


def validate_address(inp):
    try:
        ipaddress.ip_network(inp)
    except ValueError:
        return False
    return inp


def dn42_whois(target):
    if not validate_address(target) and not hostname_regex(target):
        return "Invalid input. Must be IPv4/v6 address/subnet, ASN, or hostname."
    return subprocess.run(
        ["whois", "-h", "172.22.0.43", target],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


# print(dn42_whois("map.dn42"))
# print(dn42_whois("172.22.132.160/27"))
