"""
Turn an Apple Health export into one row per day.

  iPhone: Health app -> your photo (top right) -> Export All Health Data -> save export.zip
  AirDrop it to the Mac, then:
      ./.venv/bin/python notebooks/03_apple_health.py ~/Downloads/export.zip

Writes data/health_daily.csv. Streams the XML, so multi-GB exports are fine.
Night-time metrics are attributed to the date you WOKE UP.
"""
import sys, zipfile, collections, datetime as dt
import xml.etree.ElementTree as ET
import pandas as pd

QTY = {
    "HKQuantityTypeIdentifierRestingHeartRate":           "rhr",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":   "hrv",
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": "wrist_temp",
    "HKQuantityTypeIdentifierRespiratoryRate":            "resp_rate",
    "HKQuantityTypeIdentifierStepCount":                  "steps",
    "HKQuantityTypeIdentifierAppleExerciseTime":          "exercise_min",
    "HKQuantityTypeIdentifierActiveEnergyBurned":         "active_kcal",
    "HKQuantityTypeIdentifierOxygenSaturation":           "spo2",
}
SUM_FIELDS = {"steps", "exercise_min", "active_kcal"}
ASLEEP = {"HKCategoryValueSleepAnalysisAsleepCore", "HKCategoryValueSleepAnalysisAsleepDeep",
          "HKCategoryValueSleepAnalysisAsleepREM", "HKCategoryValueSleepAnalysisAsleepUnspecified",
          "HKCategoryValueSleepAnalysisAsleep"}

def ts(s):  # "2026-09-19 07:12:00 +0200"
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")

def open_xml(path):
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if n.endswith("export.xml") and "cda" not in n.lower())
        return z.open(name)
    return open(path, "rb")

def parse(path):
    vals = collections.defaultdict(lambda: collections.defaultdict(list))
    sleep_min = collections.defaultdict(float)
    flow, ovu = {}, {}
    for _, el in ET.iterparse(open_xml(path), events=("end",)):
        if el.tag != "Record":
            continue
        t = el.get("type"); a = el.attrib
        if t in QTY:
            day = ts(a["endDate"]).date()
            try: vals[QTY[t]][day].append(float(a["value"]))
            except (KeyError, ValueError): pass
        elif t == "HKCategoryTypeIdentifierSleepAnalysis" and a.get("value") in ASLEEP:
            s, e = ts(a["startDate"]), ts(a["endDate"])
            sleep_min[e.date()] += (e - s).total_seconds() / 60
        elif t == "HKCategoryTypeIdentifierMenstrualFlow":
            flow[ts(a["startDate"]).date()] = a.get("value", "").replace("HKCategoryValueMenstrualFlow", "")
        elif t == "HKCategoryTypeIdentifierOvulationTestResult":
            ovu[ts(a["startDate"]).date()] = a.get("value", "").replace("HKCategoryValueOvulationTestResult", "")
        el.clear()

    days = set(sleep_min) | set(flow) | set(ovu)
    for f in vals: days |= set(vals[f])
    rows = []
    for d in sorted(days):
        r = {"date": d.isoformat()}
        for f in QTY.values():
            v = vals[f].get(d)
            r[f] = (sum(v) if f in SUM_FIELDS else sum(v) / len(v)) if v else None
        r["sleep_h"] = round(sleep_min[d] / 60, 2) if d in sleep_min else None
        r["hk_flow"] = flow.get(d); r["hk_ovulation_test"] = ovu.get(d)
        rows.append(r)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/export.zip"
    df = parse(src)
    df.to_csv("data/health_daily.csv", index=False)
    print(f"{len(df)} days, {df.date.min()} -> {df.date.max()}  -> data/health_daily.csv")
    print(df.notna().mean().round(2).to_string())
