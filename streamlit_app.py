"""Streamlit interface for the UroLogic screening demonstration."""

import math
import re

import streamlit as st

from logic import dm
from logic.system import UroLogic


st.set_page_config(page_title="UroLogic", page_icon="🧪", layout="wide")

if "uro" not in st.session_state:
    st.session_state.uro = UroLogic()
uro = st.session_state.uro

ALIASES = {"sg": "Specific Gravity", "wbc": "Leucocytes", "rbc": "Blood", "sugar": "Glucose"}


def find_analyte(text):
    key = text.lower().replace(" ", "")
    if key in ALIASES:
        return ALIASES[key], []
    names = {a.lower().replace(" ", ""): a for a in dm.ANALYTE_ORDER}
    if key in names:
        return names[key], []
    hits = [a for k, a in names.items() if key and k.startswith(key)]
    return (hits[0], []) if len(hits) == 1 else (None, hits)


def records_table(records):
    if records:
        st.dataframe([{
            "Patient": r["patient"], "Analyte": r["analyte"],
            "Value": f'{r["value"]:g} {r["unit"]}', "Level": r["severity"], "Time": r["time"]
        } for r in records], use_container_width=True, hide_index=True)


def home_page():
    st.title("🧪 UroLogic")
    st.caption("Smart urine-strip screening with Discrete Mathematics · KJS-HC-03")
    st.info("A teaching simulation for screening combinations and prioritizing follow-up. Results are not a diagnosis; flagged results need a clinician.")
    a, b, c = st.columns(3)
    a.metric("Patients", uro.patients.count)
    b.metric("Results", len(uro.records()))
    c.metric("Alerts waiting", len(uro.alerts))

    st.subheader("Add a test result")
    with st.form("add_result", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1, 0.7])
        patient = c1.text_input("Patient ID", placeholder="PT-110")
        analyte_text = c2.text_input("Analyte", placeholder="Glucose, glu, sg…")
        value = c3.number_input("Value", value=0.0, step=1.0, format="%.4f")
        submitted = st.form_submit_button("Save result", type="primary")
    if submitted:
        pid = patient.strip().upper()
        analyte, options = find_analyte(analyte_text.strip())
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{0,19}", pid):
            st.error("Patient ID must contain only letters, digits and hyphens, e.g. PT-101.")
        elif analyte is None:
            st.error("Did you mean: " + ", ".join(options) if options else "Unknown analyte. Choose one from the table.")
        elif not dm.is_possible(analyte, value):
            lo, hi = dm.ANALYTES[analyte][5:7]
            st.error(f"{analyte} must be between {lo:g} and {hi:g}.")
        else:
            rec = uro.add(pid, analyte, value)
            st.success(f"Saved {pid}: {analyte} = {value:g} {rec['unit']} · {rec['severity']}")
            st.rerun()

    x, y = st.columns(2)
    if x.button("Load demo data", use_container_width=True):
        count = uro.load_demo()
        st.success(f"Loaded {count} sample results for 9 patients.")
        st.rerun()
    if y.button("Reset all data", use_container_width=True):
        st.session_state.uro = UroLogic()
        st.rerun()

    st.subheader("Thresholds")
    st.dataframe([{
        "Analyte": a, "Unit": row[0],
        "Normal range": f'{row[1]:g} to < {row[2]:g}',
        "Critical when": (f'< {row[3]:g} or ≥ {row[4]:g}' if row[3] else f'≥ {row[4]:g}'),
        "Accepted values": f"{row[5]:g}–{row[6]:g}"
    } for a, row in dm.ANALYTES.items()], use_container_width=True, hide_index=True)
    st.caption("Simulation thresholds for a student project, not clinical cut-offs.")


def records_page():
    st.title("Records & Alerts")
    st.subheader("Alert queue · max-heap, critical first")
    pending = uro.alerts.ordered()
    if st.button("Review top alert", disabled=not pending, type="primary"):
        rec = uro.review_next()
        st.toast(f"Reviewed {rec['patient']} · {rec['analyte']} · {rec['severity']}")
        st.rerun()
    records_table(pending)
    if not pending:
        st.caption("No alerts waiting.")
    if uro.reviewed:
        st.subheader("Reviewed alerts")
        records_table(uro.reviewed)

    st.subheader("Search a patient · hash table")
    query = st.text_input("Patient ID", placeholder="PT-103", key="patient_search").strip().upper()
    if query:
        found = uro.patients.search(query)
        records_table(found or [])
        if not found:
            st.caption(f"No patient {query}.")

    st.subheader("Sorted values · binary search tree inorder traversal")
    analyte = st.selectbox("Analyte", dm.ANALYTE_ORDER)
    sorted_values = uro.trees[analyte].inorder()
    if sorted_values:
        lo, hi = uro.trees[analyte].minimum(), uro.trees[analyte].maximum()
        st.write(f"Lowest: **{lo['value']:g}** ({lo['patient']}) · Highest: **{hi['value']:g}** ({hi['patient']})")
        records_table(sorted_values)
    else:
        st.caption(f"No {analyte} values yet.")

    st.subheader("All results")
    records_table(uro.records())


