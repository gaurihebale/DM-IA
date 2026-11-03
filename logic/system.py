"""
system.py - joins the Data Structures (ds.py) and the Discrete Maths (dm.py).

One test result flows like this:
    patient ID, analyte, value
      -> dm.classify    NORMAL / ABNORMAL / CRITICAL
      -> HashTable      patient ID -> list of records
      -> BST            one tree per analyte, ordered by value
      -> MaxHeap        only ABNORMAL / CRITICAL results, most severe first
The maths pages then read the stored records through levels().
"""

from datetime import datetime

from logic import dm
from logic.ds import BST, HashTable, MaxHeap


class UroLogic:
    def __init__(self):
        self.patients = HashTable()
        self.trees = {a: BST() for a in dm.ANALYTE_ORDER}
        self.alerts = MaxHeap()
        self.reviewed = []      # alerts already handled, newest first
        self.seq = 0            # arrival number; also the heap's tie-break

    def add(self, patient_id, analyte, value):
        self.seq += 1
        rec = {"seq": self.seq, "patient": patient_id, "analyte": analyte,
               "value": value, "unit": dm.ANALYTES[analyte][0],
               "severity": dm.classify(analyte, value),
               "time": datetime.now().strftime("%d-%m-%Y %H:%M")}
        self.patients.insert(patient_id, rec)
        self.trees[analyte].insert(rec)
        if rec["severity"] != "NORMAL":
            self.alerts.push(rec)
        return rec

    def review_next(self):
        rec = self.alerts.pop()
        if rec:
            self.reviewed.insert(0, rec)
        return rec

    def records(self):
        return sorted(self.patients.all_records(), key=lambda r: r["seq"])

    def levels(self, patient_id):
        """{analyte: level} using the LATEST reading of each tested analyte.
        A re-test replaces the old reading; untested analytes are left out."""
        latest = {}
        for r in self.patients.search(patient_id) or []:
            if r["analyte"] not in latest or r["seq"] > latest[r["analyte"]]["seq"]:
                latest[r["analyte"]] = r
        return {a: r["severity"] for a, r in latest.items()}

    def all_levels(self):
        return {p: self.levels(p) for p in sorted(self.patients.keys())}

    def load_demo(self):
        """Replaces all data with 20 sample results for 9 patients.
        PT-101..PT-105 glucose values follow the design-doc example; the
        other values were chosen so every rule and relation has data."""
        self.__init__()
        data = [
            ("PT-101", "Glucose", 90), ("PT-101", "Protein", 10),
            ("PT-102", "Glucose", 180), ("PT-102", "Ketones", 20),
            ("PT-103", "Glucose", 260), ("PT-103", "Ketones", 95),
            ("PT-104", "Glucose", 110), ("PT-104", "Nitrite", 0.1), ("PT-104", "Leucocytes", 80),
            ("PT-105", "Glucose", 200), ("PT-105", "Protein", 40), ("PT-105", "Blood", 20),
            ("PT-106", "Bilirubin", 2), ("PT-106", "Nitrite", 0.6), ("PT-106", "Leucocytes", 600),
            ("PT-107", "Glucose", 95), ("PT-107", "pH", 4.2),
            ("PT-108", "Glucose", 170), ("PT-108", "Ketones", 18),
            ("PT-109", "Glucose", 175),
        ]
        for pid, analyte, value in data:
            self.add(pid, analyte, value)
        return len(data)
