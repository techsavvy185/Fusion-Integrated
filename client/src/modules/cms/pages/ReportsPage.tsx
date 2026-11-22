import { Card, Container, SimpleGrid, Stack, Text } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnalyticsSummary, useEscalationSummary, useOperationalReport } from "../api/hooks";

export default function ReportsPage() {
  const { can } = useAuth();
  const isHandler = can("cms.complaint.update");
  const isSupervisor = can("cms.escalation.view");
  const isAdmin = can("cms.policy.manage");

  const op = useOperationalReport(isHandler);
  const esc = useEscalationSummary(isSupervisor);
  const ana = useAnalyticsSummary(isAdmin);

  const error = op.error || esc.error || ana.error;
  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const isPending = (isHandler && op.isPending) || (isSupervisor && esc.isPending) || (isAdmin && ana.isPending);
  const hasAny = Boolean(op.data || esc.data || ana.data);

  return (
    <Container size="md">
      <PageHeader title="Reports & Analytics" subtitle="Role-scoped CMS operational reports, escalation summaries, and analytics" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && !hasAny && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No report data available for this role</Text>
        </Card>
      )}

      <Stack gap="md">
        {op.data && (
          <Card padding="md" withBorder>
            <Text fw={700} mb="sm">Operational Report</Text>
            <SimpleGrid cols={3}>
              {Object.entries(op.data.counts).map(([k, v]) => (
                <Text key={k} size="sm">{k}: <strong>{v}</strong></Text>
              ))}
            </SimpleGrid>
          </Card>
        )}

        {esc.data && (
          <Card padding="md" withBorder>
            <Text fw={700} mb="sm">Escalation Summary</Text>
            <SimpleGrid cols={3}>
              {Object.entries(esc.data.summary).map(([k, v]) => (
                <Text key={k} size="sm">{k}: <strong>{v}</strong></Text>
              ))}
            </SimpleGrid>
          </Card>
        )}

        {ana.data && (
          <Card padding="md" withBorder>
            <Text fw={700} mb="sm">CMS Analytics</Text>
            <SimpleGrid cols={3}>
              {Object.entries(ana.data.counts).map(([k, v]) => (
                <Text key={k} size="sm">{k}: <strong>{v}</strong></Text>
              ))}
            </SimpleGrid>
            <Text size="sm" mt="sm">
              Feedback submissions: <strong>{ana.data.feedback.count}</strong> · Average rating: <strong>{ana.data.feedback.average_rating ?? "N/A"}</strong>
            </Text>
          </Card>
        )}
      </Stack>
    </Container>
  );
}
