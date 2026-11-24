"""Load a small, realistic US personal-auto demo in one command.

    python manage.py load_demo            # create or refresh the demo data
    python manage.py load_demo --reset    # delete the demo data, then recreate it

Everything this command creates is marked so it can be found and removed again:
users have emails on DEMO_DOMAIN, and customer, policy, claim and investigation
numbers start with "DEMO-". Nothing else in the database is changed. People, phone
numbers (555 exchange) and VINs are fictional.

The staff accounts and the demo customer get a known password, so the command
refuses to run when DEBUG is False unless --allow-production is passed.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User, UserProfile
from apps.claims.models import (
    Claim, ClaimNote, ClaimPriority, ClaimStatus, ClaimStatusHistory, ClaimTimeline,
    IncidentSeverity, IncidentType,
)
from apps.customers.models import Customer
from apps.investigations.models import FraudAlert, Investigation, InvestigationEvidence, InvestigationNote
from apps.notifications.models import Notification
from apps.policies.models import PaymentFrequency, Policy, PolicyCoverage, PolicyStatus, PolicyType
from apps.vehicles.models import Vehicle, VehicleStatus
from common.risk import fraud_risk_band

DEMO_DOMAIN = 'demo.insurex.test'
DEMO_PREFIX = 'DEMO-'
DEFAULT_PASSWORD = 'InsureX@Demo2026'
STAFF_TIMEZONE = 'America/New_York'

STAFF = [
    {'key': 'admin', 'email': f'admin@{DEMO_DOMAIN}', 'first_name': 'Rachel', 'last_name': 'Adams',
     'role': Role.ADMIN, 'department': 'Claims Operations', 'phone': '(614) 555-0110'},
    {'key': 'employee', 'email': f'employee@{DEMO_DOMAIN}', 'first_name': 'James', 'last_name': 'Carter',
     'role': Role.EMPLOYEE, 'department': 'Auto Claims', 'phone': '(614) 555-0111'},
    {'key': 'investigator', 'email': f'investigator@{DEMO_DOMAIN}', 'first_name': 'Maria', 'last_name': 'Gonzalez',
     'role': Role.INVESTIGATOR, 'department': 'Special Investigations Unit (SIU)', 'phone': '(614) 555-0112'},
]

FULL_COVERAGE_PLAN = {
    'id': 'personal-auto-full',
    'name': 'Personal Auto - Full Coverage',
    'category': 'Personal Auto',
    'coverage_sections': [
        'Bodily injury liability', 'Property damage liability', 'Uninsured/underinsured motorist',
        'Medical payments', 'Collision', 'Comprehensive',
    ],
    'mandatory_covers': ['State minimum liability'],
    'addons': ['Rental reimbursement', 'Roadside assistance', 'Glass coverage'],
    'estimate_source': 'Demo data; not a filed rate',
}

# Policy start dates are days before today, so the demo always has active policies.
# Premiums and deductibles are annual US-dollar figures for illustration only.
CUSTOMERS = [
    {
        'key': 'sarah', 'login': True, 'email': f'customer@{DEMO_DOMAIN}',
        'first_name': 'Sarah', 'last_name': 'Mitchell', 'phone': '(614) 555-0101',
        'address': '1420 Neil Avenue, Columbus, OH 43201', 'timezone': 'America/New_York',
        'dob': (1990, 4, 12), 'license_number': 'OH-SM482915', 'license_state': 'OH',
        'credit_score': 782, 'risk_rating': 'low', 'number': 'DEMO-CUST-0001',
        'vehicles': [
            {'plate': 'JKL 4521', 'state': 'OH', 'vin': '2HGDEM00000000001', 'make': 'Honda',
             'model': 'Civic EX', 'year': 2022, 'color': 'Platinum White Pearl', 'purchase': (2022, 3, 15),
             'price': 26800, 'fuel': 'gasoline', 'transmission': 'cvt', 'engine': '2.0', 'body': 'Sedan',
             'mileage': 28400, 'policy': 'DEMO-POL-0001', 'start_days_ago': 300, 'premium': 1380,
             'deductible': 500, 'pip': 0},
            {'plate': 'HXR 7780', 'state': 'OH', 'vin': '2T3DEM00000000002', 'make': 'Toyota',
             'model': 'RAV4 XLE', 'year': 2023, 'color': 'Magnetic Gray', 'purchase': (2023, 8, 20),
             'price': 33400, 'fuel': 'hybrid', 'transmission': 'cvt', 'engine': '2.5', 'body': 'SUV',
             'mileage': 15200, 'policy': 'DEMO-POL-0002', 'start_days_ago': 120, 'premium': 1620,
             'deductible': 1000, 'pip': 0},
        ],
    },
    {
        'key': 'marcus', 'login': False, 'email': f'marcus.johnson@{DEMO_DOMAIN}',
        'first_name': 'Marcus', 'last_name': 'Johnson', 'phone': '(404) 555-0102',
        'address': '880 Glenwood Avenue SE, Apt 214, Atlanta, GA 30316', 'timezone': 'America/New_York',
        'dob': (1986, 11, 2), 'license_number': 'GA-055718342', 'license_state': 'GA',
        'credit_score': 655, 'risk_rating': 'medium', 'number': 'DEMO-CUST-0002',
        'vehicles': [
            {'plate': 'CTR 3390', 'state': 'GA', 'vin': '1FTDEM00000000003', 'make': 'Ford',
             'model': 'F-150 XLT', 'year': 2022, 'color': 'Rapid Red', 'purchase': (2022, 6, 4),
             'price': 48500, 'fuel': 'gasoline', 'transmission': 'automatic', 'engine': '3.5', 'body': 'Pickup',
             'mileage': 41800, 'policy': 'DEMO-POL-0003', 'start_days_ago': 200, 'premium': 1940,
             'deductible': 500, 'pip': 0},
            # Bought in 2024; insured with us only 55 days ago after switching carriers.
            {'plate': 'RKT 6612', 'state': 'GA', 'vin': '1GNDEM00000000004', 'make': 'Chevrolet',
             'model': 'Tahoe LT', 'year': 2024, 'color': 'Black', 'purchase': (2024, 2, 10),
             'price': 64200, 'fuel': 'gasoline', 'transmission': 'automatic', 'engine': '5.3', 'body': 'SUV',
             'mileage': 33600, 'policy': 'DEMO-POL-0004', 'start_days_ago': 55, 'premium': 2860,
             'deductible': 500, 'pip': 0},
        ],
    },
    {
        'key': 'elena', 'login': False, 'email': f'elena.rodriguez@{DEMO_DOMAIN}',
        'first_name': 'Elena', 'last_name': 'Rodriguez', 'phone': '(713) 555-0103',
        'address': '5214 Braesvalley Drive, Houston, TX 77096', 'timezone': 'America/Chicago',
        'dob': (1978, 6, 21), 'license_number': 'TX-31847562', 'license_state': 'TX',
        'credit_score': 741, 'risk_rating': 'low', 'number': 'DEMO-CUST-0003',
        'vehicles': [
            {'plate': 'BX2 1187', 'state': 'TX', 'vin': '4T1DEM00000000005', 'make': 'Toyota',
             'model': 'Camry LE', 'year': 2011, 'color': 'Classic Silver', 'purchase': (2011, 5, 10),
             'price': 22100, 'fuel': 'gasoline', 'transmission': 'automatic', 'engine': '2.5', 'body': 'Sedan',
             'mileage': 168000, 'policy': 'DEMO-POL-0005', 'start_days_ago': 330, 'premium': 1120,
             'deductible': 500, 'pip': 2500},
            {'plate': 'DPK 5504', 'state': 'TX', 'vin': '5XYDEM00000000006', 'make': 'Kia',
             'model': 'Telluride EX', 'year': 2024, 'color': 'Dark Moss', 'purchase': (2024, 1, 18),
             'price': 44900, 'fuel': 'gasoline', 'transmission': 'automatic', 'engine': '3.8', 'body': 'SUV',
             'mileage': 21900, 'policy': 'DEMO-POL-0006', 'start_days_ago': 250, 'premium': 2180,
             'deductible': 1000, 'pip': 2500},
        ],
    },
]


def actual_cash_value(price, model_year, today):
    """Rough ACV for the demo: about 12% a year off the purchase price, never below 20%."""
    age = max(0, today.year - model_year)
    return int(round(price * max(0.20, 1 - 0.12 * age), -2))


# Each status step is (status, days ago, hour, actor key, reason). The first step is the
# submission, so its date is when the claim was reported. Actor keys are staff keys or 'customer'.
CLAIMS = [
    {
        'number': 'DEMO-CLM-0001', 'plate': 'JKL 4521',
        'story': 'Honest minor collision: rear-ended at a red light, small bill, paid and closed',
        'incident_days_ago': 62, 'incident_time': (17, 40), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MODERATE, 'vehicles_involved': 2,
        'location': 'N High St & E 5th Ave, Columbus, OH', 'lat': '39.988100', 'lon': '-83.005200',
        'witnesses': True,
        'witness_details': 'A pedestrian at the crosswalk saw the pickup hit the car; the other driver admitted fault.',
        'police_report': True, 'police_report_number': 'Columbus PD crash report 26-118734',
        'claim_amount': 2450, 'estimate': 2380, 'priority': ClaimPriority.LOW,
        'description': 'A pickup truck rear-ended my car while I was stopped at the red light. The rear bumper '
                       'cover is cracked and the left tail light is broken. Repaired at a direct-repair shop.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 61, 9, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 59, 11, 'employee', 'Photos match the description; estimate within range.'),
            (ClaimStatus.APPROVED, 55, 15, 'employee', 'Approved for repair at the direct-repair shop.'),
            (ClaimStatus.CLOSED, 48, 17, 'employee',
             "Repair completed; $1,880 paid to the shop after the $500 deductible. "
             "Subrogation opened against the other driver's carrier."),
        ],
        'notes': [('employee', 'Rear bumper cover and tail light only; no structural damage. Low risk, fast-track. '
                               'Other driver at fault: pursue subrogation to recover the payment and the deductible.',
                   True)],
    },
    {
        'number': 'DEMO-CLM-0002', 'plate': 'CTR 3390',
        'story': 'Inflated repair bill: shop invoice is about 13 times the appraiser estimate',
        'incident_days_ago': 20, 'incident_time': (13, 15), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MODERATE, 'vehicles_involved': 1,
        'location': 'Parking garage, Ponce City Market, Atlanta, GA', 'lat': '33.772600', 'lon': '-84.365500',
        'police_report': False, 'claim_amount': 18900, 'estimate': 1450, 'priority': ClaimPriority.HIGH,
        'description': 'Scraped a concrete pillar while parking. The shop invoice lists a new hood, radiator, both '
                       'headlamps and front airbags, but the field appraiser found only the front bumper cover and '
                       'the left headlamp damaged.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 18, 10, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 16, 12, 'employee',
             'Shop invoice ($18,900) is far above the appraiser estimate ($1,450). Itemized estimate requested.'),
        ],
        'notes': [('employee', 'Airbags were not deployed in the appraiser photos. Asked the shop to hold the '
                               'replaced parts for inspection.', True)],
    },
    {
        'number': 'DEMO-CLM-0003', 'plate': 'RKT 6612',
        'story': 'Claim 8 days after the policy started, reported 41 days late; damage looks old',
        'incident_days_ago': 47, 'incident_time': (21, 30), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MAJOR, 'vehicles_involved': 1,
        'location': 'I-285 near the Moreland Ave exit, Atlanta, GA', 'lat': '33.661800', 'lon': '-84.349400',
        'police_report': False, 'claim_amount': 14800, 'estimate': 14200, 'priority': ClaimPriority.HIGH,
        'description': 'Hit the median barrier at night on I-285. Front bumper, grille, hood and radiator damaged. '
                       'I was traveling for work, so I could not report the claim earlier.',
        'adjuster': None,
        'steps': [
            (ClaimStatus.SUBMITTED, 6, 19, 'customer', 'Claim submitted'),
        ],
        'notes': [('employee', 'Appraiser reports surface rust on the dented panels, which suggests the damage is '
                               'older than 6 weeks.', True)],
    },
    {
        'number': 'DEMO-CLM-0004', 'plate': 'RKT 6612',
        'story': 'Night-time theft with no police report, on the same new-policy SUV a month after its damage claim',
        'incident_days_ago': 9, 'incident_time': (2, 40), 'type': IncidentType.THEFT,
        'severity': IncidentSeverity.TOTAL_LOSS, 'vehicles_involved': 1,
        'location': 'Apartment parking lot, 880 Glenwood Avenue SE, Atlanta, GA', 'lat': '33.740600',
        'lon': '-84.358900',
        'police_report': False, 'claim_amount': 58500, 'estimate': 58500, 'priority': ClaimPriority.CRITICAL,
        'description': 'The SUV was parked in my apartment lot overnight and was gone at 6 am. I have both key fobs. '
                       'I have not filed a police report yet because I was told to wait a day in case it was towed.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 8, 8, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 7, 11, 'employee',
             'Theft claim without a police report. Second claim on this vehicle within a month.'),
            (ClaimStatus.INVESTIGATION, 6, 10, 'employee', 'Referred to SIU; investigator assigned'),
        ],
        'notes': [('employee', 'Customer asked to file a police report and send both key fobs. Referred to SIU.', True)],
        'investigation': {
            'number': 'DEMO-INV-0001',
            'summary': 'Theft of a 2024 Chevrolet Tahoe insured 46 days earlier, with no police report, a month '
                       'after a late-reported damage claim on the same vehicle.',
            'findings': 'Peach Pass toll records show the vehicle entering the I-75 Express Lanes at 03:12, '
                        '30 minutes after the reported theft time. Apartment complex CCTV requested.',
            'evidence': [
                ('financial', 'Peach Pass toll records',
                 'State Road and Tollway Authority statement: I-75 Express Lanes entry at 03:12 on the night of '
                 'the theft.', True),
                ('surveillance', 'Apartment complex CCTV request',
                 'Request sent to the property manager for parking lot camera footage, 01:00-06:00.', False),
                ('statement', 'Insured recorded statement',
                 'Insured says both key fobs are at home and no one else drives the vehicle.', False),
            ],
            'notes': [
                'Called the insured: he says he called the police non-emergency line but was not given a report '
                'number. Asked for the date and time of the call.',
            ],
        },
    },
    {
        'number': 'DEMO-CLM-0005', 'plate': 'BX2 1187',
        'story': 'Flood total loss on a 15-year-old car: the model flags it, the adjuster checks and pays actual cash value',
        'incident_days_ago': 21, 'incident_time': (23, 0), 'type': IncidentType.WATER_DAMAGE,
        'severity': IncidentSeverity.TOTAL_LOSS, 'vehicles_involved': 1,
        'location': 'Braesvalley Drive, Meyerland, Houston, TX', 'lat': '29.685000', 'lon': '-95.465000',
        'property_damage': True, 'property_damage_details': 'Ground floor of the house also flooded.',
        'witnesses': True, 'witness_details': 'Neighbors on Braesvalley Drive; the whole street was under water.',
        'police_report': False, 'claim_amount': 5600, 'estimate': 5600, 'priority': ClaimPriority.MEDIUM,
        'description': 'Flash flooding after heavy storms. The car was parked on the street and was under '
                       'waist-deep water overnight. The engine was hydrolocked and the interior and wiring are ruined.',
        'adjuster': 'employee',
        'vehicle_status': VehicleStatus.TOTAL_LOSS,
        'steps': [
            (ClaimStatus.SUBMITTED, 20, 9, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 18, 14, 'employee',
             'Appraiser inspection done; National Weather Service flash flood warning for Harris County on the '
             'incident date.'),
            (ClaimStatus.APPROVED, 12, 16, 'employee',
             'Total loss. Pay the actual cash value of $5,600 less the $500 deductible; vehicle to salvage auction.'),
        ],
        'notes': [('employee', "Repair cost is more than the car's actual cash value, so it is a total loss.", True)],
        # The model scores old-car total losses as risky; the adjuster reviewed and dismissed the alert.
        'alert_review': ('dismissed', 'Flooding confirmed by the NWS flash flood warning and the appraiser visit; '
                                      'many cars on the street were submerged. Genuine catastrophe claim.'),
    },
    {
        'number': 'DEMO-CLM-0006', 'plate': 'HXR 7780',
        'story': 'Windshield cracked by a rock on the interstate; small glass claim, just submitted',
        'incident_days_ago': 3, 'incident_time': (10, 20), 'type': IncidentType.GLASS,
        'severity': IncidentSeverity.MINOR, 'vehicles_involved': 1,
        'location': 'I-71 North near Delaware, OH', 'lat': '40.260000', 'lon': '-82.940000',
        'police_report': False, 'claim_amount': 480, 'estimate': 450, 'priority': ClaimPriority.LOW,
        'description': 'A rock thrown up by a truck cracked the windshield. No other damage.',
        'adjuster': None,
        'steps': [
            (ClaimStatus.SUBMITTED, 2, 18, 'customer', 'Claim submitted'),
        ],
        'notes': [],
    },
    {
        'number': 'DEMO-CLM-0007', 'plate': 'DPK 5504',
        'story': 'Three-vehicle accident with injuries, police report and witnesses; under review',
        'incident_days_ago': 10, 'incident_time': (8, 45), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MAJOR, 'vehicles_involved': 3,
        'location': 'I-45 North Freeway near Crosstimbers St, Houston, TX', 'lat': '29.830000', 'lon': '-95.398000',
        'injuries': True,
        'injury_details': 'Driver of the other car: fractured wrist. Insured: minor bruises, treated and released '
                          'at an urgent care clinic.',
        'property_damage': True, 'property_damage_details': 'Highway guardrail damaged.',
        'witnesses': True, 'witness_details': 'A Houston police officer on patrol and a passenger on the METRO bus behind.',
        'police_report': True, 'police_report_number': 'Houston PD crash report 2026-0118402',
        'claim_amount': 9800, 'estimate': 9400, 'priority': ClaimPriority.HIGH,
        'description': 'A box truck braked suddenly in morning traffic; the car in front of me stopped and I hit it, '
                       'then the bus behind hit my SUV. Front and rear damage.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 9, 12, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 7, 10, 'employee',
             'Police report and medical records received. Third-party bodily injury claim to be handled separately.'),
        ],
        'notes': [('employee', 'Front and rear damage is consistent with a three-vehicle chain-reaction crash. '
                               'Rear damage: subrogate against the bus operator.', True)],
    },
]


def _demo_email(email):
    return (email or '').lower().endswith('@' + DEMO_DOMAIN)


class Command(BaseCommand):
    help = (
        'Load a small US personal-auto demo: 4 logins (admin, employee, investigator, customer) on '
        f'@{DEMO_DOMAIN}, 3 customers with cars and active policies, and 7 claims scored by the AI. '
        'Safe to run again; --reset deletes only the demo data and recreates it. '
        'Because it creates accounts with a known password, it refuses to run when DEBUG is False '
        'unless --allow-production is passed.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD,
                            help=f'Password for the demo logins (default: {DEFAULT_PASSWORD}).')
        parser.add_argument('--reset', action='store_true',
                            help='Delete the demo data (and only the demo data), then recreate it.')
        parser.add_argument('--allow-production', action='store_true',
                            help='Run even when DEBUG is False. This creates accounts with a known password.')
        parser.add_argument('--skip-assessment', action='store_true',
                            help='Do not run the AI assessment on the demo claims.')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError(
                'Refusing to load demo data while DEBUG is False: it creates accounts with a known password. '
                'Pass --allow-production if you really want this.'
            )
        password = options['password']
        if len(password) < 8:
            raise CommandError('The demo password must be at least 8 characters.')

        self.today = timezone.localdate()
        if options['reset']:
            with transaction.atomic():
                self.delete_demo_data()

        with transaction.atomic():
            self.users = self.create_staff(password)
            self.vehicles = {}
            for spec in CUSTOMERS:
                self.create_customer(spec, password)
            claims = [self.create_claim(spec) for spec in CLAIMS]

        results = {}
        if not options['skip_assessment']:
            results = self.assess(claims)
        self.open_investigations(claims)
        self.report(claims, results, password)

    # ----- reset -----

    def delete_demo_data(self):
        demo_users = User.objects.filter(email__iendswith='@' + DEMO_DOMAIN)
        claims = Claim.objects.filter(claim_number__startswith=DEMO_PREFIX, customer__in=demo_users)
        counts = {'claims': claims.count()}
        claims.delete()  # cascades to assessments, alerts, investigations, timeline, notes
        counts['policies'] = Policy.objects.filter(customer__in=demo_users).count()
        Policy.objects.filter(customer__in=demo_users).delete()
        counts['vehicles'] = Vehicle.objects.filter(customer__in=demo_users).count()
        Vehicle.objects.filter(customer__in=demo_users).delete()
        Customer.objects.filter(user__in=demo_users).delete()
        Notification.objects.filter(recipient__in=demo_users).delete()

        from apps.accounts.account_removal import account_history_records
        deleted, kept = 0, []
        for user in list(demo_users):
            # A demo staff login may have been used on real claims; deleting it would
            # cascade into or blank those records, so keep it and reuse it.
            if account_history_records(user):
                kept.append(user.email)
                continue
            user.delete()
            deleted += 1
        self.stdout.write(
            f"Reset: deleted {counts['claims']} demo claims, {counts['policies']} policies, "
            f"{counts['vehicles']} vehicles and {deleted} demo users."
        )
        for email in kept:
            self.stdout.write(self.style.WARNING(
                f'Kept {email}: it is referenced by non-demo records. It will be reused.'
            ))

    # ----- users and customers -----

    def upsert_user(self, *, email, first_name, last_name, role, phone, address='', department='', password=None,
                    tz=STAFF_TIMEZONE):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            username = email.split('@')[0].replace('.', '-')
            username = f'demo-{username}'
            if User.objects.filter(username=username).exists():
                raise CommandError(f'Username {username!r} is already taken by a non-demo account.')
            user = User(email=email, username=username)
        user.first_name, user.last_name = first_name, last_name
        user.role, user.phone, user.address, user.department = role, phone, address, department
        user.is_active, user.is_verified = True, True
        user.is_staff = user.is_superuser = False
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        UserProfile.objects.update_or_create(
            user=user, defaults={'timezone': tz, 'preferred_language': 'en'},
        )
        return user

    def create_staff(self, password):
        users = {}
        for spec in STAFF:
            users[spec['key']] = self.upsert_user(
                email=spec['email'], first_name=spec['first_name'], last_name=spec['last_name'],
                role=spec['role'], phone=spec['phone'], department=spec['department'], password=password,
            )
        return users

    def _check_owned(self, obj, label, owner):
        if obj is not None and not _demo_email(owner.email):
            raise CommandError(f'{label} already exists and belongs to a non-demo account; refusing to change it.')

    def create_customer(self, spec, password):
        user = self.upsert_user(
            email=spec['email'], first_name=spec['first_name'], last_name=spec['last_name'],
            role=Role.CUSTOMER, phone=spec['phone'], address=spec['address'],
            password=password if spec['login'] else None, tz=spec['timezone'],
        )
        existing = Customer.objects.filter(customer_number=spec['number']).exclude(user=user).first()
        if existing:
            raise CommandError(f"Customer number {spec['number']} belongs to a non-demo account; refusing to change it.")
        dob = datetime(*spec['dob']).date()
        Customer.objects.update_or_create(user=user, defaults={
            'customer_number': spec['number'], 'date_of_birth': dob,
            'license_number': spec['license_number'], 'license_state': spec['license_state'],
            'license_expiry': dob.replace(year=dob.year + 50), 'credit_score': spec['credit_score'],
            'risk_rating': spec['risk_rating'], 'notes': 'Demo customer created by load_demo.',
        })
        if spec['login']:
            self.users['customer'] = user
            self.customer_login = {'email': user.email}

        for v in spec['vehicles']:
            vehicle = Vehicle.objects.filter(vin=v['vin']).select_related('customer').first()
            self._check_owned(vehicle, f"Vehicle VIN {v['vin']}", vehicle.customer if vehicle else None)
            vehicle, _ = Vehicle.objects.update_or_create(vin=v['vin'], defaults={
                'customer': user, 'make': v['make'], 'model': v['model'], 'year': v['year'],
                'color': v['color'], 'license_plate': v['plate'], 'license_state': v['state'],
                'purchase_date': datetime(*v['purchase']).date(), 'purchase_price': Decimal(v['price']),
                'current_mileage': v['mileage'], 'fuel_type': v['fuel'], 'transmission': v['transmission'],
                'engine_size': Decimal(v['engine']), 'body_style': v['body'],
                'registration_expiry': datetime(*v['purchase']).date().replace(year=v['purchase'][0] + 15),
                'status': VehicleStatus.ACTIVE,
            })
            policy = Policy.objects.filter(policy_number=v['policy']).select_related('customer').first()
            self._check_owned(policy, f"Policy {v['policy']}", policy.customer if policy else None)
            start = self.today - timedelta(days=v['start_days_ago'])
            acv = actual_cash_value(v['price'], v['year'], self.today)
            policy, _ = Policy.objects.update_or_create(policy_number=v['policy'], defaults={
                'customer': user, 'agent': self.users['employee'], 'type': PolicyType.AUTO_COMPREHENSIVE,
                'status': PolicyStatus.ACTIVE, 'start_date': start, 'end_date': start + timedelta(days=364),
                'premium': Decimal(v['premium']), 'deductible': Decimal(v['deductible']),
                'payment_frequency': PaymentFrequency.ANNUAL, 'auto_renew': True, 'vehicle': vehicle,
                'coverage': {'policy_plan': FULL_COVERAGE_PLAN,
                             'limits': {'bodily_injury': '100/300', 'property_damage': 100000},
                             'actual_cash_value': acv, 'demo': True},
            })
            PolicyCoverage.objects.update_or_create(policy=policy, defaults={
                'liability': Decimal('300000'), 'collision': Decimal(acv), 'comprehensive': Decimal(acv),
                'uninsured_motorist': Decimal('100000'), 'medical_payments': Decimal('5000'),
                'personal_injury_protection': Decimal(v['pip']),
                'roadside_assistance': True, 'rental_reimbursement': True, 'glass_coverage': True,
            })
            vehicle.policy = policy
            vehicle.save(update_fields=['policy', 'updated_at'])
            self.vehicles[v['plate']] = vehicle

    # ----- claims -----

    def _at(self, days_ago, hour, minute=0):
        moment = datetime.combine(self.today - timedelta(days=days_ago), time(hour, minute))
        return timezone.make_aware(moment) if settings.USE_TZ else moment

    def _actor(self, key):
        return self.users['customer'] if key == 'customer' else self.users[key]

    def create_claim(self, spec):
        vehicle = self.vehicles[spec['plate']]
        existing = Claim.objects.filter(claim_number=spec['number']).select_related('customer').first()
        self._check_owned(existing, f"Claim {spec['number']}", existing.customer if existing else None)
        final_status = spec['steps'][-1][0]
        submitted_at = self._at(spec['steps'][0][1], spec['steps'][0][2])
        complexity = min(1.0, 0.2 + min(max(spec['vehicles_involved'] - 1, 0), 3) * 0.12
                         + spec.get('injuries', False) * 0.2 + spec.get('property_damage', False) * 0.12
                         + spec.get('witnesses', False) * 0.08 + spec['police_report'] * 0.08)
        adjuster = self.users[spec['adjuster']] if spec['adjuster'] else None
        investigator = self.users['investigator'] if 'investigation' in spec else None
        defaults = {
            'customer': vehicle.customer, 'policy': vehicle.policy, 'vehicle': vehicle,
            'incident_date': self.today - timedelta(days=spec['incident_days_ago']),
            'incident_time': time(*spec['incident_time']),
            'incident_type': spec['type'], 'incident_severity': spec['severity'],
            'location': spec['location'], 'latitude': Decimal(spec['lat']), 'longitude': Decimal(spec['lon']),
            'number_of_vehicles': spec['vehicles_involved'],
            'injuries': spec.get('injuries', False), 'injury_details': spec.get('injury_details', ''),
            'property_damage': spec.get('property_damage', False),
            'property_damage_details': spec.get('property_damage_details', ''),
            'witnesses': spec.get('witnesses', False), 'witness_details': spec.get('witness_details', ''),
            'police_report': spec['police_report'], 'police_report_number': spec.get('police_report_number', ''),
            'claim_amount': Decimal(spec['claim_amount']), 'estimated_repair_cost': Decimal(spec['estimate']),
            'complexity_score': Decimal(str(round(complexity, 3))),
            'description': spec['description'], 'status': final_status, 'priority': spec['priority'],
            'assigned_adjuster': adjuster, 'assigned_investigator': investigator,
            'closed_at': self._at(*spec['steps'][-1][1:3]) if final_status == ClaimStatus.CLOSED else None,
        }
        claim, _ = Claim.objects.update_or_create(claim_number=spec['number'], defaults=defaults)
        # submitted_at is auto_now_add; the late-report fraud rule reads it, so backdate it.
        Claim.objects.filter(pk=claim.pk).update(submitted_at=submitted_at)
        claim.refresh_from_db()

        if spec.get('vehicle_status'):
            Vehicle.objects.filter(pk=vehicle.pk).update(status=spec['vehicle_status'])

        # Rebuild the audit trail so re-runs do not duplicate it.
        claim.status_history.all().delete()
        claim.timeline.all().delete()
        claim.notes.all().delete()
        Notification.objects.filter(related_object_type='claim', related_object_id=str(claim.pk)).delete()

        previous = ''
        for status, days_ago, hour, actor_key, reason in spec['steps']:
            actor = self._actor(actor_key)
            when = self._at(days_ago, hour)
            history = ClaimStatusHistory.objects.create(
                claim=claim, from_status=previous, to_status=status, reason=reason, changed_by=actor,
            )
            label = dict(ClaimStatus.choices)[status]
            if previous:
                title, description, system = f'Status changed to {label}', reason, False
            else:
                title, description, system = 'Claim Submitted', 'New claim has been submitted', True
            entry = ClaimTimeline.objects.create(
                claim=claim, status=status, title=title, description=description, user=actor, is_system=system,
            )
            ClaimStatusHistory.objects.filter(pk=history.pk).update(changed_at=when)
            ClaimTimeline.objects.filter(pk=entry.pk).update(timestamp=when)
            if status == ClaimStatus.UNDER_REVIEW and adjuster:
                assigned = ClaimTimeline.objects.create(
                    claim=claim, status=status, title='Adjuster Assigned',
                    description=f'Claim assigned to {adjuster.get_full_name()}', user=adjuster,
                )
                ClaimTimeline.objects.filter(pk=assigned.pk).update(timestamp=when + timedelta(minutes=5))
            if status == ClaimStatus.INVESTIGATION and investigator:
                assigned = ClaimTimeline.objects.create(
                    claim=claim, status=status, title='Investigator Assigned',
                    description=f'Claim assigned to investigator {investigator.get_full_name()}', user=adjuster,
                )
                ClaimTimeline.objects.filter(pk=assigned.pk).update(timestamp=when + timedelta(minutes=5))
            notification = Notification.objects.create(
                recipient=claim.customer, notification_type='claim',
                title='Claim submitted' if not previous else 'Claim status updated',
                message=(f'Claim {claim.claim_number} was submitted successfully.' if not previous
                         else f'Claim {claim.claim_number} is now {label}.'),
                link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=str(claim.pk),
                is_read=days_ago > 7,
            )
            Notification.objects.filter(pk=notification.pk).update(sent_at=when)
            previous = status

        for actor_key, content, internal in spec['notes']:
            ClaimNote.objects.create(claim=claim, author=self._actor(actor_key), content=content, is_internal=internal)
        return claim

    # ----- AI and investigation -----

    def assess(self, claims):
        """Score every demo claim. A model failure is reported and does not stop the command."""
        from apps.assessments import ai_views

        results = {}
        for claim in claims:
            try:
                assessment = ai_views.run_claim_assessment(claim)
                results[claim.claim_number] = assessment
            except Exception as exc:  # noqa: BLE001 - any model error must not stop the demo load
                results[claim.claim_number] = exc
                self.stderr.write(self.style.WARNING(
                    f'AI assessment failed for {claim.claim_number}: {exc.__class__.__name__}: {exc}'
                ))
        return results

    def open_investigations(self, claims):
        by_number = {claim.claim_number: claim for claim in claims}
        investigator = self.users['investigator']
        for spec in CLAIMS:
            review = spec.get('alert_review')
            if review:
                last = spec['steps'][-1]
                FraudAlert.objects.filter(claim_id=by_number[spec['number']].pk).update(
                    status=review[0], investigator_notes=review[1],
                    reviewed_by=self.users['employee'], reviewed_at=self._at(last[1], last[2]),
                )
            info = spec.get('investigation')
            if not info:
                continue
            claim = Claim.objects.get(pk=by_number[spec['number']].pk)
            fraud_risk = (claim.ai_assessment or {}).get('fraud_risk') or {}
            score = claim.fraud_risk_score or Decimal('0')
            alert = FraudAlert.objects.filter(claim=claim).first()
            if alert is None:
                alert = FraudAlert(
                    claim=claim, risk_score=score, risk_level=fraud_risk_band(score),
                    risk_factors=fraud_risk.get('factors', []),
                    ai_recommendation='Claim assigned to an investigator for review.',
                )
            alert.assigned_investigator = investigator
            alert.status = 'investigation'
            alert.save()

            existing = Investigation.objects.filter(case_number=info['number']).exclude(claim=claim).exists()
            if existing:
                raise CommandError(f"Investigation {info['number']} belongs to a non-demo claim; refusing to change it.")
            started = self._at(spec['steps'][-1][1], spec['steps'][-1][2])
            investigation, _ = Investigation.objects.update_or_create(claim=claim, defaults={
                'investigator': investigator, 'fraud_alert': alert, 'case_number': info['number'],
                'status': 'in_progress', 'priority': 'critical', 'summary': info['summary'],
                'findings': info['findings'], 'started_at': started,
                'estimated_completion': self.today + timedelta(days=10),
            })
            investigation.evidence.all().delete()
            investigation.notes.all().delete()
            for evidence_type, title, description, key in info['evidence']:
                InvestigationEvidence.objects.create(
                    investigation=investigation, evidence_type=evidence_type, title=title,
                    description=description, collected_by=investigator, is_key_evidence=key,
                )
            for content in info['notes']:
                InvestigationNote.objects.create(investigation=investigation, author=investigator, content=content)

    # ----- output -----

    def report(self, claims, results, password):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Demo claims'))
        stories = {spec['number']: spec['story'] for spec in CLAIMS}
        for claim in claims:
            claim.refresh_from_db()
            result = results.get(claim.claim_number)
            if isinstance(result, Exception):
                ai = 'AI assessment failed'
            elif result is None:
                ai = 'not assessed'
            else:
                cost = f"${float(result.predicted_repair_cost or 0):,.0f}"
                ai = (f'fraud {float(claim.fraud_risk_score):.1f} ({result.risk_level}), '
                      f'total loss {float(claim.total_loss_probability):.1f}%, AI repair estimate {cost}')
            alert = ' [fraud alert]' if FraudAlert.objects.filter(claim=claim).exists() else ''
            self.stdout.write(f'  {claim.claim_number}  {claim.get_status_display():<14} {ai}{alert}')
            self.stdout.write(f'      {stories[claim.claim_number]}')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Demo logins'))
        self.stdout.write(f'  Staff (Staff login page), password: {password}')
        for spec in STAFF:
            self.stdout.write(f"    {spec['key']:<13} {spec['email']}")
        login = self.customer_login
        self.stdout.write('  Customer (Customer sign-in page emails a one-time code; with the console email backend '
                          'it appears in the runserver terminal):')
        self.stdout.write(f"    customer      {login['email']}")
        self.stdout.write(f'                  (password for the API login: {password})')
        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
