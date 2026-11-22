from __future__ import annotations

from rest_framework import serializers

from modules.cms.domain.state_machine import PRIORITIES
from modules.cms.models import (
    CmsPolicy,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintFeedback,
    ComplaintHistory,
    ReopenRequest,
)


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = ["id", "code", "name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]


class ComplaintCategoryCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class CmsPolicySerializer(serializers.ModelSerializer):
    routine_verification_by = serializers.CharField(read_only=True)
    escalated_verification_by = serializers.CharField(read_only=True)

    class Meta:
        model = CmsPolicy
        fields = [
            "id",
            "version",
            "effective_from",
            "is_active",
            "low_sla_hours",
            "medium_sla_hours",
            "high_sla_hours",
            "reminder_lead_hours",
            "max_attachments",
            "routine_verification_by",
            "escalated_verification_by",
            "notify_on_announcement",
            "created_by_user_id",
            "created_at",
        ]
        read_only_fields = fields


class CmsPolicyCreateSerializer(serializers.Serializer):
    low_sla_hours = serializers.IntegerField(min_value=1)
    medium_sla_hours = serializers.IntegerField(min_value=1)
    high_sla_hours = serializers.IntegerField(min_value=1)
    reminder_lead_hours = serializers.IntegerField(min_value=1)
    max_attachments = serializers.IntegerField(min_value=0, max_value=20, default=5)
    routine_verification_by = serializers.CharField(max_length=20)
    escalated_verification_by = serializers.CharField(max_length=20)
    notify_on_announcement = serializers.BooleanField(default=True)


class AttachmentInputSerializer(serializers.Serializer):
    label = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default="attachment"
    )
    url = serializers.CharField(max_length=500)


class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = ["id", "label", "url", "uploaded_by_user_id", "created_at"]
        read_only_fields = fields


class ComplaintHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintHistory
        fields = [
            "id",
            "actor_user_id",
            "actor_role",
            "event_type",
            "from_status",
            "to_status",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    complaint_tracking_code = serializers.CharField(
        source="complaint.tracking_code", read_only=True
    )
    complaint_title = serializers.CharField(source="complaint.title", read_only=True)
    category_name = serializers.CharField(source="complaint.category.name", read_only=True)

    class Meta:
        model = ComplaintFeedback
        fields = [
            "id",
            "complaint",
            "complaint_tracking_code",
            "complaint_title",
            "category_name",
            "submitted_by_user_id",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = fields


class ReopenRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    complaint_tracking_code = serializers.CharField(
        source="complaint.tracking_code", read_only=True
    )
    complaint_title = serializers.CharField(source="complaint.title", read_only=True)

    class Meta:
        model = ReopenRequest
        fields = [
            "id",
            "complaint",
            "complaint_tracking_code",
            "complaint_title",
            "requested_by_user_id",
            "reason",
            "status",
            "decided_by_user_id",
            "decision_note",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class ComplaintListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    priority = serializers.CharField(read_only=True)
    escalation_type = serializers.CharField(read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "tracking_code",
            "user_id",
            "category",
            "category_code",
            "category_name",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to_user_id",
            "assigned_unit",
            "sla_due_at",
            "is_escalated",
            "escalation_type",
            "escalated_at",
            "reopen_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ComplaintDetailSerializer(ComplaintListSerializer):
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)
    history = ComplaintHistorySerializer(many=True, read_only=True)
    feedback_entries = ComplaintFeedbackSerializer(many=True, read_only=True)
    reopen_requests = ReopenRequestSerializer(many=True, read_only=True)

    class Meta(ComplaintListSerializer.Meta):
        fields = [
            *ComplaintListSerializer.Meta.fields,
            "assigned_by_user_id",
            "assigned_at",
            "reminder_sent_at",
            "escalation_reason",
            "resolution_details",
            "resolved_at",
            "resolved_by_user_id",
            "rejection_reason",
            "rejected_at",
            "rejected_by_user_id",
            "closed_at",
            "verified_by_user_id",
            "verified_by_role",
            "last_reopened_at",
            "attachments",
            "history",
            "feedback_entries",
            "reopen_requests",
        ]
        read_only_fields = fields


class ComplaintCreateSerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    attachments = AttachmentInputSerializer(many=True, required=False, default=list)


class HandlingSetupSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=PRIORITIES)
    assigned_to_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_unit = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )


class ProgressUpdateSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000)


class ResolveComplaintSerializer(serializers.Serializer):
    resolution_details = serializers.CharField(max_length=4000)


class RejectComplaintSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=4000)


class VerifyCloseSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class EscalateComplaintSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class ReopenRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class ReopenDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "deny"])
    decision_note = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )


class FeedbackCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )


class ComplaintAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAnnouncement
        fields = [
            "id",
            "title",
            "body",
            "published_by_user_id",
            "published_by_role",
            "published_at",
            "is_active",
        ]
        read_only_fields = fields


class AnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=4000)


class OperationalReportSerializer(serializers.Serializer):
    counts = serializers.DictField(child=serializers.IntegerField())
    by_category = serializers.ListField(child=serializers.DictField())
    by_priority = serializers.ListField(child=serializers.DictField())


class EscalationSummarySerializer(serializers.Serializer):
    summary = serializers.DictField(child=serializers.IntegerField())
    escalated_by_category = serializers.ListField(child=serializers.DictField())


class AnalyticsSummarySerializer(serializers.Serializer):
    counts = serializers.DictField(child=serializers.IntegerField())
    escalations = serializers.DictField(child=serializers.IntegerField())
    by_category = serializers.ListField(child=serializers.DictField())
    by_priority = serializers.ListField(child=serializers.DictField())
    feedback = serializers.DictField()
