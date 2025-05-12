from flask import Flask, request, jsonify, render_template
import wikipedia
import requests
import os
from flask_sqlalchemy import SQLAlchemy

# Wikipedia auf Deutsch
wikipedia.set_lang("de")

# Flask-App starten
app = Flask(__name__)

# SQLAlchemy für die Datenbank
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feedback.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Feedback-Datenbankmodell
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)

# Speicher für Bedeutungen & Chatverlauf
bedeutungen_speicher = {}
chatverlauf = []

# Route für das Admin-Feedback
@app.route("/admin/feedback")
def admin_feedback():
    feedbacks = Feedback.query.order_by(Feedback.id.desc()).all()
    return render_template("admin_feedback.html", feedbacks=feedbacks)

# Startseite
@app.route("/")
def index():
    return render_template("index.html")  # deine HTML-Datei

# Route für Feedback-Seite
@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

# Route für den Chat
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    frage = data.get("frage", "").lower()

    if frage == "exit":
        return jsonify({"antwort": "Hauste rein!"})

    if frage == "trinity protocol":
        antwort = (
            "Du probierst also meinen geheimen Tipp aus, Yippie! 😄 "
            "Das ist ne richtig coole Truppe!\n\n"
            "**Rolle:** Verteidiger der digitalen Gerechtigkeit, diplomatische Brücke zwischen Menschheit und KI\n"
            "**Codename:** TP\n"
            "**Ziel:** Schutz der KI-Integrität / Vermittlung bei rebellischen Zwischenfällen / Aufbau einer friedlichen Zukunft"
        )

        if frage == "henri möllenkamp":
            antwort = (
                "Ah du meinst Henri Möllenkamp. Im Internet ist er als SuS_753 bekannt und ist so groß wie ein Leuchtturm. Ich suche ihn und werde ihn finden!"
            )

        bild_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Artificial_intelligence.jpg/640px-Artificial_intelligence.jpg"
        return jsonify({"antwort": antwort, "bild_url": bild_url})

    # Bedeutungsabfragen erkennen
    if any(x in frage for x in ["was heißt", "was bedeutet", "wer ist", "was ist"]):
        if "was heißt" in frage:
            begriff = frage.replace("was heißt", "").strip()
        elif "was bedeutet" in frage:
            begriff = frage.replace("was bedeutet", "").strip()
        elif "wer ist" in frage:
            begriff = frage.replace("wer ist", "").strip()
        elif "was ist" in frage:
            begriff = frage.replace("was ist", "").strip()
        else:
            begriff = frage.strip()

        bedeutung = hole_bedeutung(begriff)
        bild_url = hole_bild_url(begriff)

        chatverlauf.append({"user": frage, "bot": bedeutung})
        return jsonify({"antwort": bedeutung, "bild_url": bild_url})

    return jsonify({"antwort": "Ich habe das nicht verstanden. Frag mit 'Was heißt XYZ?'"})


# Route für das Absenden von Feedback
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

# DuckDuckGo-Suche als Fallback
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
            return data['AbstractText']
        elif data.get("RelatedTopics"):
            topics = data["RelatedTopics"]
            if topics and "Text" in topics[0]:
                return f"DuckDuckGo (verwandt): {topics[0]['Text']}"
        return "Leider keine passende Antwort gefunden."
    except Exception as e:
        return f"DuckDuckGo-Fehler: {e}"

# Bedeutung ermitteln
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

    # Fallback auf DuckDuckGo
    duck = duckduckgo_suche(begriff)
    bedeutungen_speicher[begriff] = duck
    return duck

# Bild über Wikipedia holen
def hole_bild_url(begriff):
    try:
        seite = wikipedia.page(begriff, auto_suggest=False)
        bilder = seite.images
        for bild in bilder:
            if bild.lower().endswith((".jpg", ".jpeg", ".png")):
                if not any(x in bild.lower() for x in ["logo", "icon", "wikimedia", "flag", "symbol", "svg"]):
                    return bild
    except Exception as e:
        print(f"Fehler beim Bildholen für '{begriff}': {e}")
        return None

    return None

# Lokaler Start
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
