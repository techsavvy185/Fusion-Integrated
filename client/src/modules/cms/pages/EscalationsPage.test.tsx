import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import EscalationsPage from "./EscalationsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <EscalationsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("EscalationsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.escalation.view"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage(["cms.escalation.view"]);
    expect(await screen.findByText("No escalated complaints")).toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Escalations unavailable" } } } });
    renderPage(["cms.escalation.view"]);
    expect(await screen.findByText(/Escalations unavailable/)).toBeInTheDocument();
  });

  it("lists escalated complaint and opens inspection drawer without handler controls", async () => {
    vi.spyOn(http, "get").mockImplementation((url) => {
      if (url === "/cms/complaints/") {
        return Promise.resolve({
          data: {
            results: [{ id: 5, tracking_code: "CMS-ESC01", title: "Power fault", status: "in_progress", category_name: "Electrical", escalation_type: "manual", is_escalated: true }],
            next: null,
            previous: null,
          },
        });
      }
      return Promise.resolve({
        data: {
          id: 5, tracking_code: "CMS-ESC01", title: "Power fault", description: "Main breaker", status: "in_progress",
          priority: "High", category: 1, category_name: "Electrical", assigned_unit: "Electrical", is_escalated: true,
          escalation_type: "manual", attachments: [], history: [], feedback_entries: [], reopen_requests: [],
        },
      });
    });
    renderPage(["cms.escalation.view"]);
    fireEvent.click(await screen.findByRole("button", { name: "Inspect" }));
    expect(await screen.findByText("Main breaker")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolve complaint" })).toBeNull();
  });
});
