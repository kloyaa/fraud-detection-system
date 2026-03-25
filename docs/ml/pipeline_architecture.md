# ML Pipeline Architecture
## Risk Assessment System (RAS) — Machine Learning Infrastructure

```yaml
document:       docs/ml/pipeline_architecture.md
version:        1.0.0
owner:          Dr. Yuki Tanaka (@yuki) — Lead ML / Risk Scientist
reviewers:      "@marcus · @darius · @priya · @sofia · @aisha"
last_updated:   Pre-development
status:         Approved
classification: Internal — Confidential — Model Governance
```

---

## 1. Overview

The RAS ML pipeline is a dual-path architecture:

- **Online path** — real-time feature serving (sub-5ms) via Feast + Redis, real-time inference via BentoML. This path is in the scoring hot path — every millisecond counts.
- **Offline path** — batch feature engineering via PySpark + Snowflake, model training, evaluation, and model registry management via MLflow. This path runs on a schedule — latency is irrelevant, correctness is everything.

The two paths are connected by **Feast** — the feature store that serves as the contract between the offline world (training) and the online world (serving). The single most important engineering principle in this document:

> *@yuki:* "Training-serving skew — computing features differently in training vs. serving — is the primary cause of model performance degradation in production. Feast enforces a single feature definition used for both. If you are computing a feature differently in your training pipeline vs. your serving pipeline, you are not building an ML system. You are building two different systems that happen to share a model weight file."

---

## 2. Pipeline Architecture Diagram

```
═══════════════════════════════════════════════════════════════════
                        OFFLINE PATH
═══════════════════════════════════════════════════════════════════

Snowflake (risk.training_transactions)
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  PySpark Batch Feature Pipeline (runs every 6 hours)          │
│                                                               │
│  Computes:                                                    │
│    customer_avg_amount_30d                                    │
│    customer_age_days                                          │
│    merchant_fraud_rate_30d                                    │
│    device_account_count_7d (from Neo4j graph snapshot)        │
│    linked_fraud_ring_score (from Neo4j graph snapshot)        │
│    ... 20 batch features total                                │
│                                                               │
│  Output: Feast offline store (Snowflake feature tables)       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Model Training Pipeline                                      │
│                                                               │
│  1. Point-in-time correct feature retrieval (Feast offline)   │
│  2. Label join (chargeback / merchant feedback / SAR)         │
│  3. Temporal train/val/test split (NO shuffle)                │
│  4. XGBoost DART training (GPU A10G)                         │
│  5. Platt scaling calibration                                 │
│  6. Evaluation: AUC-PR, KS, calibration, fairness            │
│  7. SHAP importance computation                               │
│  8. MLflow registration (Staging stage)                       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Model Promotion Pipeline                                     │
│                                                               │
│  Champion-challenger shadow mode (≥ 48h)                     │
│  Fairness audit (ECOA / Reg B — @james review)               │
│  @aisha PRR sign-off                                         │
│  MLflow stage: Staging → Production                           │
│  BentoML deployment: challenger → champion                    │
└───────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
                        ONLINE PATH
═══════════════════════════════════════════════════════════════════

Kafka (risk.decisions)
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Flink Real-Time Feature Pipeline                             │
│                                                               │
│  Velocity windows (ProcessingTime):                          │
│    txn_count_60s, txn_amount_1h                              │
│    txn_declined_24h, distinct_merchants_24h                  │
│                                                               │
│  Graph trigger (async Neo4j → Feast):                        │
│    device_account_count_7d                                   │
│    linked_fraud_ring_score                                   │
│    shared_device_accounts                                    │
│                                                               │
│  Output: Feast online store (Redis)                          │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Scoring API (FastAPI)                                        │
│                                                               │
│  1. Enrichment (IP geo, BIN, device fingerprint)             │
│  2. Feast online feature fetch (Redis sub-5ms)               │
│  3. Derived feature computation (inline)                     │
│  4. BentoML inference call                                   │
│  5. Score assembly + decision                                │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  BentoML Inference Server                                     │
│                                                               │
│  Runner 0: XGBoost fraud scorer    (champion / challenger)   │
│  Runner 1: LightGBM device risk    (champion)                │
│  Runner 2: PyTorch behavioral emb  (champion)                │
│                                                               │
│  Adaptive batching: max_batch=64, max_latency=1ms            │
│  Output: ensemble score 0–1000                               │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Model Monitoring (Evidently AI)                              │
│                                                               │
│  Input: risk.events (features_extracted events)              │
│  Checks: PSI per feature, score distribution drift           │
│  Output: Grafana alerts, retraining triggers                 │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Feast Feature Store

Feast is the contract between the offline training pipeline and the online serving pipeline. A feature defined in Feast is computed identically in both contexts — this eliminates training-serving skew by construction.

### 3.1 Feature Store Architecture

```
                    FEAST ARCHITECTURE
                    ══════════════════

 Training (offline):              Serving (online):
 ─────────────────────            ──────────────────────
 Snowflake                        Redis Cluster
 (feature tables)                 (feature vectors)
       ▲                                 ▲
       │                                 │
       │    ┌──────────────────┐         │
       └────┤  Feast Registry  ├─────────┘
            │  (PostgreSQL)    │
            │                  │
            │  Feature Views   │
            │  Entity defs     │
            │  Data sources    │
            └──────────────────┘
                    ▲
                    │
             Feature definitions
             (single source of truth)
                    │
       ┌────────────┴────────────┐
       │                         │
 PySpark batch             Flink real-time
 (offline store)           (online store)
