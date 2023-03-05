# dn42-lg

* A Python Flask Web Application Looking Glass for VyOS.
* Uses a mix of VyOS's GraphQL API and SSH to get data (through my [network-automation](https://github.com/usman-u/network-automation) library).
* Live at [https://lg.usman.network](https://lg.usman.network)

---

# Usage/Developer Notes
## Create Virtual Environment, clone repo, and install dependencies.
```bash
conda create -n dn42-lg
conda activate dn42-lg
git clone https://github.com/usman-u/dn42-lg.git
poetry install
```
* The same should work with virtualenv and pip.
## VSCode Remote
* If using VSCode SSH remote, change interpreter to conda env python path.

e.g. `/home/usman/miniconda3/envs/dn42-lg/bin/python3`

Confirm with `which python3`

```bash
(dn42-lg) usman@dev-usman-lan:~/projects/dn42-lg$ which python3
/home/usman/miniconda3/envs/flask-bgp-lg/bin/python3
```

## Device Inventory
* Modify `inventory.py` to include your devices.
* It's a dictionary of OOP instances from my `network-automation` library.
* Use `os.getenv()` to get environment variables.
```python
from net_automation import net_automation
import os

routers = {
    # router name:    API/SSH  instance.
    "fr_lil1": net_automation.Vyos(
        device_type="vyos",
        host="fr-lil1.usman.dn42",
        username="username",
        password=os.getenv("fr_lil1_password"),
        use_keys=False,
        url="https://fr-lil1.usman.dn42/graphql",
        key=os.getenv("apikey"),
    ),
}
```
## Environmental Variables
* A `.env` file should be created.
* The `.env` file should be added to `.gitignore`.
* The `.env` file must include the flask secret key.
```
apikey = xxxx
fr_lil1_password = xxx
us_ca1_password = xxx
flask_secret_key = xxx
```

## Running the Flask Development Server
```bash
(dn42-lg) usman@dev-usman-lan:~/projects/dn42-lg$ python main.py 
 * Serving Flask app 'main'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.10.5:5000
Press CTRL+C to quit
```
---


# Deploying the Flask Application
* Flask Apps can be deployed in a variety of ways.
* I deployed it using Gunicorn, Systemd, and Nginx.
* See Flask's [Deployment Options](https://flask.palletsprojects.com/en/1.1.x/deploying/) and [this Digital Ocean Blog](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04) for more information.