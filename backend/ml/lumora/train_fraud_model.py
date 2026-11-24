"""Train and benchmark a claim fraud model on Lumora data (offline prototype, Phase 3).

Reads the Lumora tables directly (Parquet or CSV), builds features that are known at or soon
after first notice of loss, trains a LightGBM classifier, and compares it with simple red-flag
rules at the same SIU review capacity.

This is an offline experiment. Its output is NOT loaded by the app: the live scoring in
ml_service.py is unchanged until Phases 2 and 3 of docs/US_MIGRATION_PLAN.md are done.

Usage (from backend/):
    python ml/lumora/train_fraud_model.py --data data/us/output --out ml/lumora/runs/full
    python ml/lumora/train_fraud_model.py --data data/us/sample --out ml/lumora/runs/sample

Labels:
    --label truth  ground_truth/truth_claims.is_claim_fraud (the upper bound; never import
                   ground_truth into the app database)
    --label siu    siu_investigations outcomes only (what a real carrier would have)
"""
import argparse
import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

CATEGORICAL = [
    'state', 'channel', 'payment_plan', 'reported_by', 'report_channel', 'loss_cause',
    'loss_location_type', 'fault_indicator', 'segment', 'declared_usage',
]

# Never used as features: settled amounts, statuses and outcomes are only known after the
# claim is handled, so using them would leak the answer.
LEAKY_COLUMNS = {
    'paid_total', 'reserve_total', 'incurred_total', 'recovery_total', 'net_incurred',
    'claim_status', 'closed_date', 'total_loss_flag', 'attorney_represented',
}


def read_table(data_dir, name, columns=None):
    """Read one Lumora table, preferring Parquet."""
    parquet, csv = data_dir / f'{name}.parquet', data_dir / f'{name}.csv'
    if parquet.exists():
        return pd.read_parquet(parquet, columns=columns)
    if csv.exists():
        return pd.read_csv(csv, usecols=columns, low_memory=False)
    raise FileNotFoundError(f'Missing table {name} (.parquet or .csv) in {data_dir}')


def zip3(series):
    return series.astype('string').str.zfill(5).str[:3]