```

### 3.2 Feature View Definitions

```python
# ml/features/customer_features.py

from feast import FeatureView, Entity, Field, FileSource
from feast.types import Float32, Int64, Bool, UnixTimestamp
from datetime import timedelta

# Entity definition — the join key
customer = Entity(
    name="customer",
    join_keys=["customer_id"],
    description="RAS customer entity",
)

# Batch feature view (computed by PySpark, served from Snowflake offline)
customer_history_fv = FeatureView(
    name="customer_history",
    entities=[customer],
    ttl=timedelta(days=1),          # Feast cache TTL — recompute daily
    schema=[
        Field(name="customer_avg_amount_30d",   dtype=Float32),
        Field(name="customer_age_days",          dtype=Int64),
        Field(name="txn_count_30d",              dtype=Int64),
        Field(name="chargeback_rate_90d",        dtype=Float32),
        Field(name="distinct_merchants_30d",     dtype=Int64),
    ],
    source=SnowflakeSource(
        database="RAS",
        schema="FEAST",
        table="customer_history_features",
        timestamp_field="feature_timestamp",
    ),
    online=True,    # Materialise to Redis for online serving
    tags={
        "owner": "yuki",
        "pii": "false",
        "batch_schedule": "0 */6 * * *",   # Every 6 hours
    },
)

# Real-time feature view (computed by Flink, served from Redis directly)
customer_velocity_fv = FeatureView(
    name="customer_velocity",
    entities=[customer],
    ttl=timedelta(hours=2),         # Velocity features expire after 2h inactivity
    schema=[
        Field(name="txn_count_60s",    dtype=Int64),
        Field(name="txn_amount_1h",    dtype=Float32),
        Field(name="txn_declined_24h", dtype=Int64),
    ],
    source=PushSource(              # Flink pushes directly to online store
        name="velocity_push_source",
        schema=[...],
    ),
    online=True,
    offline=False,                  # No offline store — computed only in real-time
    tags={
        "owner": "yuki",
        "computed_by": "flink",
    },
)
```

### 3.3 Point-in-Time Correct Feature Retrieval (Training)

```python
# ml/training/feature_retrieval.py

from feast import FeatureStore
import pandas as pd

store = FeatureStore(repo_path="ml/features/")

