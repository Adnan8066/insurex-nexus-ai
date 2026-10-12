import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

class DataPreprocessor:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = []

    def load_data(self, filepath):
        """Load insurance claims CSV"""
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} records from {filepath}")
        print(f"Columns: {list(df.columns)}")
        return df

    def handle_missing_values(self, df):
        """Handle missing values in the dataset"""
        # Numeric columns - fill with median
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().sum() > 0:
                df[col].fillna(df[col].median(), inplace=True)

        # Categorical columns - fill with mode
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df[col].isnull().sum() > 0:
                df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown', inplace=True)

        return df

    def encode_categorical(self, df, columns):
        """Encode categorical variables using LabelEncoder"""
        for col in columns:
            if col in df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                df[col] = self.label_encoders[col].fit_transform(df[col].astype(str))
        return df

    def feature_engineering(self, df):
        """Create new features"""
        # Claim ratio features
        if 'total_claim_amount' in df.columns and 'vehicle_claim' in df.columns:
            df['vehicle_claim_ratio'] = df['vehicle_claim'] / df['total_claim_amount'].replace(0, 1)
        if 'total_claim_amount' in df.columns and 'injury_claim' in df.columns:
            df['injury_claim_ratio'] = df['injury_claim'] / df['total_claim_amount'].replace(0, 1)
        if 'total_claim_amount' in df.columns and 'property_claim' in df.columns:
            df['property_claim_ratio'] = df['property_claim'] / df['total_claim_amount'].replace(0, 1)

        # Incident severity encoding
        if 'incident_severity' in df.columns:
            severity_map = {'Minor Damage': 1, 'Medium Damage': 2, 'Major Damage': 3, 'Total Loss': 4}
            df['incident_severity_encoded'] = df['incident_severity'].map(severity_map).fillna(2)

        # Policy deductible
        if 'policy_deductable' in df.columns:
            df['policy_deductable'] = pd.to_numeric(df['policy_deductable'], errors='coerce')

        # Auto year
        if 'auto_year' in df.columns:
            df['auto_year'] = pd.to_numeric(df['auto_year'], errors='coerce')
            df['auto_age'] = 2024 - df['auto_year']

        return df

    def prepare_features(self, df, target_column=None):
        """Prepare features for ML models"""
        # Handle missing values
        df = self.handle_missing_values(df)

        # Feature engineering
        df = self.feature_engineering(df)

        # Categorical columns to encode
        categorical_cols = ['policy_state', 'policy_csl', 'insured_sex',
                           'insured_education_level', 'insured_occupation',
                           'insured_hobbies', 'insured_relationship',
                           'incident_type', 'collision_type', 'incident_severity',
                           'authorities_contacted', 'incident_state', 'incident_city',
                           'property_damage', 'bodily_injuries', 'witnesses',
                           'police_report_available', 'fraud_reported']

        # Filter to existing columns
        categorical_cols = [c for c in categorical_cols if c in df.columns]

        # Encode categoricals
        df = self.encode_categorical(df, categorical_cols)

        # Select feature columns (exclude target and ID columns)
        exclude_cols = [target_column] if target_column else []
        exclude_cols += ['policy_number', 'policy_bind_date', 'incident_date',
                        'insured_zip', 'incident_location', 'incident_hour_of_the_day',
                        '_c39']

        self.feature_columns = [c for c in df.columns if c not in exclude_cols
                               and c in df.select_dtypes(include=[np.number]).columns]

        return df

    def get_train_test_split(self, df, target_column, test_size=0.2, random_state=42):
        """Split data into train and test sets"""
        X = df[self.feature_columns]
        y = df[target_column]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        # Scale features
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)

        return X_train, X_test, y_train, y_test

    def save_preprocessor(self, filepath):
        """Save label encoders and scaler"""
        import jobobs
        jobobs.dump({'label_encoders': self.label_encoders, 'scaler': self.scaler,
                     'feature_columns': self.feature_columns}, filepath)
        print(f"Preprocessor saved to {filepath}")

    def load_preprocessor(self, filepath):
        """Load label encoders and scaler"""
        import jobobs
        data = jobobs.load(filepath)
        self.label_encoders = data['label_encoders']
        self.scaler = data['scaler']
        self.feature_columns = data['feature_columns']
        print(f"Preprocessor loaded from {filepath}")

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    df = preprocessor.load_data("insurance_claims.csv")
    print(f"\nDataset shape: {df.shape}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    print(f"\nTarget distribution (fraud_reported):")
    print(df['fraud_reported'].value_counts())