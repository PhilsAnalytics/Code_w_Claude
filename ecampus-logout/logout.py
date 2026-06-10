from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
 
app = Flask(__name__)
 
BASE_URL = "https://ecampus.cc-student.com"
 
def zeiterfassung_stoppen(username, password):
    session = requests.Session()
 
    # Wochentag prüfen (Montag=0 … Sonntag=6), Zeitzone Deutschland
    tz = pytz.timezone("Europe/Berlin")
    heute = datetime.now(tz).weekday()
    if heute >= 5:  # 5 = Samstag, 6 = Sonntag
        return {"success": False, "skipped": True, "message": "Wochenende – Zeiterfassung wird nicht gestoppt."}
 
    # Schritt 1: Login-Seite aufrufen
    login_page = session.get(f"{BASE_URL}/login/index.php")
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
 
    # Schritt 3: Hauptseite abrufen
    main_page = session.get(f"{BASE_URL}/my/")
    html = main_page.text
 
    # Schritt 4: access_token aus dem HTML auslesen
    token_match = re.search(r'"access_token":"([a-f0-9]+)"', html)
    if not token_match:
        return {"success": False, "skipped": False, "message": "access_token nicht gefunden"}
    access_token = token_match.group(1)
 
    # Schritt 5: sesskey aus dem HTML auslesen
    sesskey_match = re.search(r'"sesskey":"([^"]+)"', html)
    if not sesskey_match:
        return {"success": False, "skipped": False, "message": "sesskey nicht gefunden"}
    sesskey = sesskey_match.group(1)
 
    # Schritt 6: Prüfen ob Zeiterfassung läuft (fa-stop vorhanden?)
    if "fa-stop" not in html:
        return {"success": False, "skipped": True, "message": "Zeiterfassung läuft nicht – nichts zu tun."}
 
    # Schritt 7: Zeiterfassung stoppen
    stopp_url = (
        f"{BASE_URL}/theme/cclms/internallib.php"
        f"?type=register_user_login"
        f"&extra_data_access_token={access_token}"
        f"&last_login_status=1"
        f"&sesskey={sesskey}"
    )
    result = session.get(stopp_url)
 
    if result.status_code == 200:
        return {"success": True, "skipped": False, "message": "Zeiterfassung erfolgreich gestoppt!"}
    else:
        return {"success": False, "skipped": False, "message": f"Fehler beim Stoppen: HTTP {result.status_code}"}
 
 
@app.route("/stopp", methods=["POST"])
def stopp():
    data = request.form if request.form else request.get_json(silent=True) or {}
    if not data or "username" not in data or "password" not in data:
        return jsonify({"success": False, "skipped": False, "message": "Benutzername oder Passwort fehlt"}), 400
 
    result = zeiterfassung_stoppen(data["username"], data["password"])
    return jsonify(result)
 
 
@app.route("/", methods=["GET"])
def index():
    return "eCampus Zeiterfassung API läuft ✅"
 
 
if __name__ == "__main__":
    app.run()
