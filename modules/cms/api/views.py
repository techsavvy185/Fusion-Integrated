from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.cms.api import serializers as s
from modules.cms.api.permissions import HasAnyPermission
from modules.cms.domain.state_machine import PRIORITIES, STATUSES
from modules.cms.models import CmsPolicy
from modules.cms.selectors import reports as report_selectors
from modules.cms.selectors import scoping
from modules.cms.services import (
    announcements as announcement_service,
)
from modules.cms.services import (
    complaints as complaint_service,
)
from modules.cms.services import (
    escalation as escalation_service,
)
from modules.cms.services import (
    feedback as feedback_service,
)
from modules.cms.services import (
    handling as handling_service,
)
from modules.cms.services import (
    policy as policy_service,
)
from modules.cms.services import (
    reopening as reopening_service,
)
from modules.cms.services import (
    transitions as transition_service,
)

MODULE = HasModuleGrant("cms")


def _actor(request):
    return getattr(request, "principal", None)


def _bool_param(params, name: str) -> bool | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    low = str(raw).strip().lower()
    if low in ("true", "1", "yes"):
        return True
    if low in ("false", "0", "no"):
        return False
    raise BadRequestError(f"{name} must be true or false.", code="invalid_filter")


def _int_param(params, name: str) -> int | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(
            f"{name} must be a whole number.", code="invalid_filter"
        ) from exc


