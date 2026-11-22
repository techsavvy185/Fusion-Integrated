import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AnalyticsSummary,
  CmsPolicy,
  ComplaintAnnouncement,
  ComplaintCategory,
  ComplaintDetail,
  ComplaintFeedback,
  ComplaintItem,
  EscalationSummary,
  OperationalReport,
  Paginated,
  ReopenRequest,
} from "./types";

export function useCategories() {
  return useQuery({
    queryKey: ["cms", "categories"],
    queryFn: async () => (await http.get<Paginated<ComplaintCategory>>("/cms/categories/")).data,
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { code: string; name: string; description?: string }) =>
      (await http.post<ComplaintCategory>("/cms/categories/", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cms", "categories"] }),
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: ["cms", "policy"],
    queryFn: async () => (await http.get<Paginated<CmsPolicy>>("/cms/policy/")).data,
  });
}

export function usePublishPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      low_sla_hours: number;
      medium_sla_hours: number;
      high_sla_hours: number;
      reminder_lead_hours: number;
      max_attachments: number;
      routine_verification_by: "complainant" | "supervisor" | "either";
      escalated_verification_by: "complainant" | "supervisor" | "either";
      notify_on_announcement: boolean;
    }) => (await http.post<CmsPolicy>("/cms/policy/", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cms", "policy"] }),
  });
}

export function useComplaints(params: { status?: string; priority?: string; escalated?: boolean; search?: string } = {}) {
  return useQuery({
    queryKey: ["cms", "complaints", params],
    queryFn: async () => (await http.get<Paginated<ComplaintItem>>("/cms/complaints/", { params })).data,
  });
}

export function useComplaintDetail(id: number | null) {
  return useQuery({
    queryKey: ["cms", "complaint", id],
    enabled: id != null,
    queryFn: async () => (await http.get<ComplaintDetail>(`/cms/complaints/${id}/`)).data,
  });
}

export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      category_id: number;
      title: string;
      description: string;
      attachments?: { label?: string; url: string }[];
    }) => (await http.post<ComplaintDetail>("/cms/complaints/", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cms", "complaints"] }),
  });
}

export function useHandlingSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      id: number;
      category_id?: number;
      priority: "Low" | "Medium" | "High";
      assigned_to_user_id?: number | null;
      assigned_unit?: string;
    }) => {
      const { id, ...body } = payload;
      return (await http.post<ComplaintDetail>(`/cms/complaints/${id}/handling-setup/`, body)).data;
    },
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useProgressUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; note: string }) =>
      (await http.post<ComplaintDetail>(`/cms/complaints/${payload.id}/progress/`, { note: payload.note })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useResolveComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; resolution_details: string }) =>
      (await http.post<ComplaintDetail>(`/cms/complaints/${payload.id}/resolve/`, {
        resolution_details: payload.resolution_details,
      })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useRejectComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; rejection_reason: string }) =>
      (await http.post<ComplaintDetail>(`/cms/complaints/${payload.id}/reject/`, {
        rejection_reason: payload.rejection_reason,
      })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useVerifyCloseComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; note?: string }) =>
      (await http.post<ComplaintDetail>(`/cms/complaints/${payload.id}/verify-close/`, {
        note: payload.note ?? "",
      })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useEscalateComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; reason: string }) =>
      (await http.post<ComplaintDetail>(`/cms/complaints/${payload.id}/escalate/`, { reason: payload.reason })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
    },
  });
}

export function useRequestReopen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; reason: string }) =>
      (await http.post<ReopenRequest>(`/cms/complaints/${payload.id}/reopen-requests/`, { reason: payload.reason })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
      qc.invalidateQueries({ queryKey: ["cms", "reopen-requests"] });
    },
  });
}

export function useReopenRequests(statusFilter?: string) {
  return useQuery({
    queryKey: ["cms", "reopen-requests", statusFilter ?? ""],
    queryFn: async () =>
      (await http.get<Paginated<ReopenRequest>>("/cms/reopen-requests/", {
        params: statusFilter ? { status: statusFilter } : {},
      })).data,
  });
}

export function useDecideReopen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; decision: "approve" | "deny"; decision_note?: string }) =>
      (await http.post<ReopenRequest>(`/cms/reopen-requests/${payload.id}/decide/`, {
        decision: payload.decision,
        decision_note: payload.decision_note ?? "",
      })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cms", "reopen-requests"] });
      qc.invalidateQueries({ queryKey: ["cms", "complaints"] });
    },
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: number; rating: number; comment?: string }) =>
      (await http.post<ComplaintFeedback>(`/cms/complaints/${payload.id}/feedback/`, {
        rating: payload.rating,
        comment: payload.comment ?? "",
      })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["cms", "complaint", vars.id] });
      qc.invalidateQueries({ queryKey: ["cms", "feedback"] });
    },
  });
}

export function useFeedbackList() {
  return useQuery({
    queryKey: ["cms", "feedback"],
    queryFn: async () => (await http.get<Paginated<ComplaintFeedback>>("/cms/feedback/")).data,
  });
}

export function useAnnouncements() {
  return useQuery({
    queryKey: ["cms", "announcements"],
    queryFn: async () => (await http.get<Paginated<ComplaintAnnouncement>>("/cms/announcements/")).data,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { title: string; body: string }) =>
      (await http.post<ComplaintAnnouncement>("/cms/announcements/", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cms", "announcements"] }),
  });
}

export function useOperationalReport(enabled: boolean) {
  return useQuery({
    queryKey: ["cms", "reports", "operational"],
    enabled,
    queryFn: async () => (await http.get<OperationalReport>("/cms/reports/operational/")).data,
  });
}

export function useEscalationSummary(enabled: boolean) {
  return useQuery({
    queryKey: ["cms", "reports", "escalations"],
    enabled,
    queryFn: async () => (await http.get<EscalationSummary>("/cms/reports/escalations/")).data,
  });
}

export function useAnalyticsSummary(enabled: boolean) {
  return useQuery({
    queryKey: ["cms", "reports", "analytics"],
    enabled,
    queryFn: async () => (await http.get<AnalyticsSummary>("/cms/reports/analytics/")).data,
  });
}
