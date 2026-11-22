import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ComplaintsPage from "./ComplaintsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <ComplaintsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("ComplaintsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state while fetching", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.complaint.view"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state and hides submit button without create permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage(["cms.complaint.view"]);
    expect(await screen.findByText("No complaints found")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit complaint" })).toBeNull();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Server down" } } } });
    renderPage(["cms.complaint.view"]);
    expect(await screen.findByText(/Server down/)).toBeInTheDocument();
  });

  it("shows submit action when permitted and submits complaint", async () => {
    vi.spyOn(http, "get").mockImplementation((url) => {
      if (url === "/cms/categories/") {
        return Promise.resolve({ data: { results: [{ id: 1, code: "NET", name: "Network", description: "", is_active: true, created_at: "" }], next: null, previous: null } });
      }
      return Promise.resolve({ data: { results: [], next: null, previous: null } });
    });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 9, tracking_code: "CMS-99999999" } });
    renderPage(["cms.complaint.view", "cms.complaint.create"]);
    fireEvent.click(await screen.findByRole("button", { name: "Submit complaint" }));
    fireEvent.change(await screen.findByLabelText(/Title/i), { target: { value: "Wi-Fi down" } });
    fireEvent.change(await screen.findByLabelText(/Description/i), { target: { value: "Router offline" } });
    expect(await screen.findByRole("button", { name: "Submit" })).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });
});
