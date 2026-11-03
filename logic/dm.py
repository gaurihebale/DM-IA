"""
dm.py - all the Discrete Mathematics of UroLogic (pure functions, no web code).

Topics used, and the job each one does:
  0. Threshold rule   value -> NORMAL < ABNORMAL < CRITICAL      (a total order)
  1. Logic            rules as propositions, truth tables, modus ponens
  2. Quantifiers      patient status: ∃ critical, ∃ abnormal, ∀ normal
  3. Sets             which patients match a rule (∩, ∪, complement)
  4. Relations        patients with the same profile = equivalence classes
  5. Poset            "at least as bad as" order, Hasse diagram, review order
  6. Functions        the hash function h: IDs -> buckets, pigeonhole principle
"""

from itertools import product
from math import ceil

# ===========================================================================
# 0. ANALYTES AND THE THRESHOLD RULE
# ===========================================================================
# name: (unit, normal_low, normal_high, critical_low, critical_high, min, max)
#   normal range is  normal_low <= value < normal_high
#   value < critical_low  or  value >= critical_high   -> CRITICAL
#   otherwise outside the normal range                 -> ABNORMAL
#   min/max = physically possible readings; anything outside is a typo.
# Most analytes are only dangerous when HIGH, so their lows are 0.
# pH and specific gravity are also abnormal when too LOW.
# Glucose limits (160 / 250) come from the design doc; the rest are
# simulation values for a student project, not clinical cut-offs.
ANALYTES = {
    "Glucose":          ("mg/dL",    0,     160,   0,     250,   0,     2000),
    "Protein":          ("mg/dL",    0,     30,    0,     300,   0,     2000),
    "pH":               ("pH",       4.5,   8.0,   4.0,   9.0,   0,     14),
    "Ketones":          ("mg/dL",    0,     15,    0,     80,    0,     200),
    "Blood":            ("Ery/uL",   0,     10,    0,     50,    0,     500),
    "Bilirubin":        ("mg/dL",    0,     1,     0,     4,     0,     20),
    "Urobilinogen":     ("mg/dL",    0,     2,     0,     8,     0,     20),
    "Nitrite":          ("mg/dL",    0,     0.05,  0,     0.5,   0,     5),
    "Leucocytes":       ("cells/uL", 0,     25,    0,     500,   0,     1000),
    "Specific Gravity": ("SG",       1.005, 1.030, 1.001, 1.040, 1.000, 1.060),
}
ANALYTE_ORDER = list(ANALYTES)                     # fixed positions for vectors
LEVELS = ["NORMAL", "ABNORMAL", "CRITICAL"]        # index = rank (a chain)
RANK = {name: i for i, name in enumerate(LEVELS)}  # "CRITICAL" -> 2


def is_possible(analyte, value):
    """Reject impossible readings (pH 20, SG 5) before they are stored."""
    lo, hi = ANALYTES[analyte][5], ANALYTES[analyte][6]
    return lo <= value <= hi


def classify(analyte, value):
    """Map a value onto the total order NORMAL < ABNORMAL < CRITICAL. O(1)."""
    _u, n_lo, n_hi, c_lo, c_hi, _mn, _mx = ANALYTES[analyte]
    if value < c_lo or value >= c_hi:
        return "CRITICAL"
    if value < n_lo or value >= n_hi:
        return "ABNORMAL"
    return "NORMAL"


# ===========================================================================
# 1. PROPOSITIONAL LOGIC
# ===========================================================================
# A formula is an EXPRESSION TREE of tuples:
#   "Glucose"         atom  p = "Glucose is ABNORMAL or worse"
#   ("NOT", f)        ¬f
#   ("AND", f, g)     f ∧ g
#   ("OR", f, g)      f ∨ g
# One recursive function evaluates any tree, however deeply nested.
SYMBOL = {"AND": "∧", "OR": "∨"}

# Each rule is an implication  condition → finding.
# Teaching examples of screening combinations, not diagnoses.
RULES = [
    {"name": "Possible urinary tract infection", "formula": ("AND", "Nitrite", "Leucocytes"),
     "advice": "Suggest urine culture"},
    {"name": "Possible diabetic ketoacidosis", "formula": ("AND", "Glucose", "Ketones"),
     "advice": "Suggest blood glucose and ketone test"},
    {"name": "Possible kidney damage", "formula": ("AND", "Protein", "Blood"),
     "advice": "Suggest kidney function test"},
    {"name": "Possible liver problem", "formula": ("OR", "Bilirubin", "Urobilinogen"),
     "advice": "Suggest liver function test"},
    {"name": "High sugar without ketones", "formula": ("AND", "Glucose", ("NOT", "Ketones")),
     "advice": "Suggest HbA1c test"},
]


