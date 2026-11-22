import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Switch, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCategories, useCreateCategory, usePolicies, usePublishPolicy } from "../api/hooks";

export default function PolicyPage() {
  const { can } = useAuth();
  const { data, isPending, error } = usePolicies();
  const { data: catData } = useCategories();
  const publish = usePublishPolicy();
  const createCat = useCreateCategory();

  const [policyOpen, setPolicyOpen] = useState(false);
  const [catOpen, setCatOpen] = useState(false);

  const [lowHours, setLowHours] = useState(72);
  const [medHours, setMedHours] = useState(48);
  const [highHours, setHighHours] = useState(24);
  const [leadHours, setLeadHours] = useState(4);
  const [maxAtt, setMaxAtt] = useState(5);
  const [routineVer, setRoutineVer] = useState<"complainant" | "supervisor" | "either">("complainant");
  const [escVer, setEscVer] = useState<"complainant" | "supervisor" | "either">("supervisor");
  const [notifyAnn, setNotifyAnn] = useState(true);

  const [catCode, setCatCode] = useState("");
  const [catName, setCatName] = useState("");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const policies = data?.results ?? [];
  const categories = catData?.results ?? [];
  const canManage = can("cms.policy.manage");

  return (
    <Container size="md">
      <PageHeader
        title="CMS Policy & Categories"
        subtitle="Effective-dated SLA durations, attachment limits, verification rules, and categories"
        action={canManage && (
          <Group gap="xs">
            <Button variant="light" onClick={() => setCatOpen(true)}>Add category</Button>
            <Button onClick={() => setPolicyOpen(true)}>Publish policy version</Button>
          </Group>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && policies.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No CMS policy configured yet</Text>
        </Card>
      )}

      <Stack gap="sm" mb="lg">
        {policies.map((p) => (
          <Card key={p.id} padding="md" withBorder>
            <Group justify="space-between">
              <Text fw={700}>Version {p.version}</Text>
              <Badge color={p.is_active ? "green" : "gray"}>{p.is_active ? "Active" : "Superseded"}</Badge>
            </Group>
            <Text size="sm" mt={4}>
              SLA (Low/Med/High): {p.low_sla_hours}h / {p.medium_sla_hours}h / {p.high_sla_hours}h · Reminder lead: {p.reminder_lead_hours}h · Max attachments: {p.max_attachments}
            </Text>
          </Card>
        ))}
      </Stack>

      <Text fw={700} mb="xs">Categories ({categories.length})</Text>
      <Stack gap="xs">
        {categories.map((c) => (
          <Card key={c.id} padding="sm" withBorder>
            <Text size="sm"><strong>{c.code}</strong> — {c.name}</Text>
          </Card>
        ))}
      </Stack>

      <FormModal
        opened={policyOpen}
        onClose={() => setPolicyOpen(false)}
        title="Publish new CMS policy version"
        submitLabel="Publish"
        submitting={publish.isPending}
        error={publish.error}
        onSubmit={() => publish.mutate(
          {
            low_sla_hours: lowHours,
            medium_sla_hours: medHours,
            high_sla_hours: highHours,
            reminder_lead_hours: leadHours,
            max_attachments: maxAtt,
            routine_verification_by: routineVer,
            escalated_verification_by: escVer,
            notify_on_announcement: notifyAnn,
          },
          {
            onSuccess: (p) => {
              notifications.show({ color: "green", title: "Published", message: `Policy v${p.version} is active.` });
              setPolicyOpen(false);
            },
          },
        )}
      >
        <Stack gap="sm">
          <NumberInput label="Low SLA hours" min={1} value={lowHours} onChange={(v) => setLowHours(Number(v) || 1)} />
          <NumberInput label="Medium SLA hours" min={1} value={medHours} onChange={(v) => setMedHours(Number(v) || 1)} />
          <NumberInput label="High SLA hours" min={1} value={highHours} onChange={(v) => setHighHours(Number(v) || 1)} />
          <NumberInput label="Reminder lead hours" min={1} value={leadHours} onChange={(v) => setLeadHours(Number(v) || 1)} />
          <NumberInput label="Max attachments" min={0} max={20} value={maxAtt} onChange={(v) => setMaxAtt(Number(v) || 0)} />
          <Select label="Routine verification by" data={["complainant", "supervisor", "either"]} value={routineVer} onChange={(v) => v && setRoutineVer(v as "complainant" | "supervisor" | "either")} />
          <Select label="Escalated verification by" data={["complainant", "supervisor", "either"]} value={escVer} onChange={(v) => v && setEscVer(v as "complainant" | "supervisor" | "either")} />
          <Switch label="Notify on announcement" checked={notifyAnn} onChange={(e) => setNotifyAnn(e.currentTarget.checked)} />
        </Stack>
      </FormModal>

      <FormModal
        opened={catOpen}
        onClose={() => setCatOpen(false)}
        title="Add complaint category"
        submitLabel="Create"
        submitting={createCat.isPending}
        error={createCat.error}
        disabled={!catCode.trim() || !catName.trim()}
        onSubmit={() => createCat.mutate(
          { code: catCode, name: catName },
          {
            onSuccess: () => {
              notifications.show({ color: "green", title: "Created", message: "Category added." });
              setCatCode(""); setCatName("");
              setCatOpen(false);
            },
          },
        )}
      >
        <Stack gap="sm">
          <TextInput label="Category code" required value={catCode} onChange={(e) => setCatCode(e.currentTarget.value)} />
          <TextInput label="Category name" required value={catName} onChange={(e) => setCatName(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
