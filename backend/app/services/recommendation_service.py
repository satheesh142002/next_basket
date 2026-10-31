"""
Decision-Tree-based next-basket recommendation service.

The model predicts the product category a customer is most likely to buy next.
For each predicted category the API returns top-rated in-stock products.

Training samples are built in time order, one per (order, category in that order):
  features  - what was known BEFORE that order
              * normalised purchase frequency per category        (history)
              * categories of the other items in the same order   (cart context)
              * categories of the customer's previous order       (recency)
              * log(total units bought so far), log(orders so far) (activity)
  label     - the category of the item being bought

The data are split by time (oldest 80% train, newest 20% test) so the reported
accuracy reflects predicting the future, and the tuned Decision Tree is benchmarked
against a majority-class baseline, a Random Forest and Gradient Boosting.
"""

import json
import logging
import os
import pickle
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

logger = logging.getLogger(__name__)

_DIR = os.path.dirname(__file__)
MODEL_PATH      = os.path.normpath(os.path.join(_DIR, "../../ml_models/rec_model.pkl"))
ENCODER_PATH    = os.path.normpath(os.path.join(_DIR, "../../ml_models/rec_encoder.pkl"))
CATEGORIES_PATH = os.path.normpath(os.path.join(_DIR, "../../ml_models/categories.pkl"))
METRICS_PATH    = os.path.normpath(os.path.join(_DIR, "../../ml_models/rec_metrics.json"))

FEATURE_VERSION = 2


# ── Features ──────────────────────────────────────────────────────────────────

def feature_names(category_list: List[str]) -> List[str]:
    return (
        [f"history: {c}" for c in category_list]
        + [f"cart: {c}" for c in category_list]
        + [f"last order: {c}" for c in category_list]
        + ["activity: units bought", "activity: orders placed"]
    )


def _build_feature_vector(
    category_list: List[str],
    user_history: Dict[str, int],
    cart_categories: List[str],
    last_categories: Optional[List[str]] = None,
    n_orders: int = 0,
) -> np.ndarray:
    hist = np.array([user_history.get(c, 0) for c in category_list], dtype=float)
    total = hist.sum()
    freq = hist / total if total > 0 else hist
    cart = set(cart_categories or [])
    last = set(last_categories or [])
    return np.concatenate([
        freq,
        np.array([1.0 if c in cart else 0.0 for c in category_list]),
        np.array([1.0 if c in last else 0.0 for c in category_list]),
        [np.log1p(total), np.log1p(n_orders)],
    ])


def build_training_samples(orders: List[Dict], product_cat_map: Dict[str, str]) -> List[Dict]:
    """
    orders: dicts with customer_username, created_at and items[{product_id, quantity}].
    Returns time-ordered samples, each using only information from before its order.
    """
    by_user: Dict[str, List[Dict]] = defaultdict(list)
    for o in orders:
        if o.get("customer_username"):
            by_user[o["customer_username"]].append(o)

    samples: List[Dict] = []
    for uname, user_orders in by_user.items():
        user_orders.sort(key=lambda o: o.get("created_at") or datetime.min)
        history: Dict[str, int] = {}
        last_cats: List[str] = []
        for n, order in enumerate(user_orders):
            lines = []
            for item in order.get("items", []):
                cat = product_cat_map.get(item.get("product_id", ""), "")
                if cat:
                    lines.append((cat, int(item.get("quantity", 1))))
            cats_in_order = sorted({c for c, _ in lines})
            for target in cats_in_order:
                samples.append({
                    "user_history": dict(history),
                    "cart_categories": [c for c in cats_in_order if c != target],
                    "last_categories": list(last_cats),
                    "n_orders": n,
                    "target_category": target,
                    "time": order.get("created_at") or datetime.min,
                })
            for cat, qty in lines:
                history[cat] = history.get(cat, 0) + qty
            last_cats = cats_in_order
    samples.sort(key=lambda s: s["time"])
    return samples


# ── Evaluation helpers ────────────────────────────────────────────────────────

def _top_k_accuracy(model, X, y, k=3) -> float:
    proba = model.predict_proba(X)
    classes = model.classes_
    hits = 0
    for row, truth in zip(proba, y):
        top = classes[np.argsort(row)[::-1][:k]]
        hits += int(truth in top)
    return hits / len(y)


