"""
backend/app.py - UroLogic BACKEND (Flask web server, no JavaScript).

Run from the "DM IA" folder:
    pip install -r requirements.txt
    python backend/app.py
Then open http://127.0.0.1:5000

Folders:  frontend/ = what you see   backend/ = this file   logic/ = the maths
Each @app.route function handles one URL. A form POST changes the data and
then redirects (Post/Redirect/Get), so refreshing never submits twice.
Jinja escapes every value, so typed text is shown as text, never run.
Data is kept in memory and is cleared when the server stops.
"""

import os
import re
import sys

from flask import Flask, flash, redirect, render_template, request, url_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)                     # so "logic" can be imported

from logic import dm                         # noqa: E402
from logic.system import UroLogic            # noqa: E402

app = Flask(__name__,
            template_folder=os.path.join(ROOT, "frontend", "templates"),
            static_folder=os.path.join(ROOT, "frontend", "static"))
app.secret_key = os.urandom(16)              # needed by flash() messages

uro = UroLogic()
PATIENT_ID = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,19}$")     # e.g. PT-101
ALIASES = {"sg": "Specific Gravity", "wbc": "Leucocytes", "rbc": "Blood", "sugar": "Glucose"}


def find_analyte(text):
    """Understand what the user typed: 'glu' -> Glucose, 'sg' -> Specific
    Gravity. Order: alias, exact name, then a prefix that matches ONE name.
    Returns (name, None) or (None, list of possible names)."""
    key = text.lower().replace(" ", "")
    if key in ALIASES:
        return ALIASES[key], None
    names = {a.lower().replace(" ", ""): a for a in dm.ANALYTE_ORDER}
    if key in names:
        return names[key], None
    hits = [a for k, a in names.items() if key and k.startswith(key)]
    return (hits[0], None) if len(hits) == 1 else (None, hits)


@app.context_processor
def shared():                                # names every template can use
    return {"ANALYTES": dm.ANALYTES, "describe": dm.describe, "to_text": dm.to_text}


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pid = request.form.get("patient", "").strip().upper()
        analyte, options = find_analyte(request.form.get("analyte", ""))
        try:
            value = float(request.form.get("value", ""))
        except ValueError:
            value = None
        if not PATIENT_ID.match(pid):
            flash("Patient ID: letters, digits and '-' only, e.g. PT-101.", "error")
        elif analyte is None:
            flash("Did you mean: " + ", ".join(options) if options
                  else "Unknown analyte. Use one from the table below.", "error")
        elif value is None or value != value or not dm.is_possible(analyte, value):
            lo, hi = dm.ANALYTES[analyte][5], dm.ANALYTES[analyte][6]
            flash(f"{analyte} must be a number from {lo:g} to {hi:g}.", "error")
        else:
            rec = uro.add(pid, analyte, value)
            flash(f"Saved {pid}: {analyte} = {value:g} {rec['unit']} -> {rec['severity']}",
                  rec["severity"].lower())
        return redirect(url_for("home"))
    return render_template("home.html", n_patients=uro.patients.count,
                           n_records=len(uro.records()), n_alerts=len(uro.alerts))


@app.route("/demo", methods=["POST"])
def demo():
    flash(f"Loaded {uro.load_demo()} demo results for 9 patients.", "normal")
    return redirect(url_for("home"))


@app.route("/reset", methods=["POST"])
def reset():
    uro.__init__()
    flash("All data cleared.", "normal")
    return redirect(url_for("home"))


@app.route("/records", methods=["GET", "POST"])
def records():
    if request.method == "POST":             # "Review top alert" button
        rec = uro.review_next()
        flash(f"Reviewed {rec['patient']} {rec['analyte']} ({rec['severity']})"
              if rec else "No alerts waiting.", "normal")
        return redirect(url_for("records"))
    query = request.args.get("patient", "").strip().upper()
    analyte = request.args.get("analyte", "Glucose")
    if analyte not in dm.ANALYTES:
        analyte = "Glucose"
    tree = uro.trees[analyte]
    return render_template("records.html", query=query,
                           found=uro.patients.search(query) if query else None,
                           analyte=analyte, sorted_values=tree.inorder(),
                           lo=tree.minimum(), hi=tree.maximum(),
                           pending=uro.alerts.ordered(), reviewed=uro.reviewed,
                           records=uro.records())


@app.route("/maths")
def maths():
    lv = uro.all_levels()
    patients = list(lv)
    # 1-2. logic + quantifiers: one row per patient
    summary = [{"patient": p, "status": dm.overall_status(l),
                "tested": len(l), "true": [a for a, t in dm.propositions(l).items() if t],
                "findings": dm.infer(l)} for p, l in lv.items()]
    # 1 + 3. each rule: truth table and the set of matching patients
    sets = dm.analyte_sets(lv)
    rules = []
    for r in dm.RULES:
        names, rows = dm.truth_table(r["formula"])
        rules.append({**r, "names": names, "rows": rows,
                      "patients": sorted(dm.evaluate_sets(r["formula"], sets, set(patients)))})
    # 4. equivalence relation
    prof = {p: dm.profile(l) for p, l in lv.items()}
    M = dm.relation_matrix(patients, lambda x, y: prof[x] == prof[y])
    eq = {"Reflexive": dm.is_reflexive(M), "Symmetric": dm.is_symmetric(M),
          "Transitive": dm.is_transitive(M)}
    classes = dm.equivalence_classes(prof)
    # 5. poset on the classes
    nodes = [vec for vec, _ in classes]
    P = dm.relation_matrix(nodes, dm.leq)
    po = {"Reflexive": dm.is_reflexive(P), "Antisymmetric": dm.is_antisymmetric(P),
          "Transitive": dm.is_transitive(P)}
    edges = dm.hasse_edges(nodes)
    pos, height = dm.hasse_layout(nodes, edges)
    # 6. the hash function
    fn = dm.function_report(uro.patients.keys(), uro.patients.hash, uro.patients.size)
    return render_template(
        "maths.html", summary=summary, rules=rules, de_morgan=dm.de_morgan_holds(),
        sets={a: sorted(s) for a, s in sets.items() if s},
        patients=patients, M=M, eq=eq, classes=classes, po=po, edges=edges,
        pos=pos, svg_height=height, maximal=dm.maximal(nodes),
        order=dm.review_order(nodes, edges), members=dict(classes),
        label={vec: f"C{i + 1}" for i, vec in enumerate(nodes)}, fn=fn)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)   # this computer only