def retrieve_training_features(
    entity_df: pd.DataFrame,    # (customer_id, event_timestamp, label)
) -> pd.DataFrame:
    """
    Retrieve features with point-in-time correctness.

    For each row in entity_df, Feast retrieves feature values
    as they existed at event_timestamp — not today's values.

    This is the mechanism that prevents label leakage:
    - A transaction on 2023-06-15 gets features computed
      from data available on 2023-06-15 only.
    - Features computed after 2023-06-15 (e.g., chargeback
      that arrives 2023-07-01) are NOT included.
    """
    training_df = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "customer_history:customer_avg_amount_30d",
            "customer_history:customer_age_days",
            "customer_velocity:txn_count_60s",
            "merchant_features:merchant_fraud_rate_30d",
            "device_features:device_first_seen",
            "graph_features:linked_fraud_ring_score",
            # ... all 47 features
        ],
    ).to_df()

    return training_df
```

> *@yuki:* "Point-in-time correctness is the most important correctness guarantee in the feature store. Without it, you have temporal leakage — features from the future informing training decisions about the past. Feast's `get_historical_features` uses an as-of join that guarantees feature values are only from data available before `event_timestamp`. This is non-negotiable."

---

## 4. Offline Feature Pipeline (PySpark)

### 4.1 Pipeline Schedule

| Job | Schedule | Input | Output | SLA |
|---|---|---|---|---|
| `customer_history_features` | Every 6 hours | Snowflake transactions | Feast offline store | < 45 min |
| `merchant_features` | Every 6 hours | Snowflake transactions | Feast offline store | < 30 min |
| `graph_feature_snapshot` | Every 4 hours | Neo4j graph export | Feast offline store | < 60 min |
| `training_dataset_build` | Weekly (Sunday 02:00 UTC) | Feast offline store | S3 Parquet (training set) | < 4 hours |
| `label_backfill` | Daily (03:00 UTC) | Chargeback webhooks + analyst labels | Snowflake labels table | < 30 min |

### 4.2 Customer History Feature Job

```python
# ml/training/jobs/customer_history_features.py

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from feast import FeatureStore

def run_customer_history_features(
    spark: SparkSession,
    store: FeatureStore,
    as_of_timestamp: str,
) -> None:
    """
    Compute customer-level historical aggregation features.
    Writes to Feast offline store (Snowflake) for training
    and materialises to online store (Redis) for serving.
    """

    # Read transactions (Snowflake via Spark connector)
    txns = spark.read.format("snowflake").options(
        sfDatabase="RAS",
        sfSchema="RISK",
        sfTable="TRANSACTIONS",
    ).load().filter(
        F.col("occurred_at") <= as_of_timestamp
    )

    # 30-day lookback window per customer
    window_30d = Window.partitionBy("customer_id").orderBy(
        F.col("occurred_at").cast("long")
    ).rangeBetween(-30 * 86400, 0)

    features = txns.select(
        "customer_id",
        F.col("occurred_at").alias("feature_timestamp"),

        # Average transaction amount (30-day)
        F.avg("amount").over(window_30d).cast("float")
         .alias("customer_avg_amount_30d"),

        # Account age in days
        F.datediff(
            F.lit(as_of_timestamp),
            F.min("occurred_at").over(
                Window.partitionBy("customer_id")
            )
        ).alias("customer_age_days"),

        # Transaction count (30-day)
        F.count("*").over(window_30d).cast("long")
         .alias("txn_count_30d"),

        # Chargeback rate (90-day)
        F.avg(F.when(F.col("is_chargeback"), 1).otherwise(0))
         .over(
             Window.partitionBy("customer_id").orderBy(
                 F.col("occurred_at").cast("long")
             ).rangeBetween(-90 * 86400, 0)
         ).cast("float").alias("chargeback_rate_90d"),

    ).dropDuplicates(["customer_id", "feature_timestamp"])

    # Write to Feast offline store
    store.write_to_offline_store(
        feature_view_name="customer_history",
        df=features,
    )

    # Materialise to Redis online store
    store.materialize_incremental(
        end_date=pd.Timestamp(as_of_timestamp, tz="UTC"),
        feature_views=["customer_history"],
    )
