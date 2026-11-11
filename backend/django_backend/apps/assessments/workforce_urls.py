from django.urls import path

from .workforce import EmployeeListView, EmployeeProfileView

urlpatterns = [
    path('employees/', EmployeeListView.as_view(), name='workforce-employees'),
    path('employees/<int:user_id>/', EmployeeProfileView.as_view(), name='workforce-employee-profile'),
]
