import { ActionIcon, ColorSwatch, Group, Tooltip } from "@mantine/core";
import {
  IconArrowBackUp, IconArrowForwardUp, IconEraser, IconLine, IconMinus, IconPointer, IconRectangle, IconTrash,
} from "@tabler/icons-react";
import type { ReviewOption } from "../../api/types";
import type { Tool } from "../../lib/drawing";
import type { ShapeEditor } from "../../state/shapeEditor";

const TOOLS: { tool: Tool; label: string; icon: typeof IconLine }[] = [
  { tool: "cursor", label: "Con trỏ: bấm chọn nét, kéo nét/đầu mút để sửa, Delete để xoá", icon: IconPointer },
  { tool: "trend", label: "Trendline: click 2 điểm", icon: IconLine },
  { tool: "hline", label: "Đường ngang (S/R): click 1 điểm", icon: IconMinus },
  { tool: "zone", label: "Vùng: click 2 góc", icon: IconRectangle },
  { tool: "erase", label: "Tẩy: bấm vào nét để xoá", icon: IconEraser },
];

function Btn({ label, onClick, disabled, active, children }: {
  label: string; onClick: () => void; disabled?: boolean; active?: boolean; children: React.ReactNode;
}) {
  return (
    <Tooltip label={label} withArrow>
      <ActionIcon size="sm" variant={active ? "filled" : "subtle"} color={active ? "blue" : "gray"} aria-label={label}
        disabled={disabled} onClick={onClick}>
        {children}
      </ActionIcon>
    </Tooltip>
  );
}

/** Công cụ vẽ, hoàn tác/làm lại, màu nét (đang chọn nét thì đổi màu nét đó), xoá hết. */
export function DrawToolbar({ editor, roles }: { editor: ShapeEditor; roles: ReviewOption[] }) {
  const count = editor.shapes.length;
  const activeRole = editor.shapes.find((s) => s.id === editor.selected)?.role ?? editor.role;
  return (
    <Group gap={4} wrap="nowrap">
      {TOOLS.map(({ tool, label, icon: Icon }) => (
        <Btn key={tool} label={label} active={editor.tool === tool} onClick={() => editor.setTool(tool)}>
          <Icon size={15} />
        </Btn>
      ))}
      <div className="draw-sep" />
      <Btn label="Hoàn tác (Ctrl+Z)" disabled={!editor.canUndo} onClick={editor.undo}><IconArrowBackUp size={15} /></Btn>
      <Btn label="Làm lại (Ctrl+Y)" disabled={!editor.canRedo} onClick={editor.redo}><IconArrowForwardUp size={15} /></Btn>
      <div className="draw-sep" />
      {roles.map((r) => (
        <Tooltip key={r.key} withArrow
          label={editor.selected ? `Đổi nét đang chọn sang: ${r.label}` : `Màu nét: ${r.label}`}>
          <ColorSwatch component="button" type="button" size={16} color={r.color ?? "#ffb74d"} aria-label={r.label}
            onClick={() => editor.setRole(r.key)} className={`draw-swatch${activeRole === r.key ? " active" : ""}`} />
        </Tooltip>
      ))}
      <Btn label="Xoá hết nét vẽ (Ctrl+Z để lấy lại)" disabled={!count} onClick={() => editor.change([])}>
        <IconTrash size={15} />
      </Btn>
    </Group>
  );
}
