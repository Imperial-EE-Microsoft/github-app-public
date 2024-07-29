from django.urls import path
from .views import *


urlpatterns = [
    path("init/", translate_init, name="dashboard-status"),
    path('repos/', dashboard_get_repos, name='dashboard_get_repos'),
    path('repos/monitor/<int:repo_id>/true/', set_monitoring_true, name='set_monitoring_true'),
    path('repos/monitor/<int:repo_id>/false/', set_monitoring_false, name='set_monitoring_false'),
    path("translate/", translate_endpoint, name="translate_markdown"),
]
