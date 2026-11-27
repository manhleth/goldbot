import { ActionIcon, Button, Group, NumberInput, Stack, Text } from "@mantine/core";
import { IconPlus, IconX } from "@tabler/icons-react";
import type { RiskCaps } from "../../api/types";

const MAX_CAPS = 4;

/** Mốc chặn rủi ro theo vốn: mỗi dòng "vốn ≥ X$ → rủi ro tối đa Y%" (dùng mốc cao nhất đã đạt). Rỗng = không chặn. */
export function RiskCapsInput({ value, onChange }: { value: RiskCaps; onChange: (v: RiskCaps) => void }) {
  const set = (i: number, j: 0 | 1, v: number) => onChange(value.map((c, k) => (k === i ? (j === 0 ? [v, c[1]] : [c[0], v]) : c)));
  const last = value[value.length - 1];
  return (
    <Stack gap={4}>
      <Text size="xs" fw={500}>Chặn rủi ro theo vốn</Text>
      {value.map(([threshold, pct], i) => (
        <Group key={i} gap={6} wrap="nowrap">
          <Text size="xs" c="dimmed">vốn ≥</Text>
          <NumberInput size="xs" w={90} min={1} step={500} thousandSeparator="," value={threshold}
            onChange={(v) => set(i, 0, Number(v) || 500)} />
          <Text size="xs" c="dimmed">$ → tối đa</Text>
          <NumberInput size="xs" w={70} min={0.1} max={50} step={0.5} decimalScale={2} value={pct}
            onChange={(v) => set(i, 1, Number(v) || 1)} />
          <Text size="xs" c="dimmed">%</Text>
          <ActionIcon size="sm" variant="subtle" color="gray" aria-label="Bỏ mốc" onClick={() => onChange(value.filter((_, k) => k !== i))}>
            <IconX size={12} />
          </ActionIcon>
        </Group>
      ))}
      {value.length < MAX_CAPS && (
        <Button size="compact-xs" variant="subtle" leftSection={<IconPlus size={12} />} w="fit-content"
          onClick={() => onChange([...value, last ? [last[0] * 10, Math.max(last[1] / 2, 0.5)] : [500, 10]])}>
          Thêm mốc
        </Button>
      )}
    </Stack>
  );
}
