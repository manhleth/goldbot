import { useState, type ReactNode } from "react";
import { Table, Text } from "@mantine/core";

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
  align?: "left" | "right";
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  onRowClick?: (row: T) => void;
  empty?: string;
  rowKey?: (row: T, index: number) => string | number;
}

export function DataTable<T>({ columns, rows, onRowClick, empty = "Chưa có dữ liệu", rowKey }: Props<T>) {
  const [selected, setSelected] = useState<number | null>(null);
  if (!rows.length) return <Text c="dimmed" size="sm">{empty}</Text>;
  return (
    <Table className="table-sticky num" striped highlightOnHover withRowBorders={false} fz="xs" verticalSpacing={4}>
      <Table.Thead>
        <Table.Tr>
          {columns.map((c) => <Table.Th key={c.key} ta={c.align ?? "left"} c="dimmed" fw={500}>{c.label}</Table.Th>)}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((row, i) => (
          <Table.Tr
            key={rowKey ? rowKey(row, i) : i}
            className={onRowClick ? "row-click" : undefined}
            bg={selected === i ? "var(--mantine-color-blue-light)" : undefined}
            onClick={onRowClick ? () => { setSelected(i); onRowClick(row); } : undefined}
          >
            {columns.map((c) => (
              <Table.Td key={c.key} ta={c.align ?? "left"} style={{ whiteSpace: "nowrap" }}>
                {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "—")}
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
