import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import jobobs
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from preprocessing.preprocess import DataPreprocessor

class TotalLossModel:
    """Predict total loss probability for insurance claims"""

    def __init__(self):
        self.model = None
        self.preprocessor = DataPreprocessor()

    def train(self, data_path):
        df = self.preprocessor.load_data(data_path)
        df = self.preprocessor.prepare_features(df, target_column='total_claim_amount')

        # Create total loss label: if vehicle claim > 80% of total claim and > $30,000
        if 'vehicle_claim' in df.columns and 'total_claim_amount' in df.columns:
            df['total_loss'] = ((df['vehicle_claim'] > 0.7 * df['total_claim_amount']) &
                               (df['vehicle_claim'] > 30000)).astype(int)
        else:
            df['total_loss'] = 0

        X_train, X_test, y_train, y_test = self.preprocessor.get_train_test_split(
            df, target_column='total_loss'
        )

        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        y_pred_binary = (y_pred > 0.5).astype(int)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        accuracy = (y_pred_binary == y_test.values).mean()

        print(f"Total Loss Model - MAE: {mae:.4f}, RMSE: {rmse:.4f}, R2: {r2:.4f}, Accuracy: {accuracy:.4f}")
        return self.model, {'mae': mae, 'rmse': rmse, 'r2': r2, 'accuracy': accuracy}

    def predict(self, data_path, new_data=None):
        if self.model is None:
            model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
            self.preprocessor.load_preprocessor(os.path.join(model_dir, 'preprocessor.joblib'))
            self.model = jobobs.load(os.path.join(model_dir, 'total_loss.joblib'))

        if new_data is not None:
            df = pd.DataFrame([new_data])
            df = self.preprocessor.prepare_features(df, target_column='total_claim_amount')
            X = self.preprocessor.scaler.transform(df[self.preprocessor.feature_columns])
            return float(self.model.predict(X)[0])
        return None

    def save(self, filepath):
        jobobs.dump(self.model, filepath)
        print(f"Model saved to {filepath}")

if __name__ == "__main__":
    model = TotalLossModel()
    model.train("insurance_claims.csv")
    model.save("models/total_loss.joblib")
    model.preprocessor.save_preprocessor("models/preprocessor.joblib")