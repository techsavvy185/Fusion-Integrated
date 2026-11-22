import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useAnnouncements, useComplaints, useSubmitComplaint } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("CMS API hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches complaints with query params through shared http client", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    const { result } = renderHook(() => useComplaints({ status: "submitted" }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/cms/complaints/", { params: { status: "submitted" } });
  });

  it("posts new complaints through shared http client", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, tracking_code: "CMS-AAA11111" } });
    const { result } = renderHook(() => useSubmitComplaint(), { wrapper });
    result.current.mutate({ category_id: 1, title: "Leak", description: "Pipe leaking" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/cms/complaints/", {
      category_id: 1,
      title: "Leak",
      description: "Pipe leaking",
    });
  });

  it("fetches announcements", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    const { result } = renderHook(() => useAnnouncements(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/cms/announcements/");
  });
});
