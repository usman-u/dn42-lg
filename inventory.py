from net_automation import net_automation
import os


routers = {
    # router name:    API/SSH  instance.
    "fr_lil1": net_automation.Vyos(
        device_type="vyos",
        host="172.22.132.167",
        username="test",
        password=os.getenv("fr_lil1_password"),
        use_keys=False,
        url="https://172.22.132.167/graphql",
        key=os.getenv("apikey"),
    ),
    "us_ca1": net_automation.Vyos(
        device_type="vyos",
        host="172.22.132.164",
        username="test",
        password=os.getenv("us_ca1_password"),
        use_keys=False,
        url="https://172.22.132.164/graphql",
        key=os.getenv("apikey"),
    ),
}
