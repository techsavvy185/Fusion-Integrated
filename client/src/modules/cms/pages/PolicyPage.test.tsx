import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import PolicyPage from "./PolicyPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderPage(perms: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => perms.includes(p) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <PolicyPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("PolicyPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage(["cms.policy.manage"]);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state and hides action buttons without manage permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage([]);
    expect(await screen.findByText("No CMS policy configured yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publish policy version" })).toBeNull();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Policy error" } } } });
    renderPage(["cms.policy.manage"]);
    expect(await screen.findByText(/Policy error/)).toBeInTheDocument();
  });

  it("creates a category when permitted", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, code: "IT", name: "IT Support" } });
    renderPage(["cms.policy.manage"]);
    fireEvent.click(await screen.findByRole("button", { name: "Add category" }));
    fireEvent.change(await screen.findByLabelText(/Category code/i), { target: { value: "IT" } });
    fireEvent.change(await screen.findByLabelText(/Category name/i), { target: { value: "IT Support" } });
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/cms/categories/", { code: "IT", name: "IT Support" }));
  });
});
