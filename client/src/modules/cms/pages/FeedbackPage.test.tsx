import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import FeedbackPage from "./FeedbackPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <FeedbackPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("FeedbackPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockImplementation(() => new Promise(() => undefined));
    renderPage();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [], next: null, previous: null } });
    renderPage();
    expect(await screen.findByText("No feedback submitted yet")).toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Feedback error" } } } });
    renderPage();
    expect(await screen.findByText(/Feedback error/)).toBeInTheDocument();
  });

  it("renders submitted feedback entries cleanly without write buttons", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: {
        results: [{ id: 1, complaint: 3, complaint_tracking_code: "CMS-F1", complaint_title: "Fan fix", category_name: "Electrical", rating: 5, comment: "Great job" }],
        next: null,
        previous: null,
      },
    });
    renderPage();
    expect(await screen.findByText("Great job")).toBeInTheDocument();
    expect(screen.getByText("5 / 5")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