def evaluate(f, truth):
    """Truth value of formula f, given truth = {atom: True/False}. Recursive."""
    if isinstance(f, str):
        return truth[f]
    if f[0] == "NOT":
        return not evaluate(f[1], truth)
    a, b = evaluate(f[1], truth), evaluate(f[2], truth)
    return (a and b) if f[0] == "AND" else (a or b)


def atoms(f):
    """Sorted list of the atomic propositions inside f."""
    if isinstance(f, str):
        return [f]
    return sorted({x for sub in f[1:] for x in atoms(sub)})


def to_text(f):
    if isinstance(f, str):
        return f
    if f[0] == "NOT":
        return "¬" + to_text(f[1])
    return f"({to_text(f[1])} {SYMBOL[f[0]]} {to_text(f[2])})"


def truth_table(f):
    """All 2^n rows. product([T, F], repeat=n) is the Cartesian product
    {T,F} x ... x {T,F}, i.e. every possible assignment."""
    names = atoms(f)
    rows = [(vals, evaluate(f, dict(zip(names, vals))))
            for vals in product([True, False], repeat=len(names))]
    return names, rows


def de_morgan_holds():
    """Law check: ¬(p ∧ q) ≡ ¬p ∨ ¬q in every row. The 'High sugar without
    ketones' rule relies on ¬ behaving this way."""
    left = ("NOT", ("AND", "p", "q"))
    right = ("OR", ("NOT", "p"), ("NOT", "q"))
    return all(evaluate(left, dict(p=p, q=q)) == evaluate(right, dict(p=p, q=q))
               for p, q in product([True, False], repeat=2))


def propositions(levels):
    """levels = {analyte: level} for the analytes this patient was TESTED for.
    p_a is True when a is ABNORMAL or CRITICAL. An untested analyte is False:
    we cannot claim it is abnormal, so no rule fires on missing data."""
    return {a: RANK[levels[a]] >= 1 if a in levels else False for a in ANALYTE_ORDER}


def infer(levels):
    """MODUS PONENS: rule (condition → finding) + condition true ⇒ finding."""
    truth = propositions(levels)
    return [r for r in RULES if evaluate(r["formula"], truth)]


# ===========================================================================
# 2. PREDICATES AND QUANTIFIERS
# ===========================================================================
# Domain D = the analytes this patient was tested for (not all 10:
# "every test is normal" must only talk about tests that were done).
#   ∃a C(a)       -> CRITICAL      any() is "there exists"
#   else ∃a A(a)  -> ABNORMAL
#   else ∀a N(a)  -> NORMAL        all() is "for all"
def overall_status(levels):
    tested = levels.values()
    if any(lv == "CRITICAL" for lv in tested):
        return "CRITICAL"
    if any(lv == "ABNORMAL" for lv in tested):
        return "ABNORMAL"
    assert all(lv == "NORMAL" for lv in tested)
    return "NORMAL"


# ===========================================================================
# 3. SET THEORY
# ===========================================================================
# U = all patients, S_a = patients whose analyte a is abnormal.
# The same rule tree is evaluated on sets: ∧ -> ∩, ∨ -> ∪, ¬ -> U − S.
# This works because sets and truth values are both Boolean algebras.
def analyte_sets(all_levels):
    return {a: {p for p, lv in all_levels.items() if propositions(lv)[a]}
            for a in ANALYTE_ORDER}


def evaluate_sets(f, sets, universe):
    if isinstance(f, str):
        return sets[f]
    if f[0] == "NOT":
        return universe - evaluate_sets(f[1], sets, universe)
    a, b = evaluate_sets(f[1], sets, universe), evaluate_sets(f[2], sets, universe)
    return (a & b) if f[0] == "AND" else (a | b)


# ===========================================================================
# 4. RELATIONS: EQUIVALENCE
# ===========================================================================
# profile(p) = 10-number vector of ranks, one position per analyte
#              (untested counts as 0, same as for the propositions).
# x R y  <=>  profile(x) == profile(y)
# R is reflexive, symmetric and transitive (checked on its 0/1 matrix), so
# it splits patients into EQUIVALENCE CLASSES: same class = same follow-up.
def profile(levels):
    return tuple(RANK[levels[a]] if a in levels else 0 for a in ANALYTE_ORDER)


def relation_matrix(items, related):
    return [[1 if related(x, y) else 0 for y in items] for x in items]


def is_reflexive(M):
    return all(M[i][i] for i in range(len(M)))


