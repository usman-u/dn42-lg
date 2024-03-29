from flask import Flask, redirect, url_for, render_template, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, RadioField
from wtforms.validators import DataRequired, Email, InputRequired
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime
from net_automation import Vyos
import os
import sys
import concurrent.futures
import dn42_whois
from inventory import routers
from validations import is_valid_address, is_valid_network

app = Flask(__name__)  # create an instance of the Flask class
app.config["SECRET_KEY"] = os.getenv("flask_secret_key")  # secret key
Bootstrap(app)


class LookingGlassForm(FlaskForm):
    device = SelectField("Router", choices=["fr-lil1.usman.dn42", "us-ca1.usman.dn42"])

    device = RadioField(
        "Router",
        choices=[("fr_lil1", "fr-lil1.usman.dn42"), ("us_ca1", "us-ca1.usman.dn42")],
        validators=[InputRequired()],
    )

    query = RadioField(
        "Query",
        choices=[
            ("show ip route", "show ip route <e.g. 172.20.0.53>"),
            ("show ip bgp summary", "show ip bgp summary"),
            ("show ip bgp route", "show ip bgp route <e.g. 172.20.0.53 > "),
            ("show ip bgp peer", "show ip bgp peer <e.g. fe80::ade0>"),
            ("show ip bgp advertised-routes", "show ip bgp peer advertised-routes <e.g. fe80::ade0>"),
            ("show ip bgp received-routes", "show ip bgp peer received routes <e.g. fe80::ade0>"),
            ("show ip ospf routes", "show ip ospf routes"),
            ("show ip ospf neighbors", "show ip ospf neighbors"),
            ("show interfaces", "show interfaces"),
            ("whois", "whois ..."),
        ],
        validators=[InputRequired()],
    )

    # operation = SelectField("Operation", choices=["BGP Peer Summary"])
    target = StringField("Target", render_kw={"placeholder": "e.g. fe80::abc0"})
    submit = SubmitField("Submit")


# ROUTES
@app.route("/")  # route for the home page
def index():
    return render_template("index.html")
    # return redirect(url_for("looking_glass"))