def build_features(data_dir):
    claims = read_table(data_dir, 'claims')
    claims = claims.drop(columns=[c for c in LEAKY_COLUMNS if c in claims.columns])
    for col in ('loss_datetime', 'report_datetime'):
        claims[col] = pd.to_datetime(claims[col])

    terms = read_table(data_dir, 'policy_terms', [
        'term_id', 'renewal_seq', 'new_business_flag', 'term_start', 'term_end', 'channel', 'state',
        'garaging_zip', 'payment_plan', 'prior_lapse_days', 'bind_datetime', 'n_vehicles',
        'nsf_payment_count', 'pip_limit', 'medpay_limit', 'um_flag',
    ])
    for col in ('term_start', 'term_end', 'bind_datetime'):
        terms[col] = pd.to_datetime(terms[col])

    vehicles = read_table(data_dir, 'vehicles', [
        'vehicle_id', 'model_year', 'segment', 'msrp', 'adas_equipped', 'lienholder_flag',
        'declared_usage', 'declared_annual_miles', 'garaging_zip',
    ]).rename(columns={'garaging_zip': 'vehicle_garaging_zip'})

    features = read_table(data_dir, 'claim_features', [
        'claim_id', 'coverage', 'claimant_id', 'claimant_role', 'attorney_id',
        'attorney_retained_date', 'loss_amount', 'acv', 'rental_days',
    ])
    features['attorney_retained_date'] = pd.to_datetime(features['attorney_retained_date'])

    df = claims.merge(terms, on='term_id', how='left').merge(vehicles, on='vehicle_id', how='left')

    # Policy timing: losses soon after binding or right before the term ends are classic signals.
    df['days_bind_to_loss'] = (df.loss_datetime - df.bind_datetime).dt.total_seconds() / 86400
    df['days_term_start_to_loss'] = (df.loss_datetime - df.term_start).dt.days
    df['days_loss_to_term_end'] = (df.term_end - df.loss_datetime).dt.days

    # Reporting: late reports and night or weekend losses.
    df['report_lag_hours'] = (df.report_datetime - df.loss_datetime).dt.total_seconds() / 3600
    df['loss_hour'] = df.loss_datetime.dt.hour
    df['loss_weekday'] = df.loss_datetime.dt.weekday
    df['is_night'] = df.loss_hour.isin([0, 1, 2, 3, 4, 5, 23]).astype(int)
    df['is_catastrophe'] = df.catastrophe_code.notna() & (df.catastrophe_code.astype('string') != '')

    # Mileage: odometer far above what the declared annual miles suggest.
    vehicle_age = (df.loss_datetime.dt.year - df.model_year).clip(lower=0) + 0.5
    expected_miles = df.declared_annual_miles * vehicle_age
    df['odometer_vs_declared'] = df.odometer_at_loss / expected_miles.replace(0, np.nan)
    df['vehicle_age'] = vehicle_age

    # Geography: loss away from where the car is garaged.
    df['loss_state_differs'] = (df.loss_state != df.state).astype(int)
    df['loss_zip3_differs'] = (zip3(df.loss_zip) != zip3(df.vehicle_garaging_zip)).astype(int)

    # History: prior claims by the same customer and vehicle (within the data window).
    df = df.sort_values('loss_datetime')
    df['prior_claims_customer'] = df.groupby('customer_id').cumcount()
    df['prior_claims_vehicle'] = df.groupby('vehicle_id').cumcount()
    prev = df.groupby('customer_id').loss_datetime.shift()
    df['days_since_prev_claim'] = (df.loss_datetime - prev).dt.days

    # Claim composition, from the coverage-level features.
    is_injury = features.coverage.isin(['BI', 'PIP', 'MEDPAY', 'UMBI'])
    agg = features.assign(is_injury=is_injury).groupby('claim_id').agg(
        n_features=('coverage', 'size'),
        n_injury_features=('is_injury', 'sum'),
        n_claimants=('claimant_id', 'nunique'),
        claimed_amount=('loss_amount', 'sum'),
        max_acv=('acv', 'max'),
        rental_days=('rental_days', 'sum'),
        first_attorney_date=('attorney_retained_date', 'min'),
    ).reset_index()
    df = df.merge(agg, on='claim_id', how='left')
    attorney_days = (df.first_attorney_date - df.report_datetime).dt.days
    df['attorney_within_30d'] = (attorney_days <= 30).astype(int)
    df['claimed_vs_msrp'] = df.claimed_amount / df.msrp.replace(0, np.nan)

    for col in ('operator_listed', 'police_report_flag', 'new_business_flag', 'adas_equipped',
                'lienholder_flag', 'um_flag', 'is_catastrophe'):
        df[col] = df[col].astype('boolean').fillna(False).astype(int)
    for col in CATEGORICAL:
        df[col] = df[col].astype('string').fillna('NA').astype('category')

    feature_columns = [
        'days_bind_to_loss', 'days_term_start_to_loss', 'days_loss_to_term_end', 'renewal_seq',
        'new_business_flag', 'prior_lapse_days', 'nsf_payment_count', 'n_vehicles', 'pip_limit',
        'medpay_limit', 'um_flag', 'report_lag_hours', 'loss_hour', 'loss_weekday', 'is_night',
        'is_catastrophe', 'vehicles_involved', 'occupants_in_vehicle', 'police_report_flag',
        'operator_listed', 'operator_age', 'odometer_vs_declared', 'vehicle_age', 'msrp',
        'adas_equipped', 'lienholder_flag', 'loss_state_differs', 'loss_zip3_differs',
        'prior_claims_customer', 'prior_claims_vehicle', 'days_since_prev_claim', 'n_features',
        'n_injury_features', 'n_claimants', 'claimed_amount', 'claimed_vs_msrp', 'max_acv',
        'rental_days', 'attorney_within_30d',
    ] + CATEGORICAL
    return df, feature_columns


def rule_points(df):
    """Red-flag rules in the style of triage_heuristic_v1, adapted to Lumora fields."""
    points = np.zeros(len(df))
    points += 20 * (df.days_bind_to_loss <= 30)
    points += 10 * (df.days_loss_to_term_end <= 15)
    points += 10 * (df.report_lag_hours > 30 * 24)
    points += 20 * ((df.loss_cause == 'THEFT') & (df.police_report_flag == 0))
    points += 10 * ((df.n_injury_features > 0) & (df.police_report_flag == 0))
    points += 20 * (df.prior_claims_customer >= 2)
    points += 25 * (df.prior_claims_vehicle >= 1)
    points += 25 * (df.claimed_vs_msrp > 1)
    return points


