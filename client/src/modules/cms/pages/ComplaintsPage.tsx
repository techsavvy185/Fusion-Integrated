import { useState } from "react";
import { Badge, Button, Card, Container, Group, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCategories, useComplaints, useSubmitComplaint } from "../api/hooks";
import { ComplaintDetailDrawer } from "../components/ComplaintDetailDrawer";

export default function ComplaintsPage() {
  const { can } = useAuth();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  const { data, isPending, error } = useComplaints(statusFilter ? { status: statusFilter } : {});
  const { data: catData } = useCategories();
  const submit = useSubmitComplaint();

  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];
  const categories = (catData?.results ?? []).map((c) => ({ value: String(c.id), label: `${c.code} — ${c.name}` }));

  return (
    <Container size="md">
      <PageHeader
        title="Complaints"
        subtitle="Submit, track, and manage institutional complaints"
        action={can("cms.complaint.create") && (
          <Button onClick={() => setCreating(true)}>Submit complaint</Button>
        )}
      />

      <Group mb="md">
        <Select
          label="Filter by status"
          placeholder="All statuses"
          clearable
          data={["submitted", "in_progress", "resolved", "rejected", "closed"]}
          value={statusFilter || null}
          onChange={(v) => setStatusFilter(v ?? "")}
        />
      </Group>

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No complaints found</Text>
        </Card>
      )}

      <Stack gap="sm">
        {rows.map((c) => (
          <Card key={c.id} padding="md" withBorder>
            <Group justify="space-between" align="flex-start">
              <Stack gap={4}>
                <Group gap="xs">
                  <Text fw={700}>{c.tracking_code}</Text>
                  <Text fw={600}>{c.title}</Text>
                  <Badge size="sm">{c.status}</Badge>
                  {c.priority && <Badge variant="light" size="sm">{c.priority}</Badge>}
                  {c.is_escalated && <Badge color="red" size="sm">Escalated</Badge>}
                </Group>
                <Text size="xs" c="dimmed">{c.category_name}</Text>
              </Stack>
              <Button size="xs" variant="light" onClick={() => setSelectedId(c.id)}>View details</Button>
            </Group>
          </Card>
        ))}
      </Stack>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Submit a complaint"
        subtitle="Provide category, title, description, and an optional Google Drive attachment link"
        submitLabel="Submit"
        submitting={submit.isPending}
        error={submit.error}
        disabled={!categoryId || !title.trim() || !description.trim()}
        onSubmit={() => submit.mutate(
          {
            category_id: Number(categoryId),
            title,
            description,
            attachments: attachmentUrl.trim() ? [{ label: "attachment", url: attachmentUrl.trim() }] : [],
          },
          {
            onSuccess: (created) => {
              notifications.show({ color: "green", title: "Submitted", message: `Tracking code: ${created.tracking_code}` });
              setTitle(""); setDescription(""); setAttachmentUrl("");
              setCreating(false);
            },
          },
        )}
      >
        <Stack gap="md">
          <Select label="Category" required data={categories} value={categoryId} onChange={setCategoryId} />
          <TextInput label="Title" required value={title} onChange={(e) => setTitle(e.currentTarget.value)} maxLength={200} />
          <Textarea label="Description" required value={description} onChange={(e) => setDescription(e.currentTarget.value)} minRows={4} />
          <TextInput label="Supporting attachment link (optional)" value={attachmentUrl} onChange={(e) => setAttachmentUrl(e.currentTarget.value)} placeholder="https://drive.google.com/file/d/..." />
        </Stack>
      </FormModal>

      <ComplaintDetailDrawer complaintId={selectedId} onClose={() => setSelectedId(null)} />
    </Container>
  );
}
