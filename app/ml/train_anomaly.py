import os
import logging
import joblib
import numpy as np
from app import db
from app.models.order_model import SalesRecord

logger = logging.getLogger(__name__)
ANOMALY_MODEL_PATH = os.path.join(os.path.dirname(__file__), "anomaly_model.pkl")


def run():
    rows = db.session.query(SalesRecord.revenue).filter(SalesRecord.revenue.isnot(None)).all()
    values = np.array([float(r[0]) for r in rows if r[0] is not None], dtype=float)
    if len(values) < 30:
        return {"status": "skipped", "message": "Not enough sales data to train anomaly model."}

    mean_rev = float(np.mean(values))
    std_rev = float(np.std(values))
    threshold = mean_rev + 2 * std_rev
    model = {
        "mean_revenue": round(mean_rev, 4),
        "std_revenue": round(std_rev, 4),
        "threshold": round(float(threshold), 4),
        "sample_count": int(len(values)),
    }
    joblib.dump(model, ANOMALY_MODEL_PATH)
    logger.info("Anomaly model trained and saved.")
    return {"status": "ok", "message": "Anomaly model trained.", "metrics": model}

