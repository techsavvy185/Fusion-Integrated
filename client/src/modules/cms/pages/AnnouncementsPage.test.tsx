import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AnnouncementsPage from "./AnnouncementsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <AnnouncementsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("AnnouncementsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.announcement.view"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state and hides publish button without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage(["cms.announcement.view"]);
    expect(await screen.findByText("No announcements published yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publish announcement" })).toBeNull();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Announcements failed" } } } });
    renderPage(["cms.announcement.view"]);
    expect(await screen.findByText(/Announcements failed/)).toBeInTheDocument();
  });

  it("publishes an announcement when permitted", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, title: "Water Notice", body: "Paused 2-4 PM" } });
    renderPage(["cms.announcement.view", "cms.announcement.publish"]);
    fireEvent.click(await screen.findByRole("button", { name: "Publish announcement" }));
    fireEvent.change(await screen.findByLabelText(/Title/i), { target: { value: "Water Notice" } });
    fireEvent.change(await screen.findByLabelText(/Body/i), { target: { value: "Paused 2-4 PM" } });
    fireEvent.click(await screen.findByRole("button", { name: "Publish" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/cms/announcements/", { title: "Water Notice", body: "Paused 2-4 PM" }));
  });
});
