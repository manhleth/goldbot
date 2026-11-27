import type { ReactNode } from "react";
import { Group, Text } from "@mantine/core";

interface Props {
  title: ReactNode;
  extra?: ReactNode;
  children: ReactNode;
  /** false = nội dung tự lo cuộn (vd biểu đồ). */
  scroll?: boolean;
  padded?: boolean;
}

/** Khung vùng nội dung kiểu cửa sổ MT5/TradingView: thanh tiêu đề + nội dung cuộn. */
export function Panel({ title, extra, children, scroll = true, padded = true }: Props) {
  return (
    <section className="panel">
      <Group className="panel-head" gap="xs" wrap="nowrap" justify="space-between">
        <Text size="xs" fw={600} tt="uppercase" c="dimmed" className="panel-title">{title}</Text>
        {extra && <Group gap="xs" wrap="nowrap">{extra}</Group>}
      </Group>
      <div className={`panel-body${scroll ? " scroll" : ""}${padded ? " padded" : ""}`}>{children}</div>
    </section>
  );
}
