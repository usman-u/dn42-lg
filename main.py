from flask import Flask, redirect, url_for, render_template, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField
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

app = Flask(__name__)  # create an instance of the Flask class
app.config["SECRET_KEY"] = os.getenv("flask_secret_key")  # secret key
Bootstrap(app)


class LookingGlassForm(FlaskForm):
    # device = QuerySelectField(query_factory=Devices.query.all())
    # all_devices = Devices.query.all()
    # device = SelectField(u"Device Name", choices=[all_devices, "test", "test2"])
    # print (all_devices)

    device = SelectField(
        "Device Name", choices=["fr-lil1.usman.dn42", "uk-lon3.usman.dn42"]
    )

    operation = SelectField("Operation", choices=["BGP Peer Summary"])
    target = StringField("Target", render_kw={"placeholder": "1.1.1.1"})
    submit = SubmitField("Submit")


# ROUTES
@app.route("/")  # route for the home page
def home():
    return render_template("index.html")


@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
    device = ""
    operation = ""
    target = ""
    form = LookingGlassForm()

    if form.validate_on_submit():
        # device = form.device.data
        device = form.device.data
        operation = form.operation.data
        target = form.target.data

        # form.device.data = ""
        # form.operation.data = ""
        # form.target.data = ""

        flash("Form submitted successfully!")
        print(form.operation.data)
        # if form.operation.data == "Show IP Route To":

        return redirect(url_for("", router=form.device.data, target=form.target.data))

    return render_template(
        "looking_glass.html",
        form=form,
        device=device,
        operation=operation,
        target=target,
    )


@app.route("/looking_glass/routesv4/", methods=["GET", "POST"])
def get_routes_v4():
    router = request.args.getlist("router")
    router += "_api"

    rtr_instance = getattr(sys.modules[__name__], router)
    result = rtr_instance.get_all_routes("inet")

    return render_template("get_routes.html", result=result, router=router)


@app.route("/looking_glass/route_summary/", methods=["GET", "POST"])
def get_route_summary():
    router = request.args.getlist("router")

    rtr_instance = routers[router]

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
            router = future_to_router[future]
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

    result = routers[router].get_bgp_peer(peer)

    return render_template(
        "get_bgp_peer.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/bgp_peers/", methods=["GET", "POST"])
def get_bgp_peers():
    router = request.args.get("router")

    result = routers[router].get_bgp_peers()
    return render_template(
        "get_bgp_peers.html", result=result, router=router, time=datetime.now()
    )


@app.route("/looking_glass/get_bgp_peer_routes/", methods=["GET", "POST"])
def get_bgp_peer_received_routes():
    router = request.args.get("router")
    peer = request.args.get("peer")

    rtr_instance = routers[router]

    if not rtr_instance.check_ssh():  # check if SSH session is active
        rtr_instance.init_ssh()  # if not, create a new SSH session

    result = rtr_instance.get_bgp_peer_received_routes(peer)

    return render_template(
        "get_bgp_peer_received_routes.html", router=router, result=result, peer=peer
    )


@app.route("/looking_glass/get_bgp_peer_advertised_routes/", methods=["GET", "POST"])
def get_bgp_peer_advertised_routes(router):
    router = request.args.getlist("router")
    peer = request.args.get("peer")

    rtr_instance = routers[router]

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_bgp_peer_advertised_routes(peer)

    return render_template(
        "get_bgp_peer_advertised_routes.html", router=router, result=result, peer=peer
    )


@app.route("/looking_glass/whois/", methods=["GET", "POST"])
def whois():
    target = request.args.get("target")

    result = dn42_whois.dn42_whois(target)

    return render_template("whois.html", target=target, result=result)


@app.route("/looking_glass/get_interfaces/", methods=["GET", "POST"])
def get_interfaces():
    router = request.args.get("router")
    
    rtr_instance = routers[router]

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_interfaces()

    return render_template("get_interfaces.html", result=result, router=router)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, threaded=False)
