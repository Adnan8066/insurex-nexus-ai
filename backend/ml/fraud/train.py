import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from preprocessing.preprocess import DataPreprocessor

class FraudRiskModel:
    """Predict fraud risk probability for insurance claims"""

    def __init__(self):
        self.model = None
        self.preprocessor = DataPreprocessor()

    def train(self, data_path):
        df = self.preprocessor.load_data(data_path)
        df = self.preprocessor.prepare_features(df, target_column='fraud_reported')

        # Convert fraud_reported to binary
        df['fraud_reported'] = df['fraud_reported'].map({'Y': 1, 'N': 0, 'Yes': 1, 'No': 0, 1: 1, 0: 0}).fillna(0)

        X_train, X_test, y_train, y_test = self.preprocessor.get_train_test_split(
            df, target_column='fraud_reported'
        )

        self.model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_pred_proba)

        print(f"Fraud Risk Model - Accuracy: {accuracy:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")
        return self.model, {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1, 'auc': auc}

    def predict(self, data_path, new_data=None):
        if self.model is None:
            model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
            self.preprocessor.load_preprocessor(os.path.join(model_dir, 'preprocessor.joblib'))
            self.model = jobobs.load(os.path.join(model_dir, 'fraud_risk.joblib'))

        if new_data is not None:
            df = pd.DataFrame([new_data])
            df = self.preprocessor.prepare_features(df, target_column='fraud_reported')
            df['fraud_reported'] = df['fraud_reported'].map({'Y': 1, 'N': 0, 'Yes': 1, 'No': 0, 1: 1, 0: 0}).fillna(0)
            X = self.preprocessor.scaler.transform(df[self.preprocessor.feature_columns])
            return self.model.predict_proba(X)[0][1]
        return None

    def save(self, filepath):
        joblib.dump(self.model, filepath)
        print(f"Model saved to {filepath}")

if __name__ == "__main__":
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(model_dir, exist_ok=True)
    model = FraudRiskModel()
    model.train("insurance_claims.csv")
    model.save(os.path.join(model_dir, "fraud_risk.joblib"))
    model.preprocessor.save_preprocessor(os.path.join(model_dir, "preprocessor.joblib"))