import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideReopen, useReopenRequests } from "../api/hooks";
import type { ReopenRequest } from "../api/types";

export default function ReopenRequestsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useReopenRequests();
  const decide = useDecideReopen();
  const [activeReq, setActiveReq] = useState<{ req: ReopenRequest; decision: "approve" | "deny" } | null>(null);
  const [note, setNote] = useState("");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];
  const canDecide = can("cms.reopen_request.approve");

  return (
    <Container size="md">
      <PageHeader title="Reopen Requests" subtitle="Review complainant reopening requests for closed complaints" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No reopen requests</Text>
        </Card>
      )}

      <Stack gap="sm">
        {rows.map((req) => (
          <Card key={req.id} padding="md" withBorder>
            <Group justify="space-between" align="flex-start">
              <Stack gap={4}>
                <Group gap="xs">
                  <Text fw={700}>{req.complaint_tracking_code}</Text>
                  <Text fw={600}>{req.complaint_title}</Text>
                  <Badge size="sm">{req.status}</Badge>
                </Group>
                <Text size="sm">{req.reason}</Text>
                {req.decision_note && <Text size="xs" c="dimmed">Decision note: {req.decision_note}</Text>}
              </Stack>
              {canDecide && req.status === "pending" && (
                <Group gap="xs">
                  <Button size="xs" color="green" onClick={() => { setActiveReq({ req, decision: "approve" }); setNote(""); }}>Approve</Button>
                  <Button size="xs" color="red" variant="outline" onClick={() => { setActiveReq({ req, decision: "deny" }); setNote(""); }}>Deny</Button>
                </Group>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      <FormModal
        opened={activeReq != null}
        onClose={() => setActiveReq(null)}
        title={activeReq?.decision === "approve" ? "Approve reopening" : "Deny reopening"}
        submitLabel={activeReq?.decision === "approve" ? "Approve" : "Deny"}
        danger={activeReq?.decision === "deny"}
        submitting={decide.isPending}
        error={decide.error}
        onSubmit={() => activeReq && decide.mutate(
          { id: activeReq.req.id, decision: activeReq.decision, decision_note: note },
          {
            onSuccess: () => {
              notifications.show({ color: "green", title: "Recorded", message: `Reopening request ${activeReq.decision}d.` });
              setActiveReq(null);
            },
            onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
          },
        )}
      >
        <Textarea label="Decision note" value={note} onChange={(e) => setNote(e.currentTarget.value)} minRows={3} />
      </FormModal>
    </Container>
  );
}
