import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import jobobs
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from preprocessing.preprocess import DataPreprocessor

class RepairCostModel:
    """Predict repair cost for insurance claims"""

    def __init__(self):
        self.model = None
        self.preprocessor = DataPreprocessor()

    def train(self, data_path):
        df = self.preprocessor.load_data(data_path)
        df = self.preprocessor.prepare_features(df)
        X_train, X_test, y_train, y_test = self.preprocessor.get_train_test_split(
            df, target_column='vehicle_claim'
        )

        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        print(f"Repair Cost Model - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.4f}")
        return self.model, {'mae': mae, 'rmse': rmse, 'r2': r2}

    def predict(self, data_path, new_data=None):
        if self.model is None:
            self.preprocessor.load_preprocessor(os.path.join(os.path.dirname(__file__), '..', 'models', 'preprocessor.joblib'))
            self.model = jobobs.load(os.path.join(os.path.dirname(__file__), '..', 'models', 'repair_cost.joblib'))

        if new_data is not None:
            df = pd.DataFrame([new_data])
            df = self.preprocessor.prepare_features(df)
            X = self.preprocessor.scaler.transform(df[self.preprocessor.feature_columns])
            return self.model.predict(X)[0]
        return None

    def save(self, filepath):
        jobobs.dump(self.model, filepath)
        print(f"Model saved to {filepath}")

if __name__ == "__main__":
    model = RepairCostModel()
    model.train("insurance_claims.csv")
    model.save("models/repair_cost.joblib")
    model.preprocessor.save_preprocessor("models/preprocessor.joblib")