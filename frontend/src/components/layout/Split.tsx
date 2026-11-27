import { Children, useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

interface Props {
  /** Khoá lưu kích thước (localStorage), mỗi vùng chia một khoá riêng. */
  id: string;
  direction: "row" | "column";
  /** Tỉ lệ ban đầu của từng vùng (tổng bất kỳ). */
  initial: number[];
  /** Kích thước tối thiểu mỗi vùng (px). */
  min?: number;
  children: ReactNode;
}

const key = (id: string) => `goldbot.split.${id}`;

function loadSizes(id: string, count: number): number[] | null {
  try {
    const v = JSON.parse(localStorage.getItem(key(id)) || "null");
    return Array.isArray(v) && v.length === count ? v : null;
  } catch {
    return null;
  }
}

/** Chia vùng kéo được (kiểu TradingView/MT5): kéo thanh giữa hai vùng để đổi kích thước; nhấp đúp = về mặc định. */
export function Split({ id, direction, initial, min = 120, children }: Props) {
  const panes = Children.toArray(children);
  const total = initial.reduce((a, b) => a + b, 0);
  const defaults = initial.map((v) => v / total);
  const [sizes, setSizes] = useState<number[]>(() => loadSizes(id, panes.length) ?? defaults);
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ index: number; start: number; sizes: number[]; length: number } | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(key(id), JSON.stringify(sizes));
    } catch {
      /* bỏ qua */
    }
  }, [id, sizes]);

  const onMove = useCallback((e: PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const delta = ((direction === "row" ? e.clientX : e.clientY) - d.start) / d.length;
    const minRatio = min / d.length;
    const pair = d.sizes[d.index] + d.sizes[d.index + 1];
    const first = Math.min(Math.max(d.sizes[d.index] + delta, minRatio), pair - minRatio);
    setSizes(d.sizes.map((s, i) => (i === d.index ? first : i === d.index + 1 ? pair - first : s)));
  }, [direction, min]);

  const onUp = useCallback(() => {
    drag.current = null;
    document.body.classList.remove("resizing", "resizing-row", "resizing-column");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  }, [onMove]);

  const onDown = (index: number) => (e: ReactPointerEvent) => {
    const rect = box.current?.getBoundingClientRect();
    if (!rect) return;
    drag.current = {
      index, sizes, start: direction === "row" ? e.clientX : e.clientY,
      length: direction === "row" ? rect.width : rect.height,
    };
    document.body.classList.add("resizing", `resizing-${direction}`);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <div ref={box} className={`split split-${direction}`}>
      {panes.map((pane, i) => (
        <div key={i} className="split-item" style={{ flexGrow: sizes[i], flexBasis: 0 }}>
          <div className="split-pane">{pane}</div>
          {i < panes.length - 1 && (
            <div className="split-gutter" role="separator"
              aria-orientation={direction === "row" ? "vertical" : "horizontal"}
              title="Kéo để đổi kích thước · nhấp đúp để về mặc định"
              onPointerDown={onDown(i)} onDoubleClick={() => setSizes(defaults)} />
          )}
        </div>
      ))}
    </div>
  );
}