def _scoped_complaint(actor, pk: int):
    complaint = (
        scoping.complaints_for(actor)
        .prefetch_related("attachments", "history", "feedback_entries", "reopen_requests")
        .filter(pk=pk)
        .first()
    )
    if complaint is None:
        raise NotFoundError("Complaint not found.", code="complaint_not_found")
    return complaint


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = s.ComplaintCategorySerializer
    throttle_scope = "cms_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("cms.policy.manage")()]
        return [MODULE(), HasAnyPermission("cms.complaint.view", "cms.policy.manage")()]

    def get_queryset(self):
        include_inactive = _bool_param(self.request.query_params, "include_inactive") or False
        return scoping.categories_for(_actor(self.request), include_inactive=include_inactive)

    @extend_schema(responses={200: s.ComplaintCategorySerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.ComplaintCategoryCreateSerializer,
        responses={201: s.ComplaintCategorySerializer},
        examples=[
            OpenApiExample(
                "Category",
                value={
                    "code": "NET",
                    "name": "Network & Wi-Fi",
                    "description": "Campus network",
                },
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        inp = s.ComplaintCategoryCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        cat = policy_service.create_category(**inp.validated_data)
        return Response(
            s.ComplaintCategorySerializer(cat).data, status=status.HTTP_201_CREATED
        )


class PolicyListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission("cms.policy.manage")]
    serializer_class = s.CmsPolicySerializer
    throttle_scope = "cms_write"

    def get_queryset(self):
        return CmsPolicy.objects.order_by("-version")

    @extend_schema(responses={200: s.CmsPolicySerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.CmsPolicyCreateSerializer,
        responses={201: s.CmsPolicySerializer},
        examples=[
            OpenApiExample(
                "Policy",
                value={
                    "low_sla_hours": 72,
                    "medium_sla_hours": 48,
                    "high_sla_hours": 24,
                    "reminder_lead_hours": 4,
                    "max_attachments": 5,
                    "routine_verification_by": "complainant",
                    "escalated_verification_by": "supervisor",
                    "notify_on_announcement": True,
                },
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        inp = s.CmsPolicyCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        pol = policy_service.publish_policy(
            actor_user_id=_actor(request).user_id, **inp.validated_data
        )
        return Response(s.CmsPolicySerializer(pol).data, status=status.HTTP_201_CREATED)


class ComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = s.ComplaintListSerializer
    throttle_scope = "cms_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("cms.complaint.create")()]
        return [MODULE(), HasPermission("cms.complaint.view")()]

    def get_queryset(self):
        qs = scoping.complaints_for(_actor(self.request))
        params = self.request.query_params

        st = params.get("status")
        if st:
            if st not in STATUSES:
                raise BadRequestError(f"Unknown status filter {st!r}.", code="invalid_filter")
            qs = qs.filter(status=st)

        pr = params.get("priority")
        if pr:
            if pr not in PRIORITIES:
                raise BadRequestError(
                    f"Unknown priority filter {pr!r}.", code="invalid_filter"
                )
            qs = qs.filter(priority=pr)

        esc = _bool_param(params, "escalated")
        if esc is not None:
            qs = qs.filter(is_escalated=esc)

        cat_id = _int_param(params, "category_id")
        if cat_id is not None:
            qs = qs.filter(category_id=cat_id)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(tracking_code__icontains=search) | Q(title__icontains=search))
        return qs

    @extend_schema(responses={200: s.ComplaintListSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.ComplaintCreateSerializer,
        responses={201: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample(
                "Submit Complaint",
                value={
                    "category_id": 1,
                    "title": "Wi-Fi down in Hall 3",
                    "description": "No connectivity since morning.",
                    "attachments": [],
                },
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        inp = s.ComplaintCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        complaint = complaint_service.submit_complaint(
            actor=_actor(request), **inp.validated_data
        )
        detail = _scoped_complaint(_actor(request), complaint.id)
        return Response(
            s.ComplaintDetailSerializer(detail).data, status=status.HTTP_201_CREATED
        )


class ComplaintDetailView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.view")]

    @extend_schema(responses={200: s.ComplaintDetailSerializer})
    def get(self, request, pk: int):
        complaint = _scoped_complaint(_actor(request), pk)
        return Response(s.ComplaintDetailSerializer(complaint).data)


class ComplaintHandlingSetupView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.assign")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.HandlingSetupSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample(
                "Setup", value={"priority": "High", "assigned_unit": "Network Section"}
            )
        ],
    )
    def post(self, request, pk: int):
        inp = s.HandlingSetupSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        handling_service.setup_complaint_handling(
            actor=_actor(request),
            complaint_id=pk,
            category_id=inp.validated_data.get("category_id"),
            priority=inp.validated_data["priority"],
            assigned_to_user_id=inp.validated_data.get("assigned_to_user_id"),
            assigned_unit=inp.validated_data.get("assigned_unit", ""),
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ComplaintProgressUpdateView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.update")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.ProgressUpdateSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample("Progress", value={"note": "Technician inspected the switch."})
        ],
    )
    def post(self, request, pk: int):
        inp = s.ProgressUpdateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        handling_service.record_progress_update(
            actor=_actor(request), complaint_id=pk, note=inp.validated_data["note"]
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ComplaintResolveView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.update")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.ResolveComplaintSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample(
                "Resolve", value={"resolution_details": "Replaced faulty access point."}
            )
        ],
    )
    def post(self, request, pk: int):
        inp = s.ResolveComplaintSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        transition_service.resolve_complaint(
            actor=_actor(request),
            complaint_id=pk,
            resolution_details=inp.validated_data["resolution_details"],
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ComplaintRejectView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.update")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.RejectComplaintSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample(
                "Reject", value={"rejection_reason": "Duplicate of an already active ticket."}
            )
        ],
    )
    def post(self, request, pk: int):
        inp = s.RejectComplaintSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        transition_service.reject_complaint(
            actor=_actor(request),
            complaint_id=pk,
            rejection_reason=inp.validated_data["rejection_reason"],
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ComplaintVerifyCloseView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.approve")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.VerifyCloseSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[OpenApiExample("Verify Close", value={"note": "Confirmed working."})],
    )
    def post(self, request, pk: int):
        inp = s.VerifyCloseSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        transition_service.verify_and_close_complaint(
            actor=_actor(request),
            complaint_id=pk,
            note=inp.validated_data.get("note", ""),
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ComplaintEscalateView(APIView):
    permission_classes = [MODULE, HasPermission("cms.complaint.update")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.EscalateComplaintSerializer,
        responses={200: s.ComplaintDetailSerializer},
        examples=[
            OpenApiExample(
                "Escalate",
                value={"reason": "Requires supervisory approval for vendor replacement."},
            )
        ],
    )
    def post(self, request, pk: int):
        inp = s.EscalateComplaintSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        escalation_service.escalate_manually(
            actor=_actor(request),
            complaint_id=pk,
            reason=inp.validated_data["reason"],
        )
        return Response(
            s.ComplaintDetailSerializer(_scoped_complaint(_actor(request), pk)).data
        )


class ReopenRequestCreateView(APIView):
    permission_classes = [MODULE, HasPermission("cms.reopen_request.create")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.ReopenRequestCreateSerializer,
        responses={201: s.ReopenRequestSerializer},
        examples=[
            OpenApiExample("Reopen", value={"reason": "Issue recurred within 24 hours."})
        ],
    )
    def post(self, request, pk: int):
        inp = s.ReopenRequestCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        req = reopening_service.request_reopening(
            actor=_actor(request),
            complaint_id=pk,
            reason=inp.validated_data["reason"],
        )
        return Response(s.ReopenRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class ReopenRequestListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("cms.reopen_request.approve")]
    serializer_class = s.ReopenRequestSerializer

    def get_queryset(self):
        qs = scoping.reopen_requests_for(_actor(self.request))
        st = self.request.query_params.get("status")
        if st:
            if st not in ("pending", "approved", "denied"):
                raise BadRequestError(
                    f"Unknown reopen status filter {st!r}.", code="invalid_filter"
                )
            qs = qs.filter(status=st)
        return qs

    @extend_schema(responses={200: s.ReopenRequestSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ReopenRequestDecideView(APIView):
    permission_classes = [MODULE, HasPermission("cms.reopen_request.approve")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.ReopenDecisionSerializer,
        responses={200: s.ReopenRequestSerializer},
        examples=[
            OpenApiExample(
                "Decide",
                value={"decision": "approve", "decision_note": "Confirmed recurrence."},
            )
        ],
    )
    def post(self, request, pk: int):
        inp = s.ReopenDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        req = reopening_service.decide_reopening(
            actor=_actor(request),
            request_id=pk,
            decision=inp.validated_data["decision"],
            decision_note=inp.validated_data.get("decision_note", ""),
        )
        return Response(s.ReopenRequestSerializer(req).data)


class FeedbackCreateView(APIView):
    permission_classes = [MODULE, HasPermission("cms.feedback.create")]
    throttle_scope = "cms_write"

    @extend_schema(
        request=s.FeedbackCreateSerializer,
        responses={201: s.ComplaintFeedbackSerializer},
        examples=[
            OpenApiExample("Feedback", value={"rating": 5, "comment": "Resolved quickly."})
        ],
    )
    def post(self, request, pk: int):
        inp = s.FeedbackCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        fb = feedback_service.submit_feedback(
            actor=_actor(request),
            complaint_id=pk,
            rating=inp.validated_data["rating"],
            comment=inp.validated_data.get("comment", ""),
        )
        return Response(s.ComplaintFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)


class FeedbackListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("cms.feedback.review")]
    serializer_class = s.ComplaintFeedbackSerializer

    def get_queryset(self):
        return scoping.feedback_for(_actor(self.request))

    @extend_schema(responses={200: s.ComplaintFeedbackSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AnnouncementListCreateView(generics.ListCreateAPIView):
    serializer_class = s.ComplaintAnnouncementSerializer
    throttle_scope = "cms_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("cms.announcement.publish")()]
        return [MODULE(), HasPermission("cms.announcement.view")()]

    def get_queryset(self):
        return scoping.announcements_for(_actor(self.request))

    @extend_schema(responses={200: s.ComplaintAnnouncementSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.AnnouncementCreateSerializer,
        responses={201: s.ComplaintAnnouncementSerializer},
        examples=[
            OpenApiExample(
                "Announcement",
                value={"title": "Planned maintenance", "body": "Water supply paused 2-4 PM."},
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        inp = s.AnnouncementCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        ann = announcement_service.publish_announcement(
            actor=_actor(request), **inp.validated_data
        )
        return Response(
            s.ComplaintAnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED
        )


class OperationalReportView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("cms.report.view"),
        HasPermission("cms.complaint.update"),
    ]

    @extend_schema(responses={200: s.OperationalReportSerializer})
    def get(self, request):
        return Response(
            s.OperationalReportSerializer(report_selectors.operational_report()).data
        )


class EscalationSummaryView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("cms.report.view"),
        HasPermission("cms.escalation.view"),
    ]

    @extend_schema(responses={200: s.EscalationSummarySerializer})
    def get(self, request):
        return Response(
            s.EscalationSummarySerializer(report_selectors.escalation_summary()).data
        )


class AnalyticsSummaryView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("cms.report.view"),
        HasPermission("cms.policy.manage"),
    ]

    @extend_schema(responses={200: s.AnalyticsSummarySerializer})
    def get(self, request):
        return Response(
            s.AnalyticsSummarySerializer(report_selectors.analytics_summary()).data
        )