def _evaluate(model, X_test, y_test) -> Dict:
    pred = model.predict(X_test)
    return {
        "top1": round(float(accuracy_score(y_test, pred)), 4),
        "top3": round(float(_top_k_accuracy(model, X_test, y_test, 3)), 4),
        "macro_f1": round(float(f1_score(y_test, pred, average="macro", zero_division=0)), 4),
    }


def _group_importance(importances: np.ndarray, n_cats: int) -> Dict[str, float]:
    groups = {
        "Purchase history": importances[:n_cats].sum(),
        "Cart context": importances[n_cats:2 * n_cats].sum(),
        "Previous order": importances[2 * n_cats:3 * n_cats].sum(),
        "Activity level": importances[3 * n_cats:].sum(),
    }
    total = sum(groups.values()) or 1.0
    return {k: round(float(v / total), 4) for k, v in groups.items()}


# ── Training ──────────────────────────────────────────────────────────────────

def train_model(training_data: List[Dict], category_list: Optional[List[str]] = None, progress=None) -> Dict:
    """
    Tune and train the Decision Tree, benchmark it, save it and its metrics.
    `progress(pct, message)` is called between stages when given.
    """
    def tick(pct, msg):
        if progress:
            progress(pct, msg)

    if len(training_data) < 30:
        return {"status": "insufficient_data", "accuracy": 0.0, "samples": len(training_data)}

    cats = set(category_list or [])
    cats.update(r["target_category"] for r in training_data)
    cats.discard("")
    categories = sorted(cats)
    if len(categories) < 2:
        return {"status": "insufficient_classes", "accuracy": 0.0, "samples": len(training_data)}

    le = LabelEncoder().fit(categories)
    X = np.array([
        _build_feature_vector(categories, r["user_history"], r["cart_categories"],
                              r.get("last_categories"), r.get("n_orders", 0))
        for r in training_data
    ])
    y = le.transform([r["target_category"] for r in training_data])

    # Time-based split: samples are already sorted oldest -> newest
    cut = int(len(X) * 0.8)
    X_tr, X_te, y_tr, y_te = X[:cut], X[cut:], y[:cut], y[cut:]
    if len(X_te) < 10 or len(np.unique(y_tr)) < 2:
        X_tr, X_te, y_tr, y_te = X, X, y, y

    # 1. Baseline: always predict the most common training category
    majority = int(np.bincount(y_tr).argmax())
    base_top1 = float(np.mean(y_te == majority))
    counts = np.bincount(y_tr, minlength=len(le.classes_))
    base_top3_set = set(np.argsort(counts)[::-1][:3])
    base_top3 = float(np.mean([t in base_top3_set for t in y_te]))
    benchmark = [{"model": "Majority-class baseline", "top1": round(base_top1, 4),
                  "top3": round(base_top3, 4), "macro_f1": 0.0, "deployed": False}]

    # 2. Tune the Decision Tree with cross-validation on the training period
    tick(80, "Tuning Decision Tree (cross-validated grid search)…")
    min_class = int(np.bincount(y_tr)[np.bincount(y_tr) > 0].min())
    folds = max(2, min(4, min_class))
    grid = GridSearchCV(
        DecisionTreeClassifier(random_state=42, class_weight="balanced"),
        {"max_depth": [4, 6, 8, 12, None], "min_samples_leaf": [1, 5, 20],
         "criterion": ["gini", "entropy"]},
        scoring="f1_macro", cv=StratifiedKFold(folds, shuffle=True, random_state=42), n_jobs=1,
    )
    grid.fit(X_tr, y_tr)
    tree = grid.best_estimator_
    tree_scores = _evaluate(tree, X_te, y_te)
    benchmark.append({"model": "Decision Tree (tuned)", **tree_scores, "deployed": True})

    # 3. Benchmark against ensembles
    tick(90, "Benchmarking against Random Forest and Gradient Boosting…")
    for name, est in (
        ("Random Forest", RandomForestClassifier(n_estimators=150, min_samples_leaf=3, class_weight="balanced",
                                                 random_state=42, n_jobs=1)),
        ("Gradient Boosting", HistGradientBoostingClassifier(max_depth=6, learning_rate=0.1, max_iter=80,
                                                             random_state=42)),
    ):
        try:
            est.fit(X_tr, y_tr)
            benchmark.append({"model": name, **_evaluate(est, X_te, y_te), "deployed": False})
        except Exception as exc:  # a benchmark failure must not block training
            logger.warning("Benchmark %s failed: %s", name, exc)

    # 4. Refit the chosen tree on all data so the live model sees the newest orders
    tick(96, "Refitting the tuned tree on all data and saving…")
    final = DecisionTreeClassifier(random_state=42, class_weight="balanced", **grid.best_params_)
    final.fit(X, y)

    names = feature_names(categories)
    imp = final.feature_importances_
    top_idx = np.argsort(imp)[::-1][:8]
    per_class = []
    pred = tree.predict(X_te)
    for i, cls in enumerate(le.classes_):
        tp = int(np.sum((pred == i) & (y_te == i)))
        fp = int(np.sum((pred == i) & (y_te != i)))
        fn = int(np.sum((pred != i) & (y_te == i)))
        per_class.append({
            "category": cls,
            "support": int(np.sum(y_te == i)),
            "precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
            "recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
        })

    metrics = {
        "status": "trained",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_version": FEATURE_VERSION,
        "samples": int(len(X)),
        "train_samples": int(len(X_tr)),
        "test_samples": int(len(X_te)),
        "split": "time-based (oldest 80% train, newest 20% test)",
        "accuracy": tree_scores["top1"],
        "top1": tree_scores["top1"],
        "top3": tree_scores["top3"],
        "macro_f1": tree_scores["macro_f1"],
        "cv_macro_f1": round(float(grid.best_score_), 4),
        "best_params": {k: (v if v is not None else "none") for k, v in grid.best_params_.items()},
        "tree_depth": int(final.get_depth()),
        "tree_leaves": int(final.get_n_leaves()),
        "classes": list(le.classes_),
        "features": int(X.shape[1]),
        "benchmark": benchmark,
        "importance_groups": _group_importance(imp, len(categories)),
        "top_features": [{"feature": names[i], "importance": round(float(imp[i]), 4)} for i in top_idx if imp[i] > 0],
        "per_class": per_class,
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f: pickle.dump(final, f)
    with open(ENCODER_PATH, "wb") as f: pickle.dump(le, f)
    with open(CATEGORIES_PATH, "wb") as f: pickle.dump(categories, f)
    with open(METRICS_PATH, "w", encoding="utf-8") as f: json.dump(metrics, f)

    logger.info("Recommendation model trained: top1 %.3f top3 %.3f f1 %.3f (baseline top1 %.3f)",
                metrics["top1"], metrics["top3"], metrics["macro_f1"], base_top1)
    return metrics


# ── Prediction ────────────────────────────────────────────────────────────────

def predict_next_categories(
    user_history: Dict[str, int],
    cart_categories: List[str],
    top_n: int = 3,
    last_categories: Optional[List[str]] = None,
    n_orders: int = 0,
) -> List[str]:
    """Return up to top_n predicted categories for the user."""
    if not os.path.exists(MODEL_PATH):
        logger.warning("Recommendation model not trained yet.")
        return []
    try:
        with open(MODEL_PATH, "rb") as f: clf = pickle.load(f)
        with open(ENCODER_PATH, "rb") as f: le = pickle.load(f)
        with open(CATEGORIES_PATH, "rb") as f: category_list = pickle.load(f)
        feat = _build_feature_vector(category_list, user_history, cart_categories, last_categories, n_orders)
        if feat.shape[0] != clf.n_features_in_:
            logger.warning("Saved model uses an older feature set - retrain it from the admin Training page.")
            return []
        proba = clf.predict_proba([feat])[0]
    except Exception as e:
        logger.error("Failed to use recommendation model: %s", e)
        return []
    top_indices = np.argsort(proba)[::-1][:top_n]
    return [le.classes_[clf.classes_[i]] for i in top_indices if proba[i] > 0.01]


def is_model_trained() -> bool:
    return os.path.exists(MODEL_PATH)


def get_model_info() -> Dict:
    """Metadata and the last training metrics of the saved model."""
    if not is_model_trained():
        return {"trained": False}
    try:
        with open(CATEGORIES_PATH, "rb") as f:
            cats = pickle.load(f)
        trained_at = datetime.fromtimestamp(os.path.getmtime(MODEL_PATH), tz=timezone.utc).isoformat()
        info = {"trained": True, "categories": cats, "trained_at": trained_at}
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, encoding="utf-8") as f:
                info["metrics"] = json.load(f)
        return info
    except Exception:
        return {"trained": True}
