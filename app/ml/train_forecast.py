import logging
from app.ml.demand_forecast import train_model

logger = logging.getLogger(__name__)


def run():
    result = train_model()
    if not result:
        return {"status": "skipped", "message": "Not enough sales data to train forecast model."}
    return {"status": "ok", "message": "Forecast model trained.", "metrics": result}