```

### 4.3 Anti-Patterns Prevented by This Pipeline

| Anti-Pattern | How Feast Prevents It |
|---|---|
| Feature leakage from future data | `get_historical_features` as-of join — no future data |
| Training-serving skew | Single feature definition for both paths |
| Stale online features | `materialize_incremental` runs every 6 hours |
| Missing features at serving time | Feast raises `FeatureMissingException` — not silent null |
| Schema drift | Feast schema enforced at write time |

---

## 5. Real-Time Feature Pipeline (Flink)

### 5.1 Flink Job: Velocity Aggregation

```python
# ml/flink/velocity_aggregator.py
# Deployed as PyFlink job on Kubernetes

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common.time import Time

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(8)                       # 8 parallel operators
env.enable_checkpointing(30_000)             # 30s checkpoint interval
env.get_checkpoint_config().set_checkpointing_mode(
    CheckpointingMode.EXACTLY_ONCE
)

# Consume from Kafka risk.decisions
decisions_stream = env.from_source(
    source=KafkaSource.builder()
        .set_bootstrap_servers(os.environ["KAFKA_BROKERS"])
        .set_topics("risk.decisions")
        .set_group_id("ras-flink-velocity")
        .set_value_only_deserializer(RiskDecisionDeserializer())
        .build(),
    watermark_strategy=WatermarkStrategy
        .for_bounded_out_of_orderness(Duration.of_seconds(5))
        .with_timestamp_assigner(RiskDecisionTimestampAssigner()),
    source_name="risk.decisions",
)

# Key by customer_id, aggregate velocity windows
velocity_stream = (
    decisions_stream
    .key_by(lambda d: d.customer_id)
    .window(TumblingProcessingTimeWindows.of(Time.seconds(60)))
    .aggregate(
        VelocityAggregateFunction(),    # count + sum(amount)
        VelocityWindowProcessFunction() # emit (customer_id, txn_count_60s, txn_amount_60s)
    )
)

# Write to Feast online store (Redis via custom sink)
velocity_stream.add_sink(
    FeastOnlineStoreSink(
        feature_view="customer_velocity",
        redis_url=os.environ["FEAST_REDIS_URL"],
    )
)

env.execute("ras-velocity-aggregator")
```

### 5.2 Flink Job: Graph Feature Trigger

```python
# ml/flink/graph_feature_trigger.py

class GraphFeatureTriggerFunction(AsyncFunction):
    """
    Triggered on new customer_id seen in the decision stream.
    Asynchronously queries Neo4j for graph features and
    writes results to Feast online store.

    Timeout: 200ms (fail open — stale feature value retained)
    """

    async def async_invoke(
        self,
        decision: RiskDecision,
        result_future: ResultFuture,
    ) -> None:
        customer_id = decision.customer_id

        try:
            async with self.neo4j_driver.session() as session:
                graph_features = await asyncio.wait_for(
                    self._query_graph(session, customer_id),
                    timeout=0.200,    # 200ms timeout — fail open
                )
                await self.feast_client.write_online_features(
                    feature_view="graph_features",
                    entities=[{"customer_id": customer_id}],
                    features=graph_features,
                )
                result_future.complete([decision])

        except asyncio.TimeoutError:
            # Fail open — retain stale graph features in Feast
            # Score will proceed with potentially stale graph features
            # Degradation flag set on decision event
            log.warning(
                "graph_feature_timeout",
                customer_id=customer_id,
                timeout_ms=200,
            )
            result_future.complete([decision])

    async def _query_graph(
        self,
        session: AsyncSession,
        customer_id: str,
    ) -> dict:
        result = await session.run("""
            MATCH (c:Customer {id: $customer_id})
            OPTIONAL MATCH (c)-[:USED_DEVICE]->(d:Device)
                          <-[:USED_DEVICE]-(c2:Customer)
            OPTIONAL MATCH (c2)-[:FLAGGED_FRAUD]->()
            RETURN
                count(DISTINCT d) AS device_account_count_7d,
                count(DISTINCT c2) AS shared_device_accounts,
                CASE WHEN count(DISTINCT c2) > 0
                     THEN toFloat(count(DISTINCT c2[FLAGGED_FRAUD]))
                          / count(DISTINCT c2)
                     ELSE 0.0
                END AS linked_fraud_ring_score
        """, customer_id=customer_id)
        record = await result.single()
        return {
            "device_account_count_7d": record["device_account_count_7d"] or 0,
            "shared_device_accounts":  record["shared_device_accounts"] or 0,
            "linked_fraud_ring_score": record["linked_fraud_ring_score"] or 0.0,
        }
