from django.urls import path

from modules.cms.api import views

urlpatterns = [
    path("categories/", views.CategoryListCreateView.as_view(), name="cms-categories"),
    path("policy/", views.PolicyListCreateView.as_view(), name="cms-policy"),
    path("complaints/", views.ComplaintListCreateView.as_view(), name="cms-complaints"),
    path(
        "complaints/<int:pk>/",
        views.ComplaintDetailView.as_view(),
        name="cms-complaint-detail",
    ),
    path(
        "complaints/<int:pk>/handling-setup/",
        views.ComplaintHandlingSetupView.as_view(),
        name="cms-complaint-setup",
    ),
    path(
        "complaints/<int:pk>/progress/",
        views.ComplaintProgressUpdateView.as_view(),
        name="cms-complaint-progress",
    ),
    path(
        "complaints/<int:pk>/resolve/",
        views.ComplaintResolveView.as_view(),
        name="cms-complaint-resolve",
    ),
    path(
        "complaints/<int:pk>/reject/",
        views.ComplaintRejectView.as_view(),
        name="cms-complaint-reject",
    ),
    path(
        "complaints/<int:pk>/verify-close/",
        views.ComplaintVerifyCloseView.as_view(),
        name="cms-complaint-verify-close",
    ),
    path(
        "complaints/<int:pk>/escalate/",
        views.ComplaintEscalateView.as_view(),
        name="cms-complaint-escalate",
    ),
    path(
        "complaints/<int:pk>/reopen-requests/",
        views.ReopenRequestCreateView.as_view(),
        name="cms-reopen-create",
    ),
    path("reopen-requests/", views.ReopenRequestListView.as_view(), name="cms-reopen-list"),
    path(
        "reopen-requests/<int:pk>/decide/",
        views.ReopenRequestDecideView.as_view(),
        name="cms-reopen-decide",
    ),
    path(
        "complaints/<int:pk>/feedback/",
        views.FeedbackCreateView.as_view(),
        name="cms-feedback-create",
    ),
    path("feedback/", views.FeedbackListView.as_view(), name="cms-feedback-list"),
    path(
        "announcements/", views.AnnouncementListCreateView.as_view(), name="cms-announcements"
    ),
    path(
        "reports/operational/",
        views.OperationalReportView.as_view(),
        name="cms-report-operational",
    ),
    path(
        "reports/escalations/",
        views.EscalationSummaryView.as_view(),
        name="cms-report-escalations",
    ),
    path(
        "reports/analytics/", views.AnalyticsSummaryView.as_view(), name="cms-report-analytics"
    ),
]
