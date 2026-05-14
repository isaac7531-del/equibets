import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "../App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    })
  );
});

describe("App", () => {
  it("renders the heading", async () => {
    render(<App />);
    expect(screen.getByText("Equibets")).toBeInTheDocument();
  });

  it("shows empty state message", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("No events yet. Add one above!")).toBeInTheDocument();
    });
  });
});