```

---

## 6. Model Training Pipeline

### 6.1 Training Workflow

```python
# ml/training/train_fraud_scorer.py

import mlflow
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
import shap

def train_fraud_scorer(
    training_df: pd.DataFrame,
    experiment_name: str = "xgb-fraud-scorer",
) -> str:
    """
    Full training pipeline. Returns MLflow run_id.

    Steps:
      1. Feature validation (no leakage, schema check)
      2. Train/val/test temporal split (NO shuffle)
      3. Stratified K-fold cross-validation
      4. XGBoost DART training (GPU)
      5. Platt calibration
      6. Evaluation: AUC-PR, KS, calibration, fairness
      7. SHAP importance computation
      8. MLflow artifact logging + model registration
    """

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run() as run:

        # Step 1: Validate no leakage features
        _validate_no_leakage(training_df)

        # Step 2: Temporal split (strict — no data from future in train)
        X_train, y_train, X_val, y_val, X_test, y_test = (
            _temporal_split(training_df)
        )

        mlflow.log_params({
            "train_size":        len(X_train),
            "val_size":          len(X_val),
            "test_size":         len(X_test),
            "fraud_rate_train":  y_train.mean(),
            "fraud_rate_test":   y_test.mean(),
            "n_features":        X_train.shape[1],
            "scale_pos_weight":  int((y_train == 0).sum() / (y_train == 1).sum()),
        })

        # Step 3: Cross-validation (stratified K-fold on train set)
        cv_scores = _stratified_kfold_cv(X_train, y_train, n_splits=5)
        mlflow.log_metrics({
            "cv_aucpr_mean": cv_scores["aucpr"].mean(),
            "cv_aucpr_std":  cv_scores["aucpr"].std(),
        })

        # Step 4: Final model training
        model = xgb.XGBClassifier(**MODEL_PARAMS)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=50,
            verbose=100,
        )

        # Step 5: Platt scaling calibration
        calibrated = CalibratedClassifierCV(
            model, method="sigmoid", cv="prefit"
        )
        calibrated.fit(X_val, y_val)

        # Step 6: Evaluation on held-out test set
        metrics = _evaluate(calibrated, X_test, y_test)
        mlflow.log_metrics(metrics)

        # Step 7: SHAP importance
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test[:10_000])
        feature_importance = pd.DataFrame({
            "feature": X_train.columns,
            "shap_mean_abs": np.abs(shap_values).mean(axis=0),
        }).sort_values("shap_mean_abs", ascending=False)

        mlflow.log_artifact(
            feature_importance.to_csv(index=False),
            "shap_importance.csv",
        )

        # Step 8: Register model
        mlflow.xgboost.log_model(
            xgb_model=calibrated,
            artifact_path="model",
            registered_model_name="xgb-fraud-scorer",
            signature=mlflow.models.infer_signature(X_test, y_test),
        )

        # Move to Staging (Production requires promotion gates)
        client = mlflow.MlflowClient()
        client.transition_model_version_stage(
            name="xgb-fraud-scorer",
            version=client.get_latest_versions(
                "xgb-fraud-scorer", stages=["None"]
            )[0].version,
            stage="Staging",
        )

        return run.info.run_id
```

### 6.2 Evaluation Suite

```python
# ml/training/evaluation.py