@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
    form = LookingGlassForm()
    result = None

    if request.method == "POST":
        device = form.device.data
        query = form.query.data
        target = form.target.data

        if query == "show ip route":
            result_url = url_for("get_route", router=device, prefix=target)
            return redirect(result_url)

        if query == "show ip bgp summary":
            result_url = url_for("get_bgp_peers", router=device)
            return redirect(result_url)

        if query == "show ip bgp route":
            result_url = url_for("get_bgp_route", prefix=target, router=device)
            return redirect(result_url)

        if query == "show ip bgp peer":
            result_url = url_for("get_bgp_peer", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip bgp received-routes":
            result_url = url_for("get_bgp_peer_received_routes", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip bgp advertised-routes":
            result_url = url_for("get_bgp_peer_advertised_routes", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip ospf routes":
            result_url = url_for("get_ospf_routes", router=device)
            return redirect(result_url)

        if query == "show ip ospf neighbors":
            result_url = url_for("get_ospf_neighbors", router=device)
            return redirect(result_url)

        if query == "show interfaces":
            result_url = url_for("get_interfaces", router=device)
            return redirect(result_url)
        if query == "whois":
            result_url = url_for("whois", target=target)
            return redirect(result_url)

    return render_template("looking_glass.html", form=form, result=result)


@app.route("/looking_glass/get_ospf_routes/", methods=["GET", "POST"])
def get_ospf_routes():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()       # if not, create a new SSH session
        result = rtr_instance.get_ospf_route_all()
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    return render_template("get_ospf_routes.html", router=router, result=result)


@app.route("/looking_glass/get_ospf_neighbors/", methods=["GET", "POST"])
def get_ospf_neighbors():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()       # if not, create a new SSH session
        result = rtr_instance.get_ospf_neighbors()
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    return render_template("get_ospf_neighbors.html", router=router, result=result)

@app.route("/looking_glass/get_all_routes/", methods=["GET", "POST"])
def get_routes():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    inet = rtr_instance.get_all_routes("inet")
    inet6 = rtr_instance.get_all_routes("inet6")

    return render_template("get_all_routes.html", inet=inet, inet6=inet6, router=router)


@app.route("/looking_glass/route_summary/", methods=["GET", "POST"])
def get_route_summary():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    inet = rtr_instance.get_route_summary("inet")
    inet6 = rtr_instance.get_route_summary("inet6")

    return render_template(
        "get_route_summary.html", inet=inet, inet6=inet6, router=router
    )


@app.route("/looking_glass/summary/bgp/", methods=["GET", "POST"])
def get_summary_bgp():
    url_routers = request.args.getlist("router")

    results = [None] * len(url_routers)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_router = {(router, i): executor.submit(routers[router].get_bgp_peers) for i, router in enumerate(url_routers)}
        for future in concurrent.futures.as_completed(future_to_router.values()):
            for router, i in future_to_router.keys():
                if future_to_router[(router, i)] == future:
                    break
            try:
                result = future.result()
                results[i] = result
            except KeyError:
                return render_template(
                    "error.html", input=router, error="Invalid router name. Please try again."
                )

    return render_template("summary_bgp.html", results=results, routers=url_routers)

@app.route("/looking_glass/get_route/", methods=["GET", "POST"])
def get_route():
    router = request.args.get("router")
    prefix = request.args.get("prefix")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_network(prefix):
        return render_template(
            "error.html",
            input=prefix,
            error=f"Invalid IP address/prefix: {prefix}",
        )

    try:
        result = routers[router].get_route(prefix, "inet")

    except KeyError:              # accounts for when the router name is wrong
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )
    except TypeError:             # accounts for when the peer IP doesn't exist
        return render_template(
            "error.html",
            input=prefix,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IPs on this router.",
        )

    return render_template(
        "get_route.html", router=router, result=result, prefix=prefix
    )



@app.route("/looking_glass/get_bgp_peer/", methods=["GET", "POST"])
def get_bgp_peer():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IP addresses.",
        )

    try:
        result = routers[router].get_bgp_peer(peer)

    except KeyError:              # accounts for when the router name is wrong
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )
    except TypeError:             # accounts for when the peer IP doesn't exist
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IPs on this router.",
        )

    return render_template(
        "get_bgp_peer.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/get_bgp_route/", methods=["GET", "POST"])
def get_bgp_route():
    router = request.args.get("router")
    prefix = request.args.get("prefix")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_network(prefix):
        return render_template(
            "error.html",
            input=prefix,
            error="Invalid BGP Preifx/IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()  # if not, create a new SSH session
        result = rtr_instance.get_bgp_route(prefix)

    except KeyError:
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )

    return render_template(
        "get_bgp_route.html", router=router, result=result, prefix=prefix, desc=desc
    )

@app.route("/looking_glass/bgp_peers/", methods=["GET", "POST"])
def get_bgp_peers():
    router = request.args.get("router")

    try:
        result = routers[router].get_bgp_peers()
    except KeyError:
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )

    return render_template(
        "get_bgp_peers.html", result=result, router=router, time=datetime.now()
    )


@app.route("/looking_glass/get_bgp_peer_received_routes/", methods=["GET", "POST"])
def get_bgp_peer_received_routes():
    router = request.args.get("router")
    desc = request.args.get("desc")
    peer = request.args.get("peer")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():  # check if SSH session is active
        rtr_instance.init_ssh()  # if not, create a new SSH session

    result = rtr_instance.get_bgp_peer_received_routes(peer)

    return render_template(
        "get_bgp_peer_received_routes.html",
        router=router,
        result=result,
        peer=peer,
        desc=desc,
    )


@app.route("/looking_glass/get_bgp_peer_advertised_routes/", methods=["GET", "POST"])
def get_bgp_peer_advertised_routes():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_bgp_peer_advertised_routes(peer)

    return render_template(
        "get_bgp_peer_advertised_routes.html",
        router=router,
        result=result,
        peer=peer,
        desc=desc,
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
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_interfaces()

    return render_template("get_interfaces.html", result=result, router=router)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, threaded=False, host="0.0.0.0")
