# api/app.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from datetime import datetime
import pandas as pd
import numpy as np
from shared.db import get_collection

# Use the same port as defined in .env
PORT = int(os.getenv("API_PORT", 5001))

app = Flask(__name__)

# --------- Helpers ---------
def parse_float(name):
    v = request.args.get(name)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None

def parse_int(name, default=None, clamp=None):
    v = request.args.get(name)
    if v is None:
        return default
    try:
        v = int(v)
        if clamp:
            v = max(clamp[0], min(clamp[1], v))
        return v
    except ValueError:
        return default

def parse_ts(name):
    v = request.args.get(name)
    if not v:
        return None
    try:
        return pd.to_datetime(v, utc=True)
    except Exception:
        return None

# --------- Routes ---------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/api/observations")
def observations():
    coll = get_collection()
    q = {}

    # Filters
    start = parse_ts("start")
    end = parse_ts("end")
    if start or end:
        q["timestamp"] = {}
        if start is not None:
            q["timestamp"]["$gte"] = start
        if end is not None:
            q["timestamp"]["$lte"] = end
        if not q["timestamp"]:
            q.pop("timestamp")

        for db_field, (mn_key, mx_key) in {
            "Temperature (c)": ("min_temp", "max_temp"),
            "Salinity (ppt)": ("min_sal", "max_sal"),
            "ODO mg/L": ("min_odo", "max_odo"),
        }.items():
            mn = parse_float(mn_key)
            mx = parse_float(mx_key)
            if mn is not None or mx is not None:
                cond = {}
                if mn is not None:
                    cond["$gte"] = mn
                if mx is not None:
                    cond["$lte"] = mx
                q[db_field] = cond

        mn = parse_float(mn_key)
        mx = parse_float(mx_key)
        if mn is not None or mx is not None:
            cond = {}
            if mn is not None:
                cond["$gte"] = mn
            if mx is not None:
                cond["$lte"] = mx
            q[fld] = cond

    limit = parse_int("limit", default=100, clamp=(1, 1000))
    skip = parse_int("skip", default=0, clamp=(0, 10000000))

    cursor = coll.find(q).skip(skip).limit(limit)
    items = []
    for doc in cursor:
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), (pd.Timestamp, datetime)):
            doc["timestamp"] = pd.to_datetime(doc["timestamp"]).isoformat()
        items.append(doc)

    count = coll.count_documents(q)
    return jsonify({"count": count, "items": items})

@app.get("/api/stats")
def stats():
    coll = get_collection()
    docs = list(coll.find({}, {"_id": 0}))
    if not docs:
        return jsonify({"message": "no data"}), 200

    df = pd.DataFrame(docs)
    fields = [c for c in ["temperature", "salinity", "odo"] if c in df.columns]
    out = {}
    for fld in fields:
        s = pd.to_numeric(df[fld], errors="coerce").dropna()
        if s.empty:
            continue
        out[fld] = {
            "count": int(s.count()),
            "mean": float(s.mean()),
            "min": float(s.min()),
            "max": float(s.max()),
            "p25": float(s.quantile(0.25)),
            "p50": float(s.quantile(0.50)),
            "p75": float(s.quantile(0.75)),
        }
    return jsonify(out)

@app.get("/api/outliers")
def outliers():
    fld = request.args.get("field", "temperature")
    method = request.args.get("method", "iqr").lower()
    k = parse_float("k") or 1.5

    coll = get_collection()
    docs = list(coll.find({}, {"_id": 0}))
    if not docs:
        return jsonify({"items": []})

    df = pd.DataFrame(docs)
    if fld not in df.columns:
        return jsonify({"items": [], "warning": f"field '{fld}' not found"})

    s = pd.to_numeric(df[fld], errors="coerce")
    mask = pd.Series(False, index=df.index)

    if method in ["z", "zscore"]:
        mu, sd = s.mean(), s.std(ddof=0)
        if sd and not np.isnan(sd):
            z = (s - mu) / sd
            mask = z.abs() > k
    else:
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - k * iqr
        upper = q3 + k * iqr
        mask = (s < lower) | (s > upper)

    flagged = df[mask].copy()
    if "timestamp" in flagged.columns:
        flagged["timestamp"] = pd.to_datetime(flagged["timestamp"], errors="coerce").astype(str)

    items = flagged.to_dict(orient="records")
    return jsonify({"count": len(items), "items": items})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
