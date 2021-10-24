import argparse
import os
import tempfile

import joblib
import numpy as np
import pandas as pd
from feast import FeatureStore, RepoConfig
from feast.infra.offline_stores.bigquery import BigQueryOfflineStoreConfig
from google.cloud import bigquery
from polyaxon import tracking
from polyaxon.tracking import Run
# from polyaxon.tracking.contrib.scikit import log_classifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score


def load_data():
    client = bigquery.Client()
    query = "SELECT CustomerID FROM loyal-copilot-329917.churn.cust_demo_info"
    df_entity = client.query(query).to_dataframe()
    df_entity["event_timestamp"] = pd.Timestamp("2021-07-31", tz="UTC")

    fs = FeatureStore(
        config=RepoConfig(
            registry="gs://mlbook/feature_store/registry.db",
            project="churn",
            provider="gcp",
            offline_store=BigQueryOfflineStoreConfig(type="bigquery", dataset="churn"),
        )
    )

    features = [
        "cust_conn_details:Tenure",
        "cust_conn_details:PhoneService",
        "cust_conn_details:MultipleLines",
        "cust_conn_details:InternetService",
        "cust_conn_details:OnlineSecurity",
        "cust_conn_details:OnlineBackup",
        "cust_conn_details:DeviceProtection",
        "cust_conn_details:TechSupport",
        "cust_conn_details:StreamingTV",
        "cust_conn_details:StreamingMovies",
        "cust_pay_det:Contract",
        "cust_pay_det:PaperlessBilling",
        "cust_pay_det:PaymentMethod",
        "cust_pay_det:MonthlyCharges",
        "cust_pay_det:TotalCharges",
        "cust_churn_det:Churn",
    ]

    training_df = fs.get_historical_features(features=features, entity_df=df_entity).to_df()

    X = training_df.drop(columns="Churn")
    y = training_df["Churn"]

    return X, y


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--n_estimators", type=int, default=50)
    parser.add_argument("--max_depth", type=int, default=3)

    args = parser.parse_args()

    # Polyaxon
    experiment = Run()

    (X, y) = load_data()

    experiment.log_data_ref(content=X, name="dataset_X")
    experiment.log_data_ref(content=y, name="dataset_y")

    classifier = RandomForestClassifier(n_estimators=args.n_estimators, max_depth=args.max_depth)

    accuracies = cross_val_score(classifier, X, y, cv=5)
    accuracy_mean, accuracy_std = (np.mean(accuracies), np.std(accuracies))
    print("Accuracy: {} +/- {}".format(accuracy_mean, accuracy_std))

    classifier.fit(X, y)

    # Polyaxon
    experiment.log_metrics(accuracy_mean=accuracy_mean, accuracy_std=accuracy_std)

    with tempfile.TemporaryDirectory() as d:
        model_path = os.path.join(d, "model.joblib")
        joblib.dump(classifier, model_path)
        tracking.log_model(model_path, name="model", framework="scikit-learn", versioned=False)


if __name__ == "__main__":
    main()
