import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useComplaints } from "../api/hooks";
import { ComplaintDetailDrawer } from "../components/ComplaintDetailDrawer";

export default function EscalationsPage() {
  const { data, isPending, error } = useComplaints({ escalated: true });
  const [selectedId, setSelectedId] = useState<number | null>(null);

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Escalated Complaints" subtitle="Supervisory oversight queue for manual and SLA-breached escalations" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No escalated complaints</Text>
        </Card>
      )}

      <Stack gap="sm">
        {rows.map((c) => (
          <Card key={c.id} padding="md" withBorder>
            <Group justify="space-between">
              <Stack gap={4}>
                <Group gap="xs">
                  <Text fw={700}>{c.tracking_code}</Text>
                  <Text fw={600}>{c.title}</Text>
                  <Badge color="red" size="sm">{c.escalation_type || "escalated"}</Badge>
                  <Badge size="sm">{c.status}</Badge>
                </Group>
                <Text size="xs" c="dimmed">{c.category_name}</Text>
              </Stack>
              <Button size="xs" variant="light" onClick={() => setSelectedId(c.id)}>Inspect</Button>
            </Group>
          </Card>
        ))}
      </Stack>

      <ComplaintDetailDrawer complaintId={selectedId} onClose={() => setSelectedId(null)} />
    </Container>
  );
}