def at_capacity(scores, y, excess, capacity):
    """Precision, recall and fraud dollars found when SIU reviews the top `capacity` share."""
    k = max(1, int(round(len(scores) * capacity)))
    order = np.lexsort((np.random.default_rng(0).random(len(scores)), -scores))[:k]
    caught = y[order].sum()
    return {
        'reviewed_claims': int(k),
        'precision': round(float(caught / k), 4),
        'recall': round(float(caught / max(y.sum(), 1)), 4),
        'fraud_dollars_found_share': round(float(excess[order].sum() / max(excess.sum(), 1)), 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, required=True, help='Folder with the Lumora tables (and ground_truth/)')
    parser.add_argument('--out', type=Path, required=True, help='Folder for the model and report')
    parser.add_argument('--label', choices=['truth', 'siu'], default='truth')
    parser.add_argument('--capacity', type=float, default=0.016, help='Share of claims SIU can review (default 1.6%%)')
    parser.add_argument('--test-share', type=float, default=0.25, help='Latest share of claims held out for testing')
    args = parser.parse_args()
    started = time.time()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f'Reading {args.data} ...')
    df, feature_columns = build_features(args.data)
    truth = read_table(args.data / 'ground_truth', 'truth_claims', ['claim_id', 'is_claim_fraud', 'fraud_excess_paid'])
    df = df.merge(truth, on='claim_id', how='left')
    df['is_claim_fraud'] = df.is_claim_fraud.astype('boolean').fillna(False).astype(int)
    df['fraud_excess_paid'] = df.fraud_excess_paid.fillna(0.0)

    if args.label == 'siu':
        siu = read_table(args.data, 'siu_investigations', ['claim_id', 'outcome'])
        siu = siu[siu.outcome.isin(['CONFIRMED_FRAUD', 'CLEARED'])]
        siu['siu_label'] = (siu.outcome == 'CONFIRMED_FRAUD').astype(int)
        df = df.merge(siu[['claim_id', 'siu_label']], on='claim_id', how='left')

    # Time-based split: train on older claims, test on the newest, like a model put into service.
    df = df.sort_values('report_datetime').reset_index(drop=True)
    cut = int(len(df) * (1 - args.test_share))
    train, test = df.iloc[:cut], df.iloc[cut:]
    if args.label == 'siu':
        train = train[train.siu_label.notna()]
        y_train = train.siu_label.astype(int).values
    else:
        y_train = train.is_claim_fraud.values
    print(f'{len(df):,} claims - train {len(train):,} ({y_train.sum():,} positive) - test {len(test):,}')
    if y_train.sum() < 20:
        raise SystemExit('Too few positive labels to train. Use a bigger book, or --label truth.')

    positives = max(y_train.sum(), 1)
    model = lgb.LGBMClassifier(
        n_estimators=600, learning_rate=0.03, num_leaves=31, min_child_samples=40,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
        scale_pos_weight=(len(y_train) - positives) / positives, random_state=42, verbose=-1,
    )
    model.fit(train[feature_columns], y_train, categorical_feature=CATEGORICAL)

    # Always evaluate on the true labels, so the two label modes are comparable.
    y_test = test.is_claim_fraud.values
    excess = test.fraud_excess_paid.values
    model_scores = model.predict_proba(test[feature_columns])[:, 1]
    rules = rule_points(test)
    any_flag = rules > 0
    report = {
        'data': str(args.data), 'label': args.label, 'capacity': args.capacity,
        'claims': len(df), 'train_claims': len(train), 'test_claims': len(test),
        'test_fraud_rate': round(float(y_test.mean()), 4),
        'model': {
            'roc_auc': round(float(roc_auc_score(y_test, model_scores)), 4),
            'pr_auc': round(float(average_precision_score(y_test, model_scores)), 4),
            'at_capacity': at_capacity(model_scores, y_test, excess, args.capacity),
        },
        'rules': {
            'roc_auc': round(float(roc_auc_score(y_test, rules)), 4),
            'any_flag_share': round(float(any_flag.mean()), 4),
            'any_flag_precision': round(float(y_test[any_flag].mean()) if any_flag.any() else 0.0, 4),
            'any_flag_recall': round(float(y_test[any_flag].sum() / max(y_test.sum(), 1)), 4),
            'at_capacity': at_capacity(rules, y_test, excess, args.capacity),
        },
        'seconds': round(time.time() - started, 1),
    }
    importance = pd.DataFrame({'feature': feature_columns, 'gain': model.booster_.feature_importance('gain')})
    importance = importance.sort_values('gain', ascending=False)
    report['top_features'] = importance.head(15).feature.tolist()

    joblib.dump({'model': model, 'features': feature_columns, 'categorical': CATEGORICAL}, args.out / 'lumora_fraud.joblib')
    importance.to_csv(args.out / 'feature_importance.csv', index=False)
    (args.out / 'report.json').write_text(json.dumps(report, indent=2))

    m, r = report['model'], report['rules']
    print(f"\nTest set: {len(test):,} claims, fraud rate {report['test_fraud_rate']:.1%}")
    print(f"SIU capacity {args.capacity:.1%}  ->  {m['at_capacity']['reviewed_claims']:,} claims reviewed")
    print(f"{'':10s}{'ROC-AUC':>9s}{'precision':>11s}{'recall':>9s}{'fraud $':>9s}")
    for name, block in (('Model', m), ('Rules', r)):
        cap = block['at_capacity']
        print(f"{name:10s}{block['roc_auc']:9.3f}{cap['precision']:11.1%}{cap['recall']:9.1%}{cap['fraud_dollars_found_share']:9.1%}")
    print(f"\nTop features: {', '.join(report['top_features'][:8])}")
    print(f"Saved model and report to {args.out}  ({report['seconds']}s)")


if __name__ == '__main__':
    main()
