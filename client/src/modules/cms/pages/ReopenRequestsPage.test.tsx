import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ReopenRequestsPage from "./ReopenRequestsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <ReopenRequestsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("ReopenRequestsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.reopen_request.approve"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage(["cms.reopen_request.approve"]);
    expect(await screen.findByText("No reopen requests")).toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Reopen list failed" } } } });
    renderPage(["cms.reopen_request.approve"]);
    expect(await screen.findByText(/Reopen list failed/)).toBeInTheDocument();
  });

  it("hides approve/deny controls without permission and submits approval when permitted", async () => {
    const reqRow = { id: 7, complaint: 2, complaint_tracking_code: "CMS-R1", complaint_title: "Leaking tap", reason: "Still leaking", status: "pending", decision_note: "" };
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [reqRow], next: null, previous: null } });
    const { unmount } = renderPage([]);
    expect(await screen.findByText("Still leaking")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    unmount();

    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { ...reqRow, status: "approved" } });
    renderPage(["cms.reopen_request.approve"]);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    fireEvent.change(await screen.findByLabelText(/Decision note/i), { target: { value: "Verified recurrence" } });
    const buttons = screen.getAllByRole("button", { name: "Approve" });
    fireEvent.click(buttons[buttons.length - 1]!);
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/cms/reopen-requests/7/decide/", { decision: "approve", decision_note: "Verified recurrence" }));
  });
});