from sklearn.metrics import (
    average_precision_score, roc_auc_score, brier_score_loss,
    precision_recall_curve
)
from scipy.stats import ks_2samp

def _evaluate(
    model: CalibratedClassifierCV,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob > 0.6).astype(int)  # Decline threshold

    # Primary metrics
    aucpr = average_precision_score(y_test, y_prob)
    aucroc = roc_auc_score(y_test, y_prob)
    brier = brier_score_loss(y_test, y_prob)

    # KS Statistic — max separation between fraud/legit distributions
    fraud_scores = y_prob[y_test == 1]
    legit_scores  = y_prob[y_test == 0]
    ks_stat, _   = ks_2samp(fraud_scores, legit_scores)

    # Operating threshold metrics
    precision, recall, thresholds = precision_recall_curve(y_test, y_prob)

    # Calibration error
    from sklearn.calibration import calibration_curve
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_test, y_prob, n_bins=10
    )
    mce = np.max(np.abs(fraction_of_positives - mean_predicted_value))

    return {
        "test_aucpr":     aucpr,
        "test_aucroc":    aucroc,
        "test_ks_stat":   ks_stat,
        "test_brier":     brier,
        "test_mce":       mce,            # Max calibration error
        "test_precision_at_decline": precision[thresholds >= 0.6][0],
        "test_recall_at_decline":    recall[thresholds >= 0.6][0],
    }
```

---

## 7. BentoML Serving

### 7.1 Service Definition

```python
# ml/serving/fraud_scorer_service.py

import bentoml
from bentoml.io import NumpyNdarray, JSON
import numpy as np

# Load models from MLflow registry (Production stage)
xgb_runner   = bentoml.mlflow.get("xgb-fraud-scorer:latest").to_runner()
lgbm_runner  = bentoml.mlflow.get("device-risk-lgbm:latest").to_runner()
torch_runner = bentoml.mlflow.get("behavioral-embedding:latest").to_runner()

svc = bentoml.Service(
    name="ras-fraud-scorer",
    runners=[xgb_runner, lgbm_runner, torch_runner],
)

@svc.api(
    input=JSON(),
    output=JSON(),
    # Adaptive batching — batch requests within 1ms window, max 64
    batchable=True,
    batch_dim=0,
    max_batch_size=64,
    max_latency_ms=1,
)
async def score(features: dict) -> dict:
    feature_array = np.array([
        features.get(f, 0.0) for f in FEATURE_ORDER
    ]).reshape(1, -1)

    # Parallel inference across all three runners
    xgb_score, lgbm_score, torch_score = await asyncio.gather(
        xgb_runner.async_run(feature_array),
        lgbm_runner.async_run(feature_array),
        torch_runner.async_run(feature_array),
    )

    # Weighted ensemble
    ensemble_prob = (
        0.60 * float(xgb_score[0])   +
        0.25 * float(torch_score[0]) +
        0.15 * float(lgbm_score[0])
    )

    # Scale to 0–1000
    ensemble_score = int(round(ensemble_prob * 1000))

    # SHAP values for top-4 features (FCRA adverse action)
    shap_values = await xgb_runner.shap_async_run(feature_array)
    top4_shap = _top4_shap_features(shap_values, FEATURE_ORDER)

    return {
        "score":       ensemble_score,
        "xgb_score":   int(round(float(xgb_score[0]) * 1000)),
        "lgbm_score":  int(round(float(lgbm_score[0]) * 1000)),
        "torch_score": int(round(float(torch_score[0]) * 1000)),
        "top4_shap":   top4_shap,
        "model_version": MODEL_VERSION,
    }

@svc.on_startup
async def warmup(ctx):
    """
    ISS-001 resolution: pre-warm model before accepting traffic.
    Readiness probe does not pass until warmup completes.
    """
    synthetic_features = _generate_synthetic_features(n=1_000)
    for batch in _batches(synthetic_features, size=64):
        await score(batch)
    log.info("bentoml_warmup_complete", n_inferences=1_000)
