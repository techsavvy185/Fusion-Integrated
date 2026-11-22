import { useState } from "react";
import { Button, Card, Container, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, usePublishAnnouncement } from "../api/hooks";

export default function AnnouncementsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useAnnouncements();
  const publish = usePublishAnnouncement();
  const [writing, setWriting] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader
        title="CMS Announcements"
        subtitle="Complaint-related updates and service notices"
        action={can("cms.announcement.publish") && (
          <Button onClick={() => setWriting(true)}>Publish announcement</Button>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">No announcements published yet</Text>
        </Card>
      )}

      <Stack gap="sm">
        {rows.map((ann) => (
          <Card key={ann.id} padding="md" withBorder>
            <Text fw={700}>{ann.title}</Text>
            <Text size="sm" mt={4}>{ann.body}</Text>
            <Text size="xs" c="dimmed" mt={6}>{ann.published_by_role} · {new Date(ann.published_at).toLocaleString()}</Text>
          </Card>
        ))}
      </Stack>

      <FormModal
        opened={writing}
        onClose={() => setWriting(false)}
        title="Publish announcement"
        submitLabel="Publish"
        submitting={publish.isPending}
        error={publish.error}
        disabled={!title.trim() || !body.trim()}
        onSubmit={() => publish.mutate(
          { title, body },
          {
            onSuccess: () => {
              notifications.show({ color: "green", title: "Published", message: "Announcement is live." });
              setTitle(""); setBody("");
              setWriting(false);
            },
          },
        )}
      >
        <Stack gap="md">
          <TextInput label="Title" required value={title} onChange={(e) => setTitle(e.currentTarget.value)} maxLength={200} />
          <Textarea label="Body" required value={body} onChange={(e) => setBody(e.currentTarget.value)} minRows={4} />
        </Stack>
      </FormModal>
    </Container>
  );
}
