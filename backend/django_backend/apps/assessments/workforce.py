"""Employee workforce profiles and claim-derived performance metrics."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsStaffMember
from apps.claims.models import Claim, ClaimStatus
from .assignment import OPEN_CLAIM_STATUSES
from .models import EmployeeSkill, RoutingAgentProfile

User = get_user_model()
ACTIVE_CLAIM_STATUSES = [*OPEN_CLAIM_STATUSES, ClaimStatus.INVESTIGATION]
COMPLETED_CLAIM_STATUSES = [ClaimStatus.CLOSED]
WEEKDAYS = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}


class EmployeeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkill
        fields = ['id', 'name', 'level']
        read_only_fields = ['id']


class EmployeeSkillsUpdateSerializer(serializers.Serializer):
    skills = EmployeeSkillSerializer(many=True)

    def validate_skills(self, skills):
        names = [skill['name'].strip().casefold() for skill in skills]
        if any(not name for name in names):
            raise serializers.ValidationError('Skill names cannot be blank.')
        if len(names) != len(set(names)):
            raise serializers.ValidationError('Skill names must be unique for each employee.')
        return skills


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', max_length=150, required=False)
    last_name = serializers.CharField(source='user.last_name', max_length=150, required=False, allow_blank=True)
    department = serializers.CharField(source='user.department', max_length=100, required=False, allow_blank=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    skills = EmployeeSkillSerializer(many=True, required=False)

    class Meta:
        model = RoutingAgentProfile
        fields = [
            'first_name', 'last_name', 'department', 'is_active', 'designation',
            'years_of_experience', 'max_claim_capacity', 'skill_tier',
            'availability_status', 'working_days', 'shift_start_time', 'shift_end_time',
            'leave_status', 'is_demo', 'skills',
        ]

    def validate_max_claim_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError('Maximum claim capacity must be at least 1.')
        if value > 1000:
            raise serializers.ValidationError('Maximum claim capacity cannot exceed 1000.')
        return value

    def validate_years_of_experience(self, value):
        if value > 60:
            raise serializers.ValidationError('Years of experience cannot exceed 60.')
        return value

    def validate_skills(self, skills):
        names = [skill['name'].strip().casefold() for skill in skills]
        if any(not name for name in names):
            raise serializers.ValidationError('Skill names cannot be blank.')
        if len(names) != len(set(names)):
            raise serializers.ValidationError('Skill names must be unique for each employee.')
        return skills

    def validate_working_days(self, value):
        if not isinstance(value, list) or any(day not in WEEKDAYS for day in value):
            raise serializers.ValidationError('Use weekday codes: mon, tue, wed, thu, fri, sat, sun.')
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Working days cannot contain duplicates.')
        return value

    def validate(self, attrs):
        start = attrs.get('shift_start_time', self.instance.shift_start_time)
        end = attrs.get('shift_end_time', self.instance.shift_end_time)
        if bool(start) != bool(end):
            raise serializers.ValidationError('Set both shift start and end times, or leave both empty.')
        if start and end and start >= end:
            raise serializers.ValidationError('Shift end must be later than shift start.')
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        skills = validated_data.pop('skills', None)
        user_fields = validated_data.pop('user', {})
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if 'availability_status' in validated_data:
            instance.is_available = validated_data['availability_status'] == RoutingAgentProfile.Availability.AVAILABLE
        elif not instance.is_available:
            instance.availability_status = RoutingAgentProfile.Availability.TEMPORARILY_UNAVAILABLE
        instance.save()
        if user_fields:
            for field, value in user_fields.items():
                setattr(instance.user, field, value)
            instance.user.save(update_fields=[*user_fields.keys()])
        if skills is not None:
            instance.skills.all().delete()
            EmployeeSkill.objects.bulk_create([
                EmployeeSkill(profile=instance, **skill) for skill in skills
            ])
        return instance


def _profile_for(user):
    profile, _ = RoutingAgentProfile.objects.get_or_create(user=user)
    return profile


def _employee_data(user):
    try:
        profile = user.routing_profile
    except RoutingAgentProfile.DoesNotExist:
        profile = RoutingAgentProfile(user=user)
    claims = Claim.objects.filter(assigned_adjuster=user)
    active_claims = claims.filter(status__in=ACTIVE_CLAIM_STATUSES).count()
    successful = claims.filter(status__in=COMPLETED_CLAIM_STATUSES)
    completed_with_timestamps = successful.filter(closed_at__isnull=False)
    processing_seconds = [
        (closed_at - submitted_at).total_seconds()
        for submitted_at, closed_at in completed_with_timestamps.values_list('submitted_at', 'closed_at')
    ]
    now = timezone.localtime()
    current_day = now.strftime('%a').lower()
    scheduled_today = not profile.working_days or current_day in profile.working_days
    within_shift = not profile.shift_start_time or not profile.shift_end_time or (
        profile.shift_start_time <= now.time() <= profile.shift_end_time
    )
    is_available = (
        user.is_active and profile.is_available
        and profile.availability_status == RoutingAgentProfile.Availability.AVAILABLE
        and scheduled_today and within_shift
    )
    eligible = is_available and active_claims < profile.max_claim_capacity
    return {
        'id': user.pk,
        'employee_id': str(user.pk),
        'name': user.get_full_name() or user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'department': user.department,
        'designation': profile.designation,
        'role': user.role,
        'years_of_experience': profile.years_of_experience,
        'employment_status': 'active' if user.is_active else 'inactive',
        'is_active': user.is_active,
        'avatar': user.avatar.url if user.avatar else None,
        'skill_tier': profile.skill_tier,
        'skills': EmployeeSkillSerializer(
            EmployeeSkill.objects.filter(profile_id=profile.pk) if profile.pk else EmployeeSkill.objects.none(), many=True
        ).data,
        'availability_status': profile.availability_status,
        'working_days': profile.working_days,
        'shift_start_time': profile.shift_start_time,
        'shift_end_time': profile.shift_end_time,
        'current_shift_status': (
            'not_configured' if not profile.working_days and not profile.shift_start_time and not profile.shift_end_time
            else 'on_shift' if scheduled_today and within_shift else 'off_shift'
        ),
        'leave_status': profile.leave_status or None,
        'active_claims': active_claims,
        'max_claim_capacity': profile.max_claim_capacity,
        'capacity_utilization': round(active_claims / profile.max_claim_capacity * 100, 1),
        'total_claims_assigned': claims.count(),
        'successfully_completed_claims': successful.count(),
        'average_processing_time_days': round(sum(processing_seconds) / len(processing_seconds) / 86400, 2) if processing_seconds else None,
        'on_time_completion_rate': None,
        'reassignment_count': None,
        'assignment_eligible': eligible,
        'assignment_ineligibility_reason': (
            None if eligible else 'At capacity' if active_claims >= profile.max_claim_capacity
            else 'Inactive employee' if not user.is_active else 'Unavailable or outside working hours'
        ),
    }


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.filter(role='employee').order_by('last_name', 'first_name', 'id')
        return Response([_employee_data(user) for user in users])


class EmployeeProfileView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember]

    def get_object(self, user_id):
        return User.objects.filter(pk=user_id, role='employee').first()

    def get(self, request, user_id):
        user = self.get_object(user_id)
        if user is None:
            return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.pk != user.pk and not IsAdmin().has_permission(request, self):
            return Response({'detail': 'You can only view your own employee profile.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(_employee_data(user))

    def patch(self, request, user_id):
        user = self.get_object(user_id)
        if user is None:
            return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        is_admin = IsAdmin().has_permission(request, self)
        if not is_admin and request.user.pk != user.pk:
            return Response({'detail': 'You can only update your own expertise.'}, status=status.HTTP_403_FORBIDDEN)
        if not is_admin and set(request.data.keys()) != {'skills'}:
            return Response({'detail': 'Employees can update only their own skills.'}, status=status.HTTP_403_FORBIDDEN)
        profile = _profile_for(user)
        if not is_admin:
            serializer = EmployeeSkillsUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            skills = serializer.validated_data['skills']
            with transaction.atomic():
                profile.skills.all().delete()
                EmployeeSkill.objects.bulk_create([
                    EmployeeSkill(profile=profile, name=skill['name'].strip(), level=skill['level'])
                    for skill in skills
                ])
            return Response(_employee_data(user))
        serializer = EmployeeProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_employee_data(user))
