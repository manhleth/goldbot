import { Badge } from "@mantine/core";
import type { Dir } from "../../api/types";
import { NEWS_LABEL } from "../../lib/labels";

const DIR_COLOR: Record<string, string> = { BUY: "teal", SELL: "red", NEUTRAL: "gray" };
const NEWS_COLOR: Record<string, string> = { aligned: "teal", against: "red", neutral: "gray", none: "gray" };

export function DirBadge({ dir, size = "sm" }: { dir: Dir | string; size?: "xs" | "sm" | "md" | "lg" | "xl" }) {
  return <Badge color={DIR_COLOR[dir] ?? "gray"} variant="light" size={size} radius="sm">{dir}</Badge>;
}

export function NewsBadge({ value }: { value: string | null }) {
  const key = value || "none";
  return <Badge color={NEWS_COLOR[key] ?? "gray"} variant="light" size="xs" radius="sm">{NEWS_LABEL[key] ?? key}</Badge>;
}
