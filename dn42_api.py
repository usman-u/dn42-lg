import requests
import re


def aut_num_exists(aut_num):

    aut_num = aut_num.upper()

    url = f"https://explorer.dn42.dev/api/registry/aut-num/{aut_num}"
    response = requests.get(url)

    if response.status_code == 404:
        return False
    return True


def get_aut_num_bgp_persons(aut_num):
    """Returns person values as a string, given a DN42 ASN"""

    aut_num = aut_num.upper()

    url = f"https://explorer.dn42.dev/api/registry/aut-num/{aut_num}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        attributes = data.get(f"aut-num/{aut_num}").get('Attributes')

        person = []

        # Loops through every attribute in the parsed BGP attributes list,
        # Splits the attribute twice, to remove chars before the first '/' and after
        # the next ')'. E.g. ['admin-c', '[C4TG1RL5-DN42](person/C4TG1RL5-DN42)'] --> C4TG1RL5-DN42.
        # and stores it in a the string "person". 
        # If the attribute's index 0 is "admin-c" or "email-c" AND 
        # isn't already in the current_person
        # Add it to the person array.

        for attr in attributes:

            if (attr[0] == "admin-c" or attr[0] == "tech-c"):
                current_person = (attr[1].split("/")[1].split(")")[0])

                if current_person not in person:

                    person.append(current_person)
        return person

    else:
        print("Request failed with status code:", response.status_code)
        
def get_persons_emails(admins):

    emails = []
    email_found = False
    # print(admins)

    for admin in admins:
        print(admin)
        url = f"https://explorer.dn42.dev/api/registry/person/{admin}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            attributes = data.get(f"person/{admin}").get('Attributes')


            for attribute in attributes:
                if attribute[0] == "e-mail":
                    emails.append(attribute[1])
                    email_found = True
        
        else:
            print("Request failed with status code:", response.status_code)
    
    if not email_found:
        return False

    return emails