```

### 7.2 Champion-Challenger Traffic Split

```python
# ml/serving/ab_runner.py

class ChampionChallengerRunner:
    """
    Routes inference requests between champion and challenger
    based on a configurable traffic split.

    Default: 100% champion.
    Shadow mode: 100% champion inference + async challenger inference
                 (challenger result not returned to client).
    A/B mode:   Split% challenger, (100-Split)% champion.
    """

    def __init__(
        self,
        champion: bentoml.Runner,
        challenger: bentoml.Runner | None = None,
        challenger_pct: float = 0.0,      # 0.0 = shadow mode
        shadow_mode: bool = True,
    ):
        self.champion      = champion
        self.challenger    = challenger
        self.challenger_pct = challenger_pct
        self.shadow_mode   = shadow_mode

    async def async_run(self, features: np.ndarray) -> np.ndarray:
        champion_result = await self.champion.async_run(features)

        if self.challenger and self.shadow_mode:
            # Shadow: run challenger async, don't return result
            asyncio.create_task(
                self._shadow_challenger(features, champion_result)
            )
        elif self.challenger and random.random() < self.challenger_pct:
            # A/B: return challenger result for this request
            return await self.challenger.async_run(features)

        return champion_result

    async def _shadow_challenger(
        self,
        features: np.ndarray,
        champion_result: np.ndarray,
    ) -> None:
        challenger_result = await self.challenger.async_run(features)
        # Publish shadow comparison to Kafka model.feedback topic
        await self.kafka_producer.send(
            "model.feedback",
            value={
                "type": "shadow_comparison",
                "champion_score": float(champion_result[0]),
                "challenger_score": float(challenger_result[0]),
                "delta": float(challenger_result[0] - champion_result[0]),
            },
        )
```

---

## 8. Model Monitoring (Evidently AI)

### 8.1 Monitoring Configuration

```python
# ml/monitoring/evidently_monitor.py

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, ModelPerformancePreset
from evidently.metrics import (
    DatasetDriftMetric,
    ColumnDriftMetric,
    ClassificationQualityMetric,
)

def build_monitoring_report(
    reference_df: pd.DataFrame,    # Training feature distribution
    current_df: pd.DataFrame,      # Last 24h production features
) -> Report:

    report = Report(metrics=[
        # Dataset-level drift (PSI across all features)
        DatasetDriftMetric(
            stattest="psi",
            stattest_threshold=0.20,     # Alert threshold per ADR-006
        ),

        # Per-feature drift for top-10 by SHAP importance
        *[
            ColumnDriftMetric(
                column_name=feature,
                stattest="psi",
                stattest_threshold=0.20,
            )
            for feature in TOP_10_FEATURES_BY_SHAP
        ],

        # Score distribution drift
        ColumnDriftMetric(
            column_name="model_score",
            stattest="wasserstein",
            stattest_threshold=20.0,   # 20-point Wasserstein distance
        ),
    ])

    report.run(
        reference_data=reference_df,
        current_data=current_df,
    )
    return report
```

### 8.2 Monitoring Alerts

| Alert | Condition | Action | Owner |
|---|---|---|---|
| Feature PSI breach | Any top-10 feature PSI > 0.20 | PagerDuty P2 + Slack | `@yuki` |
| Score distribution shift | Wasserstein > 20 over 24h | PagerDuty P2 | `@yuki` |
| False positive rate | > 7.5% over 7 days | PagerDuty P2 + retraining trigger | `@yuki` |
| Model calibration error | MCE > 0.05 | PagerDuty P2 | `@yuki` |
| Shadow challenger divergence | Mean delta > 50 score points | Slack notification | `@yuki` |
| Inference latency | P95 > 35ms | PagerDuty P2 | `@darius` + `@yuki` |

---

## 9. Model Registry & Lifecycle

### 9.1 MLflow Model Stages

```
None (freshly trained)
  │
  ▼ (automated — training pipeline)
Staging
  │
  ▼ (after shadow mode ≥ 48h + promotion gates)
