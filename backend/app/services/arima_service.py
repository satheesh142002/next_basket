"""
ARIMA-based sales forecasting service.

For each product the daily order quantities are aggregated into a weekly series,
then:
  1. the differencing order d is chosen with the ADF stationarity test,
  2. (p, q) is chosen by searching a small grid and minimising AICc,
  3. the model is back-tested on the last few weeks and compared with two simple
     baselines (mean of recent weeks, last value); the forecaster uses ARIMA only
     if it is at least as accurate as the mean baseline on that hold-out,
  4. the next 30 days are forecast with a 95% prediction interval and compared
     with current stock to flag a shortage.
"""

import itertools
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

MIN_ORDER_DAYS = 10


# ── Series preparation ────────────────────────────────────────────────────────

def weekly_series(order_history: List[Dict]) -> pd.Series:
    """order_history: [{'date': 'YYYY-MM-DD', 'quantity': int}] -> weekly unit totals."""
    df = pd.DataFrame(order_history)
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date")["quantity"].sum().sort_index()
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"), fill_value=0)
    return daily.astype(float).resample("W").sum()


def choose_d(series: pd.Series, max_d: int = 2) -> Tuple[int, List[float]]:
    """Smallest d that makes the series stationary (ADF p < 0.05); returns (d, p-value per step)."""
    s, pvals = series.copy(), []
    for d in range(max_d + 1):
        clean = s.dropna()
        try:
            p = float(adfuller(clean.values, autolag="AIC")[1]) if len(clean) > 8 else 1.0
        except Exception:
            p = 1.0
        pvals.append(p)
        if p < 0.05:
            return d, pvals
        s = s.diff()
    return max_d, pvals


# ── Model selection ───────────────────────────────────────────────────────────

def _aicc(fit, n: int) -> float:
    k = len(fit.params) + 1
    return float(fit.aic + (2 * k * (k + 1)) / max(n - k - 1, 1))


def select_order(series: pd.Series, d: Optional[int] = None, max_p: int = 2, max_q: int = 2):
    """Grid-search (p, q) at the given d by AICc. Returns (fit, order, candidates)."""
    if d is None:
        d, _ = choose_d(series)
    n = len(series)
    candidates, best = [], None
    for p, q in itertools.product(range(max_p + 1), range(max_q + 1)):
        try:
            fit = ARIMA(series.values, order=(p, d, q)).fit()
            score = _aicc(fit, n)
        except Exception:
            continue
        candidates.append({"order": [p, d, q], "aicc": round(score, 1)})
        if best is None or score < best[0]:
            best = (score, fit, (p, d, q))
    if best is None:
        fit = ARIMA(series.values, order=(0, 1, 0)).fit()
        return fit, (0, 1, 0), []
    candidates.sort(key=lambda c: c["aicc"])
    return best[1], best[2], candidates


def fit_arima(series: pd.Series, order: Tuple[int, int, int] = (1, 1, 1)):
    """Compatibility helper: best ARIMA by AICc (the `order` argument is only the fallback)."""
    try:
        return select_order(series)[0]
    except Exception:
        return ARIMA(series.values, order=order).fit()


# ── Validation ────────────────────────────────────────────────────────────────

def _errors(actual: np.ndarray, pred: np.ndarray) -> Dict[str, float]:
    err = actual - pred
    return {
        "mae": round(float(np.mean(np.abs(err))), 3),
        "rmse": round(float(np.sqrt(np.mean(err ** 2))), 3),
        "wape": round(float(np.sum(np.abs(err)) / max(np.sum(actual), 1e-9)), 3),
    }


