from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
 
app = Flask(__name__)
 
BASE_URL = "https://ecampus.cc-student.com"
 
def do_logout(username, password):
    session = requests.Session()
 
    # Wochentag prüfen (Montag=0 … Sonntag=6), Zeitzone Deutschland
    tz = pytz.timezone("Europe/Berlin")
    heute = datetime.now(tz).weekday()
    if heute >= 5:  # 5 = Samstag, 6 = Sonntag
        return {"success": False, "skipped": True, "message": "Wochenende – kein Logout nötig."}
 
    # Schritt 1: Login-Seite aufrufen und prüfen ob schon ausgeloggt
    login_page = session.get(f"{BASE_URL}/login/index.php")
 
    # Wenn wir direkt auf der Login-Seite landen → schon ausgeloggt
    if "logintoken" in login_page.text and "/my/" not in login_page.url:
        return {"success": False, "skipped": True, "message": "Bereits ausgeloggt – nichts zu tun."}
 
    soup = BeautifulSoup(login_page.text, "html.parser")
    token_input = soup.find("input", {"name": "logintoken"})
    logintoken = token_input["value"] if token_input else ""
 
    # Schritt 2: Einloggen
    login_data = {
        "username": username,
        "password": password,
        "logintoken": logintoken,
    }
    response = session.post(f"{BASE_URL}/login/index.php", data=login_data)
 
    if "loginerrormessage" in response.text or "/login" in response.url:
        return {"success": False, "skipped": False, "message": "Login fehlgeschlagen – Zugangsdaten prüfen!"}
 
    # Schritt 3: sesskey aus der Seite lesen
    soup = BeautifulSoup(response.text, "html.parser")
    logout_link = soup.find("a", href=lambda h: h and "logout" in h and "sesskey" in h)
 
    if not logout_link:
        # Fallback: sesskey direkt aus dem HTML suchen
        import re
        match = re.search(r'"sesskey":"([^"]+)"', response.text)
        if match:
            sesskey = match.group(1)
            logout_url = f"{BASE_URL}/login/logout.php?sesskey={sesskey}"
        else:
            return {"success": False, "skipped": False, "message": "sesskey nicht gefunden"}
    else:
        logout_url = logout_link["href"]
 
    # Schritt 4: Ausloggen
    session.get(logout_url)
    return {"success": True, "skipped": False, "message": "Erfolgreich ausgeloggt!"}
 
 
@app.route("/logout", methods=["POST"])
def logout():
    data = request.form if request.form else request.get_json(silent=True) or {}
    if not data or "username" not in data or "password" not in data:
        return jsonify({"success": False, "skipped": False, "message": "Benutzername oder Passwort fehlt"}), 400
 
    result = do_logout(data["username"], data["password"])
    return jsonify(result)
 
 
@app.route("/", methods=["GET"])
def index():
    return "eCampus Logout API läuft ✅"
 
 
if __name__ == "__main__":
    app.run()
