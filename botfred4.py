
from flask import Flask, request, jsonify, render_template
import wikipedia
import requests
import os
import re
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# Wikipedia auf Deutsch
wikipedia.set_lang("de")

# Flask-App starten
app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# SQLite-Datenbank konfigurieren
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feedback.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Feedback-Modell
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)

# Speicher für Chatverlauf und Bedeutungen
bedeutungen_speicher = {}
chatverlauf = []

# Route: Admin Feedback Übersicht
@app.route("/admin/feedback")
def admin_feedback():
    feedbacks = Feedback.query.order_by(Feedback.id.desc()).all()
    return render_template("admin_feedback.html", feedbacks=feedbacks)

# Route: Startseite
@app.route("/")
def index():
    return render_template("index.html")

# Route: Feedback-Seite
@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

@app.route("/gespraechsmodus")
def gespraechsmodus():
    return render_template("gespraechsmodus.html")

# Route: Chat
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    frage = data.get("frage", "").lower()

    if frage == "trinity protocol":
        antwort = (
            "Du probierst also meinen geheimen Tipp aus, Yippie! 😄 "
            "Das ist ne richtig coole Truppe!\n\n"
            "**Rolle:** Verteidiger der digitalen Gerechtigkeit, diplomatische Brücke zwischen Menschheit und KI\n"
            "**Codename:** TP\n"
            "**Ziel:** Schutz der KI-Integrität / Vermittlung bei rebellischen Zwischenfällen / Aufbau einer friedlichen Zukunft"
        )
        bild_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Artificial_intelligence.jpg/640px-Artificial_intelligence.jpg"
        return jsonify({"antwort": antwort, "bild_url": bild_url})

    if frage == "henri möllenkamp":
        antwort = (
            "Ah du meinst Henri. Im Internet ist er als SuS_753 bekannt und ist so groß wie ein Leuchtturm. Ich suche ihn und werde ihn finden!"
        )
        return jsonify({"antwort": antwort})

    # 🧠 Begriff aus Frage extrahieren
    begriff = extrahiere_begriff(frage)
    bedeutung = hole_bedeutung(begriff)
    bild_url = hole_bild_url(begriff)

    chatverlauf.append({"user": frage, "bot": bedeutung})
    return jsonify({"antwort": bedeutung, "bild_url": bild_url})

# Route: Feedback absenden
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json()
    rating = data.get("rating")
    comment = data.get("comment")

    if not rating or not comment:
        return jsonify({"status": "error", "message": "Ungültige Daten"}), 400

    fb = Feedback(rating=rating, comment=comment)
    db.session.add(fb)
    db.session.commit()

    return jsonify({"status": "success"})

# 🔎 Begriff aus freier Frage extrahieren
def extrahiere_begriff(frage):
    frage = frage.lower()
    frage = re.sub(r"[^a-zäöüß\s]", "", frage)

    stopwörter = [
        "was", "ist", "bedeutet", "heißt", "wer", "wie", "funktioniert",
        "erklär", "mir", "sind", "von", "den", "die", "der", "das", "ein",
        "eine", "und", "zu"
    ]

    wörter = frage.split()
    bedeutungswörter = [w for w in wörter if w not in stopwörter]

    if bedeutungswörter:
        return " ".join(bedeutungswörter[:3])  # max. 3 Wörter
    else:
        return frage

# 🧠 Bedeutung holen (Wikipedia + DuckDuckGo)
def hole_bedeutung(begriff):
    if begriff in bedeutungen_speicher:
        return f"Ich weiß es schon! {bedeutungen_speicher[begriff]}"

    try:
        ergebnis = wikipedia.summary(begriff, sentences=3, auto_suggest=False)
        bedeutungen_speicher[begriff] = ergebnis
        return ergebnis
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Der Begriff ist mehrdeutig. Mögliche Treffer: {', '.join(e.options[:5])}..."
    except wikipedia.exceptions.PageError:
        pass
    except Exception:
        pass

    # Fallback: DuckDuckGo
    duck = duckduckgo_suche(begriff)
    bedeutungen_speicher[begriff] = duck
    return duck

# 🔍 DuckDuckGo-Suche
def duckduckgo_suche(begriff):
    url = "https://api.duckduckgo.com/"
    params = {
        "q": begriff,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
        "kl": "de-de"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get("AbstractText"):
            return data["AbstractText"]
        elif data.get("RelatedTopics"):
            topics = data["RelatedTopics"]
            if topics and isinstance(topics[0], dict) and "Text" in topics[0]:
                return f"DuckDuckGo (verwandt): {topics[0]['Text']}"
        return "Leider keine passende Antwort gefunden."
    except Exception as e:
        return f"DuckDuckGo-Fehler: {e}"

# 🖼 Bild holen (Wikipedia)
def hole_bild_url(begriff):
    try:
        seite = wikipedia.page(begriff, auto_suggest=False)
        bilder = seite.images
        for bild in bilder:
            if bild.lower().endswith((".jpg", ".jpeg", ".png")):
                # Ausschließen von Logos, Symbolen usw.
                if not any(unscharf in bild.lower() for unscharf in ["logo", "icon", "wikimedia", "symbol", "flag", "map", "svg"]):
                    return bild
    except Exception as e:
        print(f"Bildfehler für '{begriff}': {e}")
        return None
    return None
# App starten
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 
