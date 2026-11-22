import { useState } from "react";
import {
  Anchor, Badge, Button, Divider, Drawer, Group, NumberInput, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useCategories,
  useComplaintDetail,
  useEscalateComplaint,
  useHandlingSetup,
  useProgressUpdate,
  useRejectComplaint,
  useRequestReopen,
  useResolveComplaint,
  useSubmitFeedback,
  useVerifyCloseComplaint,
} from "../api/hooks";

export function ComplaintDetailDrawer({ complaintId, onClose }: { complaintId: number | null; onClose: () => void }) {
  const { can } = useAuth();
  const { data, isPending, error } = useComplaintDetail(complaintId);
  const { data: categoriesData } = useCategories();

  const setup = useHandlingSetup();
  const progress = useProgressUpdate();
  const resolve = useResolveComplaint();
  const reject = useRejectComplaint();
  const verifyClose = useVerifyCloseComplaint();
  const escalate = useEscalateComplaint();
  const reopen = useRequestReopen();
  const feedback = useSubmitFeedback();

  const [priority, setPriority] = useState<"Low" | "Medium" | "High">("Medium");
  const [unit, setUnit] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [resolutionDetails, setResolutionDetails] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [escalationReason, setEscalationReason] = useState("");
  const [reopenReason, setReopenReason] = useState("");
  const [rating, setRating] = useState<number>(5);
  const [fbComment, setFbComment] = useState("");

  const notifyOk = (title: string, message: string) => notifications.show({ color: "green", title, message });
  const notifyErr = (e: unknown) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) });

  const categories = (categoriesData?.results ?? []).map((c) => ({ value: String(c.id), label: `${c.code} — ${c.name}` }));

  return (
    <Drawer opened={complaintId != null} onClose={onClose} title={data ? `${data.tracking_code}: ${data.title}` : "Complaint detail"} position="right" size="lg">
      {isPending && <Text c="dimmed">Loading…</Text>}
      {error && <ErrorState error={error} />}
      {data && (
        <Stack gap="md">
          <Group gap="xs">
            <Badge>{data.status}</Badge>
            {data.priority && <Badge variant="light">{data.priority}</Badge>}
            {data.is_escalated && <Badge color="red">Escalated ({data.escalation_type})</Badge>}
          </Group>
          <Text size="sm">{data.description}</Text>
          <Text size="xs" c="dimmed">
            Category: {data.category_name} · Unit: {data.assigned_unit || "Unassigned"} · SLA due: {data.sla_due_at ? new Date(data.sla_due_at).toLocaleString() : "Not set"}
          </Text>

          {data.attachments.length > 0 && (
            <Stack gap={4}>
              <Text fw={600} size="sm">Attachments</Text>
              {data.attachments.map((att) => (
                <Anchor key={att.id} href={att.url} target="_blank" rel="noreferrer" size="sm">{att.label}</Anchor>
              ))}
            </Stack>
          )}

          {can("cms.complaint.assign") && (data.status === "submitted" || data.status === "in_progress") && (
            <Stack gap="xs">
              <Divider label="Handling setup" />
              <Select label="Category" data={categories} value={categoryId ?? String(data.category)} onChange={setCategoryId} />
              <Select label="Priority" data={["Low", "Medium", "High"]} value={priority} onChange={(v) => v && setPriority(v as "Low" | "Medium" | "High")} />
              <TextInput label="Assigned unit" value={unit} onChange={(e) => setUnit(e.currentTarget.value)} placeholder="e.g. Network Section" />
              <Button
                loading={setup.isPending}
                onClick={() => setup.mutate(
                  { id: data.id, category_id: Number(categoryId ?? data.category), priority, assigned_unit: unit },
                  { onSuccess: () => notifyOk("Saved", "Handling setup updated."), onError: notifyErr },
                )}
              >
                Save handling setup
              </Button>
            </Stack>
          )}

          {can("cms.complaint.update") && (data.status === "submitted" || data.status === "in_progress") && (
            <Stack gap="xs">
              <Divider label="Handler actions" />
              <Textarea label="Progress note" value={note} onChange={(e) => setNote(e.currentTarget.value)} />
              <Button
                variant="light" loading={progress.isPending} disabled={!note.trim()}
                onClick={() => progress.mutate({ id: data.id, note }, { onSuccess: () => { setNote(""); notifyOk("Updated", "Progress recorded."); }, onError: notifyErr })}
              >
                Add progress update
              </Button>

              <Textarea label="Resolution details" value={resolutionDetails} onChange={(e) => setResolutionDetails(e.currentTarget.value)} />
              <Button
                color="green" loading={resolve.isPending} disabled={!resolutionDetails.trim()}
                onClick={() => resolve.mutate({ id: data.id, resolution_details: resolutionDetails }, { onSuccess: () => { setResolutionDetails(""); notifyOk("Resolved", "Complaint marked resolved."); }, onError: notifyErr })}
              >
                Resolve complaint
              </Button>

              <Textarea label="Rejection reason" value={rejectionReason} onChange={(e) => setRejectionReason(e.currentTarget.value)} />
              <Button
                color="red" variant="outline" loading={reject.isPending} disabled={!rejectionReason.trim()}
                onClick={() => reject.mutate({ id: data.id, rejection_reason: rejectionReason }, { onSuccess: () => { setRejectionReason(""); notifyOk("Rejected", "Complaint rejected."); }, onError: notifyErr })}
              >
                Reject complaint
              </Button>

              {!data.is_escalated && (
                <>
                  <Textarea label="Escalation reason" value={escalationReason} onChange={(e) => setEscalationReason(e.currentTarget.value)} />
                  <Button
                    color="orange" loading={escalate.isPending} disabled={!escalationReason.trim()}
                    onClick={() => escalate.mutate({ id: data.id, reason: escalationReason }, { onSuccess: () => { setEscalationReason(""); notifyOk("Escalated", "Complaint escalated to supervisor."); }, onError: notifyErr })}
                  >
                    Escalate complaint
                  </Button>
                </>
              )}
            </Stack>
          )}

          {can("cms.complaint.approve") && data.status === "resolved" && (
            <Stack gap="xs">
              <Divider label="Closure verification" />
              <Button
                color="teal" loading={verifyClose.isPending}
                onClick={() => verifyClose.mutate({ id: data.id, note: "Verified in CMS" }, { onSuccess: () => notifyOk("Closed", "Complaint verified and closed."), onError: notifyErr })}
              >
                Verify and close
              </Button>
            </Stack>
          )}

          {can("cms.reopen_request.create") && data.status === "closed" && (
            <Stack gap="xs">
              <Divider label="Request reopening" />
              <Textarea label="Reopen reason" value={reopenReason} onChange={(e) => setReopenReason(e.currentTarget.value)} />
              <Button
                loading={reopen.isPending} disabled={!reopenReason.trim()}
                onClick={() => reopen.mutate({ id: data.id, reason: reopenReason }, { onSuccess: () => { setReopenReason(""); notifyOk("Requested", "Reopening request submitted."); }, onError: notifyErr })}
              >
                Submit reopen request
              </Button>
            </Stack>
          )}

          {can("cms.feedback.create") && (data.status === "resolved" || data.status === "closed") && data.feedback_entries.length === 0 && (
            <Stack gap="xs">
              <Divider label="Submit feedback" />
              <NumberInput label="Rating (1-5)" min={1} max={5} value={rating} onChange={(v) => setRating(Number(v) || 5)} />
              <Textarea label="Feedback comment" value={fbComment} onChange={(e) => setFbComment(e.currentTarget.value)} />
              <Button
                loading={feedback.isPending}
                onClick={() => feedback.mutate({ id: data.id, rating, comment: fbComment }, { onSuccess: () => { setFbComment(""); notifyOk("Submitted", "Thank you for your feedback."); }, onError: notifyErr })}
              >
                Submit feedback
              </Button>
            </Stack>
          )}

          <Divider label="History" />
          <Stack gap={6}>
            {data.history.map((h) => (
              <Text key={h.id} size="xs">
                <strong>{h.event_type}</strong> ({h.actor_role}) — {h.note || `${h.from_status} -> ${h.to_status}`}
              </Text>
            ))}
          </Stack>
        </Stack>
      )}
    </Drawer>
  );
}
