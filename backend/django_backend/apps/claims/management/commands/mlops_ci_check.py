"""Validate training data and trained model artifacts for the Jenkins MLOps CI pipeline."""
import hashlib
import json
import math
import platform
import subprocess
from datetime import datetime, timezone

import pandas as pd
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.assessments import vehicle_fraud
from apps.claims.management.commands.train_project_models import (
    INSURANCE_FEATURES,
    ORACLE_FEATURES,
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


class Command(BaseCommand):
    help = 'Run dataset validation or trained-model quality gates for MLOps CI.'

    def add_arguments(self, parser):
        parser.add_argument('--phase', choices=('data', 'quality', 'drift', 'explainability'), required=True)

    def handle(self, *args, **options):
        backend_dir = settings.BASE_DIR.parent
        datasets_dir = backend_dir / 'data' / 'india'
        models_dir = backend_dir / 'ml' / 'models'
        if options['phase'] == 'data':
            self.validate_data(datasets_dir, models_dir)
        elif options['phase'] == 'quality':
            self.validate_quality(backend_dir, models_dir)
        elif options['phase'] == 'drift':
            self.validate_drift(datasets_dir, models_dir)
        else:
            self.validate_explainability(models_dir)

    def validate_drift(self, datasets_dir, models_dir):
        """Check for large distribution shifts between deterministic dataset partitions.

        This is a CI proxy for drift until a separately collected production/incoming
        dataset is configured. It catches ordering or source changes within bundled data.
        """
        datasets = ('india_insurance_claims.csv', 'india_fraud_oracle.csv', 'india_vehicle_fraud.csv')
        report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'method': 'first-half vs second-half PSI/TV', 'datasets': {}, 'passed': True, 'errors': []}
        for filename in datasets:
            frame = pd.read_csv(datasets_dir / filename, encoding='utf-8-sig')
            if len(frame) < 20:
                report['errors'].append(f'{filename}: at least 20 rows are required for drift checks.')
                continue
            split = len(frame) // 2
            reference, current = frame.iloc[:split], frame.iloc[split:]
            numeric = frame.select_dtypes(include=[np.number]).columns
            feature_results = {}
            for column in frame.columns:
                a, b = reference[column].dropna(), current[column].dropna()
                if a.empty or b.empty:
                    continue
                if column in numeric:
                    edges = np.unique(np.quantile(a.astype(float), np.linspace(0, 1, 11)))
                    if len(edges) < 2:
                        continue
                    edges[0], edges[-1] = -np.inf, np.inf
                    pa = np.histogram(a.astype(float), bins=edges)[0].astype(float)
                    pb = np.histogram(b.astype(float), bins=edges)[0].astype(float)
                    pa = np.clip(pa / pa.sum(), 1e-6, None)
                    pb = np.clip(pb / pb.sum(), 1e-6, None)
                    score = float(np.sum((pb - pa) * np.log(pb / pa)))
                    metric = 'psi'
                else:
                    av, bv = a.astype(str).value_counts(normalize=True), b.astype(str).value_counts(normalize=True)
                    categories = set(av.index) | set(bv.index)
                    score = float(0.5 * sum(abs(av.get(k, 0) - bv.get(k, 0)) for k in categories))
                    metric = 'total_variation'
                feature_results[column] = {'metric': metric, 'score': round(score, 6)}
            report['datasets'][filename] = {
                'reference_rows': len(reference), 'comparison_rows': len(current),
                'features': feature_results,
                'large_shift_features': [name for name, item in feature_results.items()
                                         if item['metric'] == 'psi' and item['score'] > 0.5
                                         or item['metric'] == 'total_variation' and item['score'] > 0.5],
            }
        report['passed'] = not report['errors']
        write_json(models_dir / 'data_drift_report.json', report)
        if report['errors']:
            raise CommandError('Data drift check failed:\n- ' + '\n- '.join(report['errors']))
        self.stdout.write(self.style.SUCCESS('Dataset partition drift report created (PSI/total variation).'))

    def validate_explainability(self, models_dir):
        """Publish top global feature contributions from the trained vehicle fraud model."""
        model_path = models_dir / 'vehicle_fraud.joblib'
        if not model_path.is_file():
            raise CommandError(f'Missing model for explainability report: {model_path.name}')
        import joblib
        artifact = joblib.load(model_path)
        model = artifact.get('model') if isinstance(artifact, dict) else artifact
        if model is None:
            raise CommandError('Vehicle fraud model bundle is missing its model pipeline.')
        estimator = model.named_steps.get('estimator')
        preprocessing = model.named_steps.get('preprocessing')
        importances = getattr(estimator, 'feature_importances_', None)
        if importances is None or preprocessing is None:
            raise CommandError('Vehicle fraud model does not expose feature importances.')
        names = preprocessing.get_feature_names_out()
        if len(names) != len(importances) or not np.isfinite(importances).all() or float(np.sum(importances)) <= 0:
            raise CommandError('Vehicle fraud feature importance values are invalid.')
        top = sorted(zip(names, importances), key=lambda pair: float(pair[1]), reverse=True)[:30]
        report = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'model': model_path.name,
            'method': 'LightGBM split gain importance; global, not a per-claim causal explanation',
            'top_features': [{'feature': str(name), 'importance': round(float(value), 8)} for name, value in top],
        }
        write_json(models_dir / 'vehicle_fraud_explainability.json', report)
        self.stdout.write(self.style.SUCCESS('Vehicle-fraud global explainability report created.'))

    def validate_data(self, datasets_dir, models_dir):
        specifications = {
            'india_insurance_claims.csv': {
                'required': INSURANCE_FEATURES + ['fraud_reported', 'vehicle_claim', 'total_claim_amount'],
                'label': 'fraud_reported', 'labels': {'Y', 'N'}, 'minimum_rows': 100,
            },
            'india_fraud_oracle.csv': {
                'required': ORACLE_FEATURES + ['FraudFound_P'],
                'label': 'FraudFound_P', 'labels': {'0', '1'}, 'minimum_rows': 100,
            },
            'india_vehicle_fraud.csv': {
                'required': vehicle_fraud.FEATURES + ['fraud_outcome'],
                'label': 'fraud_outcome', 'labels': set(vehicle_fraud.LABELS), 'minimum_rows': 40,
            },
        }
        audit = {
            'validated_at': datetime.now(timezone.utc).isoformat(),
            'data_classification': 'synthetic demo datasets; not production claim outcomes',
            'datasets': {},
        }
        errors = []
        for filename, spec in specifications.items():
            path = datasets_dir / filename
            if not path.is_file():
                errors.append(f'Missing dataset: {path}')
                continue
            try:
                frame = pd.read_csv(path, encoding='utf-8-sig')
            except Exception as exc:
                errors.append(f'Could not read {filename}: {exc}')
                continue
            missing_columns = sorted(set(spec['required']) - set(frame.columns))
            if missing_columns:
                errors.append(f'{filename} is missing columns: {", ".join(missing_columns)}')
                continue
            if len(frame) < spec['minimum_rows']:
                errors.append(f'{filename} has {len(frame)} rows; expected at least {spec["minimum_rows"]}.')
            labels = frame[spec['label']].astype(str).str.strip()
            unexpected = sorted(set(labels.dropna().unique()) - spec['labels'])
            if unexpected:
                errors.append(f'{filename} has unexpected {spec["label"]} labels: {unexpected}')
            counts = {str(label): int(count) for label, count in labels.value_counts().items()}
            if not spec['labels'].issubset(set(counts)):
                errors.append(f'{filename} must contain every expected class {sorted(spec["labels"])}.')
            if filename == 'india_vehicle_fraud.csv' and min(counts.get(label, 0) for label in ('fraud', 'genuine')) < 8:
                errors.append(f'{filename} needs at least 8 rows in each fraud_outcome class.')
            if filename == 'india_insurance_claims.csv':
                target = pd.to_numeric(frame['vehicle_claim'], errors='coerce')
                if target.isna().any() or not target.map(math.isfinite).all() or (target < 0).any():
                    errors.append('india_insurance_claims.csv vehicle_claim target must be finite and non-negative.')
            audit['datasets'][filename] = {
                'rows': int(len(frame)),
                'columns': int(len(frame.columns)),
                'label_column': spec['label'],
                'label_counts': counts,
                'missing_value_fraction': round(float(frame.isna().sum().sum() / max(frame.size, 1)), 6),
                'sha256': sha256_file(path),
            }
        audit['passed'] = not errors
        audit['errors'] = errors
        write_json(models_dir / 'data_validation.json', audit)
        if errors:
            raise CommandError('Dataset validation failed:\n- ' + '\n- '.join(errors))
        self.stdout.write(self.style.SUCCESS('Dataset schema, labels, row counts and repair target validated.'))

    def validate_quality(self, backend_dir, models_dir):
        training_path = models_dir / 'training_report.json'
        vehicle_path = models_dir / 'vehicle_fraud_report.json'
        data_path = models_dir / 'data_validation.json'
        required_artifacts = [
            'fraud_risk.joblib', 'repair_cost.joblib', 'total_loss.joblib',
            'fraud_oracle_fraud.joblib', 'vehicle_fraud.joblib', 'fraud_oracle_evaluation.png',
        ]
        errors = []
        for path in (training_path, vehicle_path, data_path):
            if not path.is_file():
                errors.append(f'Missing report: {path.name}')
        artifact_paths = [models_dir / name for name in required_artifacts]
        for path in artifact_paths:
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f'Missing or empty model artifact: {path.name}')
        if errors:
            raise CommandError('MLOps quality gate failed:\n- ' + '\n- '.join(errors))

        training = json.loads(training_path.read_text(encoding='utf-8'))
        vehicle = json.loads(vehicle_path.read_text(encoding='utf-8'))
        data_audit = json.loads(data_path.read_text(encoding='utf-8'))
        if not data_audit.get('passed'):
            errors.append('The dataset validation report did not pass.')

        metrics = {row.get('model'): row for row in training.get('metrics', [])}
        for name in ('insurance_fraud', 'total_loss', 'fraud_oracle_fraud'):
            row = metrics.get(name)
            auc = row.get('roc_auc') if row else None
            if auc is None or not math.isfinite(float(auc)) or float(auc) < 0.5:
                errors.append(f'{name} ROC-AUC must be finite and at least 0.50 (got {auc}).')
        repair = metrics.get('repair_cost')
        if not repair:
            errors.append('Repair-cost model metrics are missing.')
        else:
            for name in ('mae', 'rmse'):
                value = repair.get(name)
                if value is None or not math.isfinite(float(value)) or float(value) < 0:
                    errors.append(f'Repair-cost {name.upper()} must be finite and non-negative (got {value}).')

        oracle = metrics.get('fraud_oracle_fraud', {})
        oracle_selection = oracle.get('threshold_selection', {}).get('selected_validation_metrics', {})
        if float(oracle_selection.get('recall', 0)) < 0.75:
            errors.append('Fraud Oracle validation recall must be at least 0.75.')
        oracle_rate = float(data_audit.get('datasets', {}).get('india_fraud_oracle.csv', {}).get('label_counts', {}).get('1', 0))
        oracle_rows = int(data_audit.get('datasets', {}).get('india_fraud_oracle.csv', {}).get('rows', 0))
        if not oracle_rows or float(oracle_selection.get('precision', 0)) <= oracle_rate / oracle_rows:
            errors.append('Fraud Oracle validation precision must exceed the dataset fraud rate.')

        vehicle_metrics = vehicle.get('metrics', {}).get('at_selected_threshold', {})
        vehicle_rate = int(vehicle.get('fraud_claims', 0)) / max(int(vehicle.get('labelled_claims', 0)), 1)
        if float(vehicle_metrics.get('recall', 0)) < 0.75:
            errors.append('Vehicle-fraud out-of-fold recall must be at least 0.75.')
        if float(vehicle_metrics.get('precision', 0)) <= vehicle_rate:
            errors.append('Vehicle-fraud out-of-fold precision must exceed the dataset fraud rate.')

        gate = {
            'validated_at': datetime.now(timezone.utc).isoformat(),
            'passed': not errors,
            'errors': errors,
            'gates': {
                'classification_roc_auc_minimum': 0.5,
                'fraud_recall_minimum': 0.75,
                'fraud_precision_above_prevalence': True,
                'repair_cost_error_metrics_finite': True,
                'all_expected_artifacts_present': True,
            },
        }
        write_json(models_dir / 'model_quality_gate.json', gate)
        if errors:
            raise CommandError('MLOps model quality gate failed:\n- ' + '\n- '.join(errors))

        try:
            revision = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=backend_dir.parent, text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = 'unknown'
        requirements = backend_dir / 'django_backend' / 'requirements.txt'
        manifest = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'git_revision': revision,
            'python_version': platform.python_version(),
            'requirements_sha256': sha256_file(requirements) if requirements.is_file() else None,
            'datasets': data_audit.get('datasets', {}),
            'artifacts': {path.name: {'bytes': path.stat().st_size, 'sha256': sha256_file(path)} for path in artifact_paths},
            'reports': {
                path.name: sha256_file(path)
                for path in (training_path, vehicle_path, data_path, models_dir / 'model_quality_gate.json')
            },
        }
        write_json(models_dir / 'mlops_manifest.json', manifest)
        self.stdout.write(self.style.SUCCESS('Model metrics passed the CI quality gates; manifest created.'))
