from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import CharField, Q
from django.db.models.functions import Cast

from apps.accounts.models import Role
from common.permissions import IsStaffMember
from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['entity_type', 'entity_id', 'action', 'actor']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        user = self.request.user
        queryset = AuditEvent.objects.select_related('actor')
        if user.role == Role.ADMIN:
            return queryset
        if user.role == Role.EMPLOYEE:
            # Employees can inspect audits related to claims/policies they service;
            # investigator work stays restricted to the assigned investigator.
            claim_ids = user.assigned_claims.values_list('pk', flat=True)
            claim_audit_ids = user.assigned_claims.annotate(audit_id=Cast('pk', CharField())).values_list('audit_id', flat=True)
            policy_ids = user.managed_policies.annotate(audit_id=Cast('pk', CharField())).values_list('audit_id', flat=True)
            from apps.settlements.models import Settlement
            settlement_ids = Settlement.objects.filter(claim_id__in=claim_ids).annotate(
                audit_id=Cast('pk', CharField())
            ).values_list('audit_id', flat=True)
            return queryset.filter(
                Q(entity_type='claims.claim', entity_id__in=claim_audit_ids)
                | Q(entity_type='policies.policy', entity_id__in=policy_ids)
                | Q(entity_type='settlements.settlement', entity_id__in=settlement_ids)
            )
        if user.role == Role.INVESTIGATOR:
            claim_ids = user.investigated_claims.values_list('pk', flat=True)
            claim_audit_ids = user.investigated_claims.annotate(audit_id=Cast('pk', CharField())).values_list('audit_id', flat=True)
            investigation_ids = user.investigations.annotate(audit_id=Cast('pk', CharField())).values_list('audit_id', flat=True)
            from apps.settlements.models import Settlement
            settlement_ids = Settlement.objects.filter(claim_id__in=claim_ids).annotate(
                audit_id=Cast('pk', CharField())
            ).values_list('audit_id', flat=True)
            return queryset.filter(
                Q(entity_type='claims.claim', entity_id__in=claim_audit_ids)
                | Q(entity_type='investigations.investigation', entity_id__in=investigation_ids)
                | Q(entity_type='settlements.settlement', entity_id__in=settlement_ids)
            )
        return queryset.none()
