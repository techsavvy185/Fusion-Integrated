export interface Paginated<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface ComplaintCategory {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface CmsPolicy {
  id: number;
  version: number;
  effective_from: string;
  is_active: boolean;
  low_sla_hours: number;
  medium_sla_hours: number;
  high_sla_hours: number;
  reminder_lead_hours: number;
  max_attachments: number;
  routine_verification_by: "complainant" | "supervisor" | "either";
  escalated_verification_by: "complainant" | "supervisor" | "either";
  notify_on_announcement: boolean;
  created_by_user_id: number;
  created_at: string;
}

export interface ComplaintAttachment {
  id: number;
  label: string;
  url: string;
  uploaded_by_user_id: number;
  created_at: string;
}

export interface ComplaintHistoryItem {
  id: number;
  actor_user_id: number | null;
  actor_role: string;
  event_type: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface ComplaintFeedback {
  id: number;
  complaint: number;
  complaint_tracking_code: string;
  complaint_title: string;
  category_name: string;
  submitted_by_user_id: number;
  rating: number;
  comment: string;
  created_at: string;
}

export interface ReopenRequest {
  id: number;
  complaint: number;
  complaint_tracking_code: string;
  complaint_title: string;
  requested_by_user_id: number;
  reason: string;
  status: "pending" | "approved" | "denied";
  decided_by_user_id: number | null;
  decision_note: string;
  decided_at: string | null;
  created_at: string;
}

export interface ComplaintItem {
  id: number;
  tracking_code: string;
  user_id: number;
  category: number;
  category_code: string;
  category_name: string;
  title: string;
  description: string;
  status: "submitted" | "in_progress" | "resolved" | "rejected" | "closed";
  priority: "" | "Low" | "Medium" | "High";
  assigned_to_user_id: number | null;
  assigned_unit: string;
  sla_due_at: string | null;
  is_escalated: boolean;
  escalation_type: "" | "manual" | "automatic";
  escalated_at: string | null;
  reopen_count: number;
  created_at: string;
  updated_at: string;
}

export interface ComplaintDetail extends ComplaintItem {
  assigned_by_user_id: number | null;
  assigned_at: string | null;
  reminder_sent_at: string | null;
  escalation_reason: string;
  resolution_details: string;
  resolved_at: string | null;
  resolved_by_user_id: number | null;
  rejection_reason: string;
  rejected_at: string | null;
  rejected_by_user_id: number | null;
  closed_at: string | null;
  verified_by_user_id: number | null;
  verified_by_role: string;
  last_reopened_at: string | null;
  attachments: ComplaintAttachment[];
  history: ComplaintHistoryItem[];
  feedback_entries: ComplaintFeedback[];
  reopen_requests: ReopenRequest[];
}

export interface ComplaintAnnouncement {
  id: number;
  title: string;
  body: string;
  published_by_user_id: number;
  published_by_role: string;
  published_at: string;
  is_active: boolean;
}

export interface OperationalReport {
  counts: Record<string, number>;
  by_category: { code: string; name: string; count: number }[];
  by_priority: { priority: string; count: number }[];
}

export interface EscalationSummary {
  summary: Record<string, number>;
  escalated_by_category: { code: string; name: string; count: number }[];
}

export interface AnalyticsSummary {
  counts: Record<string, number>;
  escalations: Record<string, number>;
  by_category: { code: string; name: string; count: number }[];
  by_priority: { priority: string; count: number }[];
  feedback: { count: number; average_rating: number | null };
}