def is_symmetric(M):
    n = len(M)
    return all(M[i][j] == M[j][i] for i in range(n) for j in range(n))


def is_antisymmetric(M):
    n = len(M)
    return all(not (M[i][j] and M[j][i]) for i in range(n) for j in range(n) if i != j)


def is_transitive(M):
    """M[i][j] and M[j][k]  ⇒  M[i][k], for all i, j, k.  O(n^3)."""
    n = len(M)
    return all(M[i][k] or not (M[i][j] and M[j][k])
               for i in range(n) for j in range(n) for k in range(n))


def equivalence_classes(profiles):
    """Group patients by vector. Returns [(vector, [patients])], worst first."""
    groups = {}
    for patient, vec in sorted(profiles.items()):
        groups.setdefault(vec, []).append(patient)
    return sorted(groups.items(), key=lambda kv: (-sum(kv[0]), kv[1]))


def describe(vec):
    """'Glucose:C, Ketones:A' or 'all normal'."""
    return ", ".join(f"{a}:{LEVELS[r][0]}" for a, r in zip(ANALYTE_ORDER, vec) if r) or "all normal"


# ===========================================================================
# 5. PARTIAL ORDER (POSET) AND HASSE DIAGRAM
# ===========================================================================
# On classes:  u ≤ v  <=>  u[i] ≤ v[i] for every analyte i
# ("v is at least as bad as u in every test").
# Reflexive, antisymmetric (classes have distinct vectors), transitive
# => a partial order. Not total: "only Glucose bad" and "only Protein bad"
# cannot be compared.
def leq(u, v):
    return all(a <= b for a, b in zip(u, v))


def hasse_edges(nodes):
    """Covering pairs u ⋖ v: u < v with nothing strictly in between.
    Only these are drawn; loops and transitive shortcuts are dropped."""
    return [(u, v) for u in nodes for v in nodes
            if u != v and leq(u, v)
            and not any(w not in (u, v) and leq(u, w) and leq(w, v) for w in nodes)]


def maximal(nodes):
    """Nothing is worse than these -> review first."""
    return [u for u in nodes if not any(v != u and leq(u, v) for v in nodes)]


def review_order(nodes, edges):
    """TOPOLOGICAL SORT (Kahn's algorithm), worst first: a class is listed
    only after every class above it. Ties: higher total severity first."""
    above = {n: 0 for n in nodes}
    for u, _v in edges:
        above[u] += 1
    ready, order = [n for n in nodes if above[n] == 0], []
    while ready:
        ready.sort(key=lambda n: (-sum(n), n))
        n = ready.pop(0)
        order.append(n)
        for u, v in edges:
            if v == n:
                above[u] -= 1
                if above[u] == 0:
                    ready.append(u)
    return order


def hasse_layout(nodes, edges, width=680, gap=110, margin=50):
    """(x, y) for each node. Row = height = longest chain below the node.
    Sorting by sum is a valid topological order (u < v ⇒ sum(u) < sum(v)),
    so every lower node's height is known before it is needed."""
    if not nodes:
        return {}, 0
    height = {}
    for n in sorted(nodes, key=sum):
        height[n] = 1 + max((height[u] for u, v in edges if v == n), default=-1)
    top, rows = max(height.values()), {}
    for n in sorted(nodes, key=lambda n: (-sum(n), n)):
        rows.setdefault(height[n], []).append(n)
    pos = {}
    for h, row in rows.items():
        for i, n in enumerate(row):
            pos[n] = (round(width / (len(row) + 1) * (i + 1)), margin + (top - h) * gap)
    return pos, margin * 2 + top * gap


# ===========================================================================
# 6. FUNCTIONS AND THE PIGEONHOLE PRINCIPLE
# ===========================================================================
# h : PatientIDs -> {0, ..., m-1} is a function (every ID has one bucket).
#   injective  = no two IDs share a bucket (no collisions)
#   surjective = every bucket is used
# PIGEONHOLE: n IDs in m buckets with n > m forces a collision;
# generalised, some bucket holds at least ceil(n / m) IDs.
def function_report(keys, h, m):
    image = {}
    for k in keys:
        image.setdefault(h(k), []).append(k)
    n = len(keys)
    return {
        "n": n, "m": m,
        "mapping": sorted((k, h(k)) for k in keys),
        "injective": all(len(v) == 1 for v in image.values()),
        "surjective": len(image) == m,
        "collisions": {b: ks for b, ks in sorted(image.items()) if len(ks) > 1},
        "forced": n > m,
        "at_least": ceil(n / m) if n else 0,
        "fullest": max((len(v) for v in image.values()), default=0),
    }
