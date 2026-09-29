from flask import Flask, render_template, jsonify
from resume_data import RESUME

app = Flask(__name__)


@app.route("/")
def index():
    # Every skill used anywhere, so the sidebar can render filter chips.
    skills = sorted({s for item in RESUME["experience"] + RESUME["projects"] for s in item["skills"]})
    return render_template("index.html", r=RESUME, skills=skills)


@app.route("/api/resume")
def api_resume():
    return jsonify(RESUME)


if __name__ == "__main__":
    app.run(debug=True)
