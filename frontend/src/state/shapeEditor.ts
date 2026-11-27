import { useCallback, useEffect, useRef, useState } from "react";
import type { Shape, Tool } from "../lib/drawing";

const HISTORY_LIMIT = 100;

/** Trạng thái sửa nét vẽ của một chart: công cụ, màu, nét đang chọn, lịch sử undo/redo (Ctrl+Z / Ctrl+Y). */
export interface ShapeEditor {
  shapes: Shape[];
  tool: Tool;
  setTool: (t: Tool) => void;
  role: string;
  /** Đổi màu nét mới; đang chọn một nét thì đổi luôn màu nét đó. */
  setRole: (r: string) => void;
  selected: string | null;
  setSelected: (id: string | null) => void;
  /** Ghi một thay đổi (một bước undo). */
  change: (next: Shape[]) => void;
  remove: (id: string) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

/** `save` lưu danh sách nét (tự lưu lên server); lịch sử reset khi đổi `scope`. */
export function useShapeEditor(scope: string, shapes: Shape[], save: (s: Shape[]) => void, defaultRole: string): ShapeEditor {
  const past = useRef<Shape[][]>([]);
  const future = useRef<Shape[][]>([]);
  const current = useRef(shapes);
  current.current = shapes;
  const [, rerender] = useState(0);
  const [tool, setTool] = useState<Tool>("cursor");
  const [role, setRoleState] = useState(defaultRole);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    past.current = [];
    future.current = [];
    setSelected(null);
    rerender((x) => x + 1);
  }, [scope]);

  const change = useCallback((next: Shape[]) => {
    past.current = [...past.current, current.current].slice(-HISTORY_LIMIT);
    future.current = [];
    save(next);
    rerender((x) => x + 1);
  }, [save]);

  const step = useCallback((from: React.MutableRefObject<Shape[][]>, to: React.MutableRefObject<Shape[][]>) => {
    const target = from.current[from.current.length - 1];
    if (!target) return;
    from.current = from.current.slice(0, -1);
    to.current = [...to.current, current.current];
    save(target);
    setSelected((id) => (id && target.some((s) => s.id === id) ? id : null));
    rerender((x) => x + 1);
  }, [save]);

  const undo = useCallback(() => step(past, future), [step]);
  const redo = useCallback(() => step(future, past), [step]);
  const remove = useCallback((id: string) => {
    change(current.current.filter((s) => s.id !== id));
    setSelected((sel) => (sel === id ? null : sel));
  }, [change]);

  const setRole = useCallback((r: string) => {
    setRoleState(r);
    const target = current.current.find((s) => s.id === selected);
    if (target && target.role !== r) change(current.current.map((s) => (s.id === selected ? { ...s, role: r } : s)));
  }, [selected, change]);

  return {
    shapes, tool, setTool, role, setRole, selected, setSelected, change, remove, undo, redo,
    canUndo: past.current.length > 0, canRedo: future.current.length > 0,
  };
}
