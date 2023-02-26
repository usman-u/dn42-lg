from flask import Flask, redirect, url_for, render_template, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, RadioField
from wtforms.validators import DataRequired, Email, InputRequired
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime
from net_automation import net_automation
import os
import sys
import concurrent.futures
import dn42_whois
from inventory import routers
from validations import is_valid_address

app = Flask(__name__)  # create an instance of the Flask class
app.config["SECRET_KEY"] = os.getenv("flask_secret_key")  # secret key
Bootstrap(app)


class LookingGlassForm(FlaskForm):
    device = SelectField(
        "Router", choices=["fr-lil1.usman.dn42", "us-ca1.usman.dn42"]
    )

    device = RadioField('Router', choices=[('fr_lil1', 'fr-lil1.usman.dn42'), ('us_ca1', 'us-ca1.usman.dn42')])

    operation = SelectField("Operation", choices=["BGP Peer Summary"])
    target = StringField("Target", render_kw={"placeholder": "1.1.1.1"})
    submit = SubmitField("Submit")


# ROUTES
@app.route("/")  # route for the home page
def home():
    return render_template("index.html")


@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
    form = LookingGlassForm()

    if request.method == 'POST':
        device = form.device.data
        operation = form.operation.data
        target = form.target.data

        if operation == 'BGP Peer Summary':
            device = form.device.data
            operation = form.operation.data
            target = form.target.data

            if operation == 'BGP Peer Summary':
                result = (operation, target)
                result_url = url_for("get_bgp_peers", router=device)

                return redirect(result_url)

            else:
                result_url = None

    else:
        result_url = None
        
    return render_template('looking_glass.html', form=form)


@app.route("/looking_glass/get_all_routes/", methods=["GET", "POST"])
def get_routes():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again.")

    inet = rtr_instance.get_all_routes("inet")
    inet6 = rtr_instance.get_all_routes("inet6")

    return render_template("get_all_routes.html", inet=inet, inet6=inet6, router=router)


@app.route("/looking_glass/route_summary/", methods=["GET", "POST"])
def get_route_summary():
    router = request.args.getlist("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again.")

    inet = rtr_instance.get_route_summary("inet")
    inet6 = rtr_instance.get_route_summary("inet6")

    return render_template(
        "get_route_summary.html", inet=inet, inet6=inet6, router=router
    )


@app.route("/looking_glass/summary/bgp/", methods=["GET", "POST"])
def get_summary_bgp():
    routers = request.args.getlist("routers")

    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_router = {
            executor.submit(routers[router].get_bgp_peers()): router
            for router in routers
        }
        for future in concurrent.futures.as_completed(future_to_router):
            try:
                router = routers[router]
            except KeyError:
                return render_template("error.html", input=router, error="Invalid router name. Please try again.")
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"{router} generated an exception: {exc}")

    return render_template("summary_bgp.html", results=results, routers=routers)


@app.route("/looking_glass/get_bgp_peer/", methods=["GET", "POST"])
def get_bgp_peer():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template("error.html", input=peer ,error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.")

    try:
        result = routers[router].get_bgp_peer(peer)
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again. If you're trying to inject something, please stop.")

    return render_template(
        "get_bgp_peer.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/bgp_peers/", methods=["GET", "POST"])
def get_bgp_peers():
    router = request.args.get("router")

    try:
        result = routers[router].get_bgp_peers()
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again. If you're trying to inject something, please stop.")

    return render_template(
        "get_bgp_peers.html", result=result, router=router, time=datetime.now()
    )


@app.route("/looking_glass/get_bgp_peer_routes/", methods=["GET", "POST"])
def get_bgp_peer_received_routes():
    router = request.args.get("router")
    desc = request.args.get("desc")
    peer = request.args.get("peer")

    # injection attack check
    if not is_valid_address(peer):
        return render_template("error.html", input=peer ,error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again.")

    if not rtr_instance.check_ssh():  # check if SSH session is active
        rtr_instance.init_ssh()  # if not, create a new SSH session

    result = rtr_instance.get_bgp_peer_received_routes(peer)

    return render_template(
        "get_bgp_peer_received_routes.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/get_bgp_peer_advertised_routes/", methods=["GET", "POST"])
def get_bgp_peer_advertised_routes():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template("error.html", input=peer ,error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again.")

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_bgp_peer_advertised_routes(peer)

    return render_template(
        "get_bgp_peer_advertised_routes.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/whois/", methods=["GET", "POST"])
def whois():
    target = request.args.get("target")

    result = dn42_whois.dn42_whois(target)

    return render_template("whois.html", target=target, result=result)


@app.route("/looking_glass/get_interfaces/", methods=["GET", "POST"])
def get_interfaces():
    router = request.args.get("router")
    
    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template("error.html", input=router, error="Invalid router name. Please try again.")

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_interfaces()

    return render_template("get_interfaces.html", result=result, router=router)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, threaded=False, host="0.0.0.0")