def maths_page():
    st.title("Discrete Mathematics")
    levels = uro.all_levels()
    if not levels:
        st.info("No data yet. Load demo data on the Home page.")
        return
    patients = list(levels)
    summary = []
    for patient, lv in levels.items():
        truth = dm.propositions(lv)
        summary.append({
            "Patient": patient, "Tested": f"{len(lv)}/10", "Status": dm.overall_status(lv),
            "True propositions": ", ".join(a for a, yes in truth.items() if yes) or "—",
            "Inferred findings": "; ".join(r["name"] for r in dm.infer(lv)) or "—"
        })
    st.header("1–2. Logic and quantifiers")
    st.caption("An analyte proposition is true when its latest result is abnormal or critical. Untested analytes are false.")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    sets = dm.analyte_sets(levels)
    st.header("3. Rules, truth tables and sets")
    st.write(f"De Morgan’s law checked across all four truth assignments: **{dm.de_morgan_holds()}**")
    for rule in dm.RULES:
        names, rows = dm.truth_table(rule["formula"])
        matching = sorted(dm.evaluate_sets(rule["formula"], sets, set(patients)))
        with st.expander(f"{rule['name']} · {dm.to_text(rule['formula'])} → finding", expanded=False):
            st.dataframe([{**dict(zip(names, ("T" if v else "F" for v in vals))), "Result": "T" if result else "F"}
                          for vals, result in rows], use_container_width=True, hide_index=True)
            st.write("Matching patients: " + (", ".join(matching) if matching else "∅"))
    st.dataframe([{"Set": f"S({a})", "Abnormal patients": ", ".join(sorted(ps)) or "∅", "Count": len(ps)}
                  for a, ps in sets.items() if ps], use_container_width=True, hide_index=True)

    st.header("4. Equivalence relation")
    profiles = {p: dm.profile(lv) for p, lv in levels.items()}
    classes = dm.equivalence_classes(profiles)
    matrix = dm.relation_matrix(patients, lambda x, y: profiles[x] == profiles[y])
    st.write("Reflexive, symmetric, transitive: **", dm.is_reflexive(matrix), ", ", dm.is_symmetric(matrix), ", ", dm.is_transitive(matrix), "**")
    st.dataframe([{"Class": f"C{i+1}", "Profile": dm.describe(vec), "Patients": ", ".join(members)}
                  for i, (vec, members) in enumerate(classes)], use_container_width=True, hide_index=True)
    if len(patients) <= 30:
        st.caption("Same-profile relation matrix (1 means related)")
        st.dataframe([{ "Patient": p, **{q: matrix[i][j] for j, q in enumerate(patients)} }
                      for i, p in enumerate(patients)], use_container_width=True, hide_index=True)

    st.header("5. Partial order and Hasse covers")
    nodes = [vec for vec, _ in classes]
    edges = dm.hasse_edges(nodes)
    poset = dm.relation_matrix(nodes, dm.leq)
    st.write("Reflexive, antisymmetric, transitive: **", dm.is_reflexive(poset), ", ", dm.is_antisymmetric(poset), ", ", dm.is_transitive(poset), "**")
    labels = {vec: f"C{i+1}" for i, (vec, _) in enumerate(classes)}
    st.write("Cover relations: " + (" · ".join(f"{labels[u]} → {labels[v]}" for u, v in edges) if edges else "none"))
    st.write("Maximal classes (review first): " + ", ".join(labels[n] for n in dm.maximal(nodes)))
    st.write("Review order: " + " → ".join(labels[n] for n in dm.review_order(nodes, edges)))

    st.header("6. Hash function and pigeonhole principle")
    fn = dm.function_report(uro.patients.keys(), uro.patients.hash, uro.patients.size)
    st.code(f"h(ID) = polynomial rolling hash(ID) mod {fn['m']}")
    st.write(f"Injective: **{fn['injective']}** · Surjective: **{fn['surjective']}** · IDs: **{fn['n']}** · buckets: **{fn['m']}**")
    st.dataframe([{"Patient ID": k, "Bucket": b} for k, b in fn["mapping"]], use_container_width=True, hide_index=True)
    st.write(f"Generalized pigeonhole bound: some bucket has at least ⌈n/m⌉ = **{fn['at_least']}** ID(s); fullest bucket: **{fn['fullest']}**.")


st.sidebar.title("UroLogic")
page = st.sidebar.radio("Navigate", ["Home", "Records & Alerts", "Discrete Maths"], label_visibility="collapsed")
if page == "Home":
    home_page()
elif page == "Records & Alerts":
    records_page()
else:
    maths_page()
