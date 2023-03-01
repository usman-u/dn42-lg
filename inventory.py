from net_automation import net_automation
import os


routers = {
    # router name:    API/SSH  instance.
    "fr_lil1": net_automation.Vyos(
        device_type="vyos",
        host="fr-lil1.usman.dn42",
        username="test",
        password=os.getenv("fr_lil1_password"),
        use_keys=False,
        url="https://fr-lil1.usman.dn42/graphql",
        key=os.getenv("apikey"),
    ),
    "us_ca1": net_automation.Vyos(
        device_type="vyos",
        host="us-ca1.usman.dn42",
        username="lg",
        password=os.getenv("us_ca1_password"),
        use_keys=False,
        url="https://us-ca1.usman.dn42/graphql",
        key=os.getenv("apikey"),
    ),
}
