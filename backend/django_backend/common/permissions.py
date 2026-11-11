from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'role', None) == 'admin' or request.user.is_staff_member:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'customer'):
            customer = obj.customer
            if customer == request.user:
                return True
            if hasattr(customer, 'user'):
                return customer.user == request.user
        return False


class IsStaffMember(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff_member


class IsEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['employee', 'admin']


class CanIssuePolicy(permissions.BasePermission):
    """Customers can issue records for themselves; employees/admins can act for a customer."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['customer', 'employee', 'admin']


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'