def backtest(series: pd.Series) -> Optional[Dict]:
    """Hold out the last weeks, fit on the rest and compare ARIMA with the baselines."""
    n = len(series)
    h = min(8, max(4, n // 5))
    if n - h < 20:
        return None
    train, test = series.iloc[:-h], series.iloc[-h:]
    try:
        fit, order, _ = select_order(train)
        arima_pred = np.maximum(np.asarray(fit.forecast(steps=h), dtype=float), 0)
    except Exception as exc:
        logger.warning("Backtest ARIMA failed: %s", exc)
        return None
    mean_pred = np.full(h, train.iloc[-8:].mean())
    last_pred = np.full(h, train.iloc[-1])
    actual = test.values
    res = {
        "horizon_weeks": int(h),
        "order": list(order),
        "arima": _errors(actual, arima_pred),
        "naive_mean": _errors(actual, mean_pred),
        "naive_last": _errors(actual, last_pred),
        "dates": [d.strftime("%Y-%m-%d") for d in test.index],
        "actual": [round(float(v), 3) for v in actual],
        "predicted": [round(float(v), 3) for v in arima_pred],
        "train_tail": [{"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 3)}
                       for d, v in zip(train.index[-26:], train.values[-26:])],
    }
    res["chosen"] = "arima" if res["arima"]["mae"] <= res["naive_mean"]["mae"] else "naive_mean"
    return res


# ── Forecast ──────────────────────────────────────────────────────────────────

def _daily_from_weekly(weekly: np.ndarray, horizon: int) -> List[float]:
    return [float(weekly[i // 7]) / 7.0 for i in range(horizon)]


def forecast_product(order_history: List[Dict], current_stock: int, horizon: int = 30) -> Dict:
    """
    Returns daily forecast arrays (for the chart), a 95% interval, the total 30-day demand,
    the shortage flag and the model-quality details (order, AICc, back-test errors).
    """
    dates = [(datetime.today() + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(horizon)]

    def pack(method, values, lower, upper, extra=None):
        total = round(sum(values))
        out = {
            "method": method,
            "forecast_dates": dates,
            "forecast_values": [round(v, 2) for v in values],
            "lower_values": [round(max(v, 0), 2) for v in lower],
            "upper_values": [round(v, 2) for v in upper],
            "total_forecasted_demand": total,
            "current_stock": current_stock,
            "shortage_predicted": current_stock < total,
            "shortage_units": max(0, total - current_stock),
        }
        out.update(extra or {})
        return out

    if len({r["date"] for r in order_history}) < MIN_ORDER_DAYS:
        avg_daily = sum(r["quantity"] for r in order_history) / len(order_history) if order_history else 1.0
        vals = [avg_daily] * horizon
        return pack("naive_mean", vals, [0.0] * horizon, [avg_daily * 2] * horizon, {"backtest": None})

    series = weekly_series(order_history)
    weeks = int(np.ceil(horizon / 7))
    bt = backtest(series)
    use_arima = bt is None or bt["chosen"] == "arima"

    method, extra = "naive_mean", {"backtest": bt}
    w_mean = np.full(weeks, series.iloc[-8:].mean())
    resid_sd = float(series.iloc[-26:].std() or 0.0)
    w_low = np.maximum(w_mean - 1.96 * resid_sd, 0)
    w_high = w_mean + 1.96 * resid_sd
    w_fc = w_mean

    if use_arima:
        try:
            fit, order, _ = select_order(series)
            res = fit.get_forecast(steps=weeks)
            w_fc = np.maximum(np.asarray(res.predicted_mean, dtype=float), 0)
            ci = np.asarray(res.conf_int(alpha=0.05), dtype=float)
            w_low, w_high = np.maximum(ci[:, 0], 0), np.maximum(ci[:, 1], w_fc)
            method = "arima"
            extra.update({"order": list(order), "aic": round(float(fit.aic), 1)})
        except Exception as exc:
            logger.error("ARIMA forecast failed: %s", exc)

    return pack(method, _daily_from_weekly(w_fc, horizon), _daily_from_weekly(w_low, horizon),
                _daily_from_weekly(w_high, horizon), extra)


def get_stock_alerts(products_forecast: List[Dict]) -> List[Dict]:
    """Filter products where a shortage is predicted."""
    return [p for p in products_forecast if p.get("shortage_predicted")]
