from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
 
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
 
    # Schritt 3: Hauptseite abrufen und prüfen ob Zeiterfassung läuft
    main_page = session.get(f"{BASE_URL}/my/")
    soup = BeautifulSoup(main_page.text, "html.parser")
 
    # Stopp-Button suchen (fa-stop Icon = Zeiterfassung läuft)
    stop_button = soup.find("a", class_="register-time-btn-nav")
 
    if not stop_button:
        return {"success": False, "skipped": True, "message": "Zeiterfassung läuft nicht – nichts zu tun."}
 
    # Prüfen ob es der Stopp-Button ist (fa-stop) oder der Start-Button (fa-play)
    icon = stop_button.find("i", class_="fa-stop")
    if not icon:
        return {"success": False, "skipped": True, "message": "Zeiterfassung läuft nicht – nichts zu tun."}
 
    # Schritt 4: Zeiterfassung stoppen
    stop_url = BASE_URL + stop_button["href"]
    session.get(stop_url)
 
    return {"success": True, "skipped": False, "message": "Zeiterfassung erfolgreich gestoppt!"}
 
 
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
