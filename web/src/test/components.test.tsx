import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import i18n, { setLocale } from "../i18n";
import { Counter } from "../shared/components/Controls";
import { LanguageSwitch } from "../shared/components/Brand";
import { BookingStatusBadge } from "../shared/components/StatusBadge";
import { MemoryRouter } from "react-router-dom";

describe("BookingStatusBadge", () => {
  it("renders the localized label and follows language changes", async () => {
    await act(() => setLocale("en"));
    render(<BookingStatusBadge status="FINDING_PROVIDER" />);
    expect(screen.getByText("Finding a cleaner")).toBeInTheDocument();
    await act(() => setLocale("sw"));
    expect(screen.getByText("Tunatafuta msafishaji")).toBeInTheDocument();
    await act(() => setLocale("en"));
  });
});

describe("LanguageSwitch", () => {
  it("switches language and persists the choice", async () => {
    await act(() => setLocale("en"));
    render(
      <MemoryRouter>
        <LanguageSwitch />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: "SW" }));
    expect(i18n.language).toBe("sw");
    expect(localStorage.getItem("safisha.locale")).toBe("sw");
    expect(screen.getByRole("button", { name: "SW" })).toHaveAttribute("aria-pressed", "true");
    await act(() => setLocale("en"));
  });
});

describe("Counter", () => {
  it("respects min and max bounds", async () => {
    const onChange = vi.fn();
    render(<Counter value={1} min={1} max={2} onChange={onChange} label="Bathrooms" />);
    expect(screen.getByRole("button", { name: "Bathrooms −" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Bathrooms +" }));
    expect(onChange).toHaveBeenCalledWith(2);
  });
});
