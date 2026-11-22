import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ReportsPage from "./ReportsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <ReportsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("ReportsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.report.view", "cms.complaint.update"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state when role has no report sections enabled", async () => {
    renderPage(["cms.report.view"]);
    expect(await screen.findByText("No report data available for this role")).toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Report error" } } } });
    renderPage(["cms.report.view", "cms.complaint.update"]);
    expect(await screen.findByText(/Report error/)).toBeInTheDocument();
  });

  it("renders operational report for handler and hides analytics section", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { counts: { total: 4, submitted: 2 }, by_category: [], by_priority: [] },
    });
    renderPage(["cms.report.view", "cms.complaint.update"]);
    expect(await screen.findByText("Operational Report")).toBeInTheDocument();
    expect(screen.queryByText("CMS Analytics")).toBeNull();
  });
});