Production  ←── Champion
  │
  ▼ (when superseded by new champion)
Archived    ←── Retained 2 years (SR 11-7)
```

### 9.2 Promotion Gate Automation

```python
# ml/training/promote.py

async def evaluate_promotion_gates(
    challenger_run_id: str,
    champion_model_name: str,
) -> PromotionDecision:

    client = mlflow.MlflowClient()
    challenger = client.get_run(challenger_run_id)
    champion = client.get_latest_versions(
        champion_model_name, stages=["Production"]
    )[0]

    champion_metrics = client.get_run(champion.run_id).data.metrics
    challenger_metrics = challenger.data.metrics

    gates = {
        # Gate 1: AUC-PR improvement
        "aucpr_improvement": (
            challenger_metrics["test_aucpr"]
            >= champion_metrics["test_aucpr"]
        ),
        # Gate 2: Shadow mode duration
        "shadow_duration_met": await _check_shadow_duration(
            challenger_run_id, min_hours=48
        ),
        # Gate 3: Fairness — no group DIR < 0.80
        "fairness_passed": await _check_fairness_audit(
            challenger_run_id
        ),
        # Gate 4: @james SHAP review (manual — checked via Jira ticket)
        "james_shap_review": await _check_jira_gate(
            f"SHAP-REVIEW-{challenger_run_id[:8]}"
        ),
        # Gate 5: @aisha PRR sign-off (checked via PRR checklist status)
        "aisha_ppr_signoff": await _check_prr_gate(
            challenger_run_id
        ),
    }

    all_passed = all(gates.values())

    return PromotionDecision(
        challenger_run_id=challenger_run_id,
        gates=gates,
        decision="promote" if all_passed else "hold",
        reason=None if all_passed else [
            k for k, v in gates.items() if not v
        ],
    )
```

---

## 10. Data Quality & Validation

```python
# ml/training/data_validation.py

import great_expectations as ge

def validate_training_dataset(df: pd.DataFrame) -> ValidationResult:
    """
    Great Expectations suite run before every training job.
    Fails fast on data quality issues.
    """
    dataset = ge.from_pandas(df)

    # Schema validation
    dataset.expect_column_to_exist("customer_id")
    dataset.expect_column_to_exist("label")
    dataset.expect_column_values_to_be_in_set("label", [0, 1])

    # Fraud rate sanity check (0.05% – 1.0% expected)
    dataset.expect_column_mean_to_be_between("label", 0.0005, 0.01)

    # No future features (leakage check)
    dataset.expect_column_values_to_be_null("chargeback_flag")
    dataset.expect_column_values_to_be_null("dispute_status")

    # Feature completeness
    for feature in REQUIRED_FEATURES:
        dataset.expect_column_values_to_not_be_null(
            feature, mostly=0.95   # Allow 5% missing
        )

    # Amount sanity (no negative amounts)
    dataset.expect_column_values_to_be_between(
        "amount_cents", min_value=0, max_value=100_000_00
    )

    return dataset.validate()
```

---

## 11. Related Documents

| Document | Location | Owner |
|---|---|---|
| Model Card (XGBoost Fraud Scorer) | `docs/ml/model_card.md` | `@yuki` |
| Feature Catalog | `docs/ml/feature_catalog.md` | `@yuki` |
| Fairness Audit Report | `docs/ml/fairness_audit.md` | `@yuki` / `@james` |
| Kafka Topic Design | `docs/architecture/kafka_topics.md` | `@marcus` |
| System Architecture Overview | `docs/architecture/system_overview.md` | `@marcus` |
| Feast Feature Definitions | `ml/features/` | `@yuki` |
| BentoML Service Definition | `ml/serving/fraud_scorer_service.py` | `@yuki` |
| PRR Model Gates | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owner: Dr. Yuki Tanaka — Lead ML / Risk Scientist*
*Review Cycle: Per model promotion · Quarterly scheduled*
*Classification: Internal — Confidential — Model Governance*