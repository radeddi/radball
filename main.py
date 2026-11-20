# app.py  – Radball-API + Crawler-Scheduler + Admin-Interface
# ------------------------------------------------------------
from flask import (
    Flask, jsonify, make_response, send_from_directory,
    render_template, request, redirect, url_for, flash
)
from markupsafe import escape
from gevent.pywsgi import WSGIServer
from threading import Thread
from datetime import datetime
import json, time, os

# -----------------------------------------------------------------
# 1)  Crawler-Import  (in crawler/radball_crawler.py)
# -----------------------------------------------------------------
try:
    from crawler import radball_crawler
except ImportError:
    radball_crawler = None  # Scheduler will be disabled

# -----------------------------------------------------------------
app         = Flask(__name__)
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT   = os.path.join(BASE_DIR, "data", "leagues")
LEAGUE_JSON = os.path.join(DATA_ROOT, "leagues.json")
PDF_ROOT    = os.path.join(BASE_DIR, "data", "pdfs")

# static route for PDFs
app.static_folder = None
app.add_url_rule(
    '/pdfs/<path:filename>',
    endpoint='pdfs',
    view_func=lambda filename: send_from_directory(PDF_ROOT, filename)
)

# =================================================================
# 2)  BACKGROUND SCHEDULER
# =================================================================
def run_scheduler():
    if radball_crawler is None:
        print("[WARN] crawler/radball_crawler.py not found – scheduler disabled")
        return
    while True:
        try:
            print(f"[{datetime.now():%F %T}]  Crawl start")
            radball_crawler.run()           # fetch PDFs & build JSON
            build_league_index()            # rebuild leagues.json
            print(f"[{datetime.now():%F %T}]  Crawl done")
        except Exception as e:
            print("[Scheduler] Error:", e)
        time.sleep(6 * 60 * 60)            # every 6h

# =================================================================
# 3)  HELPERS
# =================================================================
def safe_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        print("[safe_json] Error:", e)
        return None

def build_league_index():
    os.makedirs(DATA_ROOT, exist_ok=True)
    leagues = []
    for league_dir in sorted(os.listdir(DATA_ROOT)):
        md_file = os.path.join(DATA_ROOT, league_dir, "matchdays", "matchdays.json")
        mds = safe_json(md_file) or []
        if not mds:
            continue
        first = mds[0]
        start_val = first.get("start")
        if isinstance(start_val, str) and len(start_val) >= 4:
            season = start_val[:4]
        else:
            season = str(datetime.now().year)
        leagues.append({
            "shortName":  league_dir,
            "longName":   first.get("leagueLongName", league_dir),
            "hasNonCompetitive": False,
            "season":     season,
            "manager":    {"name":"","email":"","street":"","zip":"","city":"","phone":""},
            "rules":      ["*"],
            "lastImport": first.get("lastImport", datetime.now().isoformat())
        })
    with open(LEAGUE_JSON, "w", encoding="utf-8") as fh:
        json.dump(leagues, fh, indent=2, ensure_ascii=False)

# =================================================================
# 4)  API ROUTES
# =================================================================
@app.route("/api/leagues", methods=["GET"])
def api_leagues():
    return jsonify(safe_json(LEAGUE_JSON) or []), 200

@app.route("/api/leagues/<league>", methods=["GET"])
def api_league(league):
    league = escape(league)
    for lg in safe_json(LEAGUE_JSON) or []:
        if lg["shortName"] == league:
            return jsonify(lg)
    return make_response("not found", 404)

@app.route("/api/leagues/<league>/teams", methods=["GET"])
def api_teams(league):
    league = escape(league)
    data = safe_json(os.path.join(DATA_ROOT, league, "teams", "teams.json"))
    if data is None:
        return make_response("not found", 404)
    return jsonify(data)

@app.route("/api/leagues/<league>/matchdays", methods=["GET"])
def api_matchdays(league):
    league = escape(league)
    data = safe_json(os.path.join(DATA_ROOT, league, "matchdays", "matchdays.json"))
    if data is None:
        return make_response("not found", 404)
    # strip out the heavy teams/games arrays
    lite = [{k:v for k,v in md.items() if k not in ("teams","games")} for md in data]
    return jsonify(lite)

@app.route("/api/leagues/<league>/matchdays/<int:number>", methods=["GET"])
def api_matchday(league, number):
    league = escape(league)
    mds = safe_json(os.path.join(DATA_ROOT, league, "matchdays", "matchdays.json")) or []
    if not (1 <= number <= len(mds)):
        return make_response("not found", 404)
    return jsonify(mds[number-1])

# =================================================================
# 5)  ADMIN INTERFACE
# =================================================================
@app.route("/admin")
def admin_index():
    leagues = safe_json(LEAGUE_JSON) or []
    overview = []
    for lg in leagues:
        short = lg["shortName"]
        mds = safe_json(os.path.join(DATA_ROOT, short, "matchdays", "matchdays.json")) or []
        overview.append({
            "shortName":  short,
            "longName":   lg["longName"],
            "count":      len(mds),
            "lastImport": lg["lastImport"]
        })
    return render_template("admin.html", leagues=overview)

@app.route("/admin/<league>")
def admin_league(league):
    league = escape(league)
    mds = safe_json(os.path.join(DATA_ROOT, league, "matchdays", "matchdays.json")) or []
    data = []
    for md in mds:
        data.append({
            "number":    md.get("number"),
            "start":     md.get("start")    or "<fehlend>",
            "hostClub":  md.get("hostClub") or "<fehlend>",
            "games":     len(md.get("games", [])),
            "hasTime":   bool(md.get("start")),
            "hasHost":   bool(md.get("hostClub")),
            "hasGames":  len(md.get("games", [])) > 0
        })
    return render_template("admin.html",
                           league=league,
                           matchdays=data)

@app.route("/admin/<league>/<int:num>", methods=["GET","POST"])
def edit_matchday(league, num):
    league = escape(league)
    md_file = os.path.join(DATA_ROOT, league, "matchdays", "matchdays.json")
    mds = safe_json(md_file) or []
    if not (1 <= num <= len(mds)):
        return make_response("nicht gefunden", 404)
    md = mds[num-1]

    if request.method == "POST":
        md["start"]    = request.form.get("start")    or md["start"]
        md["hostClub"] = request.form.get("hostClub") or md["hostClub"]
        with open(md_file, "w", encoding="utf-8") as fh:
            json.dump(mds, fh, indent=2, ensure_ascii=False)
        flash("Änderungen gespeichert", "success")
        return redirect(url_for("admin_league", league=league))

    # --- find the *exact* snippet JSON, swap to .pdf ---
    snippet_dir = os.path.join(DATA_ROOT, league)
    candidate_pdf = None
    if os.path.isdir(snippet_dir):
        for fn in os.listdir(snippet_dir):
            # skip the consolidated files
            if fn.lower().endswith(".json") and fn != "matchdays.json":
                # match this matchday by number in the filename
                if f"_{num}." in fn:
                    pdfn = fn[:-5] + ".pdf"
                    if os.path.exists(os.path.join(PDF_ROOT, league, pdfn)):
                        candidate_pdf = pdfn
                        break

    return render_template("edit_matchday.html",
                           league=league,
                           md=md,
                           pdf_file=candidate_pdf)

# =================================================================
# 6)  STARTUP
# =================================================================
if __name__ == "__main__":
    build_league_index()
    Thread(target=run_scheduler, daemon=True).start()
    app.secret_key = "change_me_for_prod"
    print(" * running on http://0.0.0.0:8000")
    WSGIServer(("", 8000), app).serve_forever()
