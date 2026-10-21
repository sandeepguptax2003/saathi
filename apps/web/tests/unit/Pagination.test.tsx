import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination, useCursorPagination } from "@/components/common/Pagination";
import { I18nProvider } from "@/lib/i18n/I18nProvider";

describe("useCursorPagination", () => {
  it("walks forward with cursors and back through the stack", () => {
    const { result } = renderHook(() => useCursorPagination());
    expect(result.current.cursor).toBeUndefined();
    act(() => result.current.next("c2"));
    act(() => result.current.next("c3"));
    expect(result.current).toMatchObject({ cursor: "c3", pageIndex: 2, hasPrevious: true });
    act(() => result.current.previous());
    expect(result.current.cursor).toBe("c2");
    act(() => result.current.next(null));
    expect(result.current.pageIndex).toBe(1);
    act(() => result.current.reset());
    expect(result.current).toMatchObject({ cursor: undefined, pageIndex: 0, hasPrevious: false });
  });
});

describe("<Pagination />", () => {
  it("disables Previous on the first page and calls onNext", async () => {
    const onNext = vi.fn();
    render(
      <I18nProvider>
        <Pagination
          pageIndex={0}
          hasPrevious={false}
          hasNext
          onPrevious={vi.fn()}
          onNext={onNext}
        />
      </I18nProvider>,
    );
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(onNext).toHaveBeenCalledOnce();
  });

  it("renders nothing when there is a single page", () => {
    const { container } = render(
      <I18nProvider>
        <Pagination
          pageIndex={0}
          hasPrevious={false}
          hasNext={false}
          onPrevious={vi.fn()}
          onNext={vi.fn()}
        />
      </I18nProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
