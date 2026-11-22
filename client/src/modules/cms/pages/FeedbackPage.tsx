import { Badge, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedbackList } from "../api/hooks";

export default function FeedbackPage() {
  const { data, isPending, error } = useFeedbackList();

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Submitted Feedback" subtitle="Review complainant ratings and comments on resolved and closed complaints" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No feedback submitted yet</Text>
        </Card>
      )}

      <Stack gap="sm">
        {rows.map((fb) => (
          <Card key={fb.id} padding="md" withBorder>
            <Group justify="space-between" mb={4}>
              <Text fw={700}>{fb.complaint_tracking_code} — {fb.complaint_title}</Text>
              <Badge size="sm">{fb.rating} / 5</Badge>
            </Group>
            <Text size="sm">{fb.comment || "No comment provided."}</Text>
            <Text size="xs" c="dimmed" mt={4}>{fb.category_name}</Text>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
