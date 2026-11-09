"""Train the Indian vehicle-claim fraud model from this app's own investigated claims.

Labels come from Claim.fraud_outcome (fraud / genuine); claims marked unclear are skipped.
Features are the claim, policy and vehicle details known at filing time plus checks on the
claim photos (see apps.assessments.vehicle_fraud).

    python manage.py train_vehicle_fraud_model
    python manage.py train_vehicle_fraud_model --min-claims 100 --models-dir ../ml/models
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from apps.assessments import vehicle_fraud as vf
from apps.claims.models import Claim

MIN_RECALL = 0.75


def build_model(rows):
    preprocessing = ColumnTransformer([
        ('numeric', SimpleImputer(strategy='median', keep_empty_features=True), vf.NUMERIC),
        ('categorical', Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='unknown')),
            ('one_hot', OneHotEncoder(handle_unknown='infrequent_if_exist', min_frequency=3, sparse_output=False)),
        ]), vf.CATEGORICAL),
    ])
    estimator = LGBMClassifier(
        n_estimators=300, learning_rate=0.03, num_leaves=7,
        min_child_samples=max(3, min(20, rows // 20)), subsample=0.8, subsample_freq=1,
        colsample_bytree=0.8, reg_lambda=1.0, class_weight='balanced',
        random_state=42, verbosity=-1, n_jobs=1,
    )
    return Pipeline([('preprocessing', preprocessing), ('estimator', estimator)])


def metrics_at(target, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predictions, labels=[0, 1]).ravel()
    return {
        'threshold': round(float(threshold), 4),
        'precision': round(float(precision_score(target, predictions, zero_division=0)), 4),
        'recall': round(float(recall_score(target, predictions, zero_division=0)), 4),
        'f1': round(float(f1_score(target, predictions, zero_division=0)), 4),
        'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
    }


def choose_threshold(target, probabilities):
    """Most precise threshold that still catches MIN_RECALL of known fraud, from out-of-fold scores."""
    candidates = [metrics_at(target, probabilities, t) for t in np.round(np.arange(0.05, 0.96, 0.01), 2)]
    eligible = [row for row in candidates if row['recall'] >= MIN_RECALL]
    if not eligible:
        return max(candidates, key=lambda row: row['f1'])
    return max(eligible, key=lambda row: (row['precision'], row['threshold']))


def baselines(frame):
    typical = {}
    for column in frame.columns:
        values = frame[column].dropna()
        if values.empty:
            continue
        if column in vf.NUMERIC:
            typical[column] = float(pd.to_numeric(values, errors='coerce').median())
        else:
            typical[column] = str(values.astype(str).mode().iloc[0])
    return typical


class Command(BaseCommand):
    help = 'Train the vehicle fraud model on claims whose fraud outcome has been recorded.'

    def add_arguments(self, parser):
        parser.add_argument('--models-dir', type=Path, default=None)
        parser.add_argument('--dataset', type=Path, default=None,
                            help='Train from a CSV in feature layout (with fraud_outcome) instead of the database.')
        parser.add_argument('--min-claims', type=int, default=40,
                            help='Refuse to train with fewer labelled claims than this (default 40).')
        parser.add_argument('--min-per-class', type=int, default=8,
                            help='Refuse to train with fewer fraud or genuine claims than this (default 8).')

    def handle(self, *args, **options):
        if options['dataset']:
            features, target = self.features_from_csv(options['dataset'])
        else:
            features, target = self.features_from_claims(options)
        self.train(features, target, options)

    def features_from_csv(self, path):
        """Rows already in feature layout (e.g. data/india/india_vehicle_fraud.csv) with a fraud_outcome column."""
        if not path.is_file():
            raise CommandError(f'Dataset not found: {path}')
        frame = pd.read_csv(path)
        missing = [name for name in vf.FEATURES + ['fraud_outcome'] if name not in frame.columns]
        if missing:
            raise CommandError(f"Dataset is missing columns: {', '.join(missing)}")
        frame = frame[frame['fraud_outcome'].isin(list(vf.LABELS))]
        target = frame['fraud_outcome'].map(vf.LABELS).astype(int).reset_index(drop=True)
        self.stdout.write(f'Labelled rows from {path.name}: {len(target)} ({int(target.sum())} fraud)')
        return vf.feature_frame(frame.to_dict('records')), target

    def features_from_claims(self, options):
        claims = list(
            Claim.objects.filter(fraud_outcome__in=list(vf.LABELS))
            .select_related('vehicle', 'policy').prefetch_related('documents')
            .order_by('incident_date', 'pk')
        )
        target = pd.Series([vf.LABELS[claim.fraud_outcome] for claim in claims], dtype=int)
        fraud, genuine = int(target.sum()), int((target == 0).sum())
        self.stdout.write(f'Labelled claims: {len(claims)} ({fraud} fraud, {genuine} genuine)')
        if len(claims) < options['min_claims'] or min(fraud, genuine) < options['min_per_class']:
            raise CommandError(
                f"Not enough investigated claims to train: need at least {options['min_claims']} "
                f"with {options['min_per_class']} fraud and {options['min_per_class']} genuine. "
                'Record outcomes on closed claims (Claim details > Fraud outcome) and run this again.'
            )

        self.stdout.write('Reading claim photos...')
        hashes_by_claim = {}
        for claim in claims:
            hashes_by_claim[claim.pk] = [
                info['hash'] for info in (vf.read_photo(path) for path in vf._claim_photo_paths(claim)) if info
            ]
        rows = []
        for claim in claims:
            others = [h for pk, hashes in hashes_by_claim.items() if pk != claim.pk for h in hashes]
            rows.append(vf.claim_features(claim, other_hashes=others))
        return vf.feature_frame(rows), target

    def train(self, features, target, options):
        fraud, genuine = int(target.sum()), int((target == 0).sum())
        folds = max(2, min(5, fraud, genuine))
        splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        out_of_fold = cross_val_predict(build_model(len(target)), features, target, cv=splitter, method='predict_proba')[:, 1]
        selected = choose_threshold(target, out_of_fold)
        evaluation = {
            'cross_validation_folds': folds,
            'roc_auc': round(float(roc_auc_score(target, out_of_fold)), 4),
            'pr_auc': round(float(average_precision_score(target, out_of_fold)), 4),
            'pr_auc_baseline': round(float(target.mean()), 4),
            'at_selected_threshold': selected,
        }

        model = build_model(len(target))
        model.fit(features, target)
        trained_at = datetime.now(timezone.utc).isoformat()
        report = {
            'model': 'vehicle_fraud',
            'trained_at': trained_at,
            'training_source': str(options['dataset']) if options['dataset'] else 'database: Claim.fraud_outcome',
            'labelled_claims': len(target),
            'fraud_claims': fraud,
            'genuine_claims': genuine,
            'claims_with_photos': int((features['photo_count'] > 0).sum()),
            'label': 'Claim.fraud_outcome: fraud = 1, genuine = 0 (unclear excluded)',
            'threshold_rule': f'highest precision with out-of-fold recall >= {MIN_RECALL}',
            'features': vf.FEATURES,
            'metrics': evaluation,
        }
        bundle = {
            'model': model,
            'threshold': selected['threshold'],
            'features': vf.FEATURES,
            'baselines': baselines(features),
            'trained_at': trained_at,
        }

        models_dir = options['models_dir'] or vf.models_dir()
        models_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='vehicle-fraud-', dir=models_dir) as temp_dir:
            staged_model = Path(temp_dir) / vf.MODEL_FILENAME
            staged_report = Path(temp_dir) / vf.REPORT_FILENAME
            joblib.dump(bundle, staged_model)
            staged_report.write_text(json.dumps(report, indent=2, default=vf.json_default) + '\n', encoding='utf-8')
            os.replace(staged_model, models_dir / vf.MODEL_FILENAME)
            os.replace(staged_report, models_dir / vf.REPORT_FILENAME)

        self.stdout.write(
            f"Cross-validated ROC-AUC {evaluation['roc_auc']}, PR-AUC {evaluation['pr_auc']} "
            f"(random = {evaluation['pr_auc_baseline']})"
        )
        self.stdout.write(
            f"At threshold {selected['threshold']}: recall {selected['recall']}, precision {selected['precision']}, "
            f"confusion {json.dumps(selected['confusion_matrix'])}"
        )
        self.stdout.write(self.style.SUCCESS(f'Saved {vf.MODEL_FILENAME} and {vf.REPORT_FILENAME} to {models_dir}'))
