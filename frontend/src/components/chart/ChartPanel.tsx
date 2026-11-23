import { Checkbox, Group, Text } from "@mantine/core";
import { useUi, type Overlay } from "../../state/ui";
import { SourceSelect } from "../common/SourceSelect";
import { PriceChart } from "./PriceChart";

const OVERLAYS: [Overlay, string][] = [
  ["ema", "EMA"], ["sr", "S/R"], ["fvg", "FVG"], ["ob", "OB"], ["swings", "Swing"],
  ["setups", "Setup"], ["trades", "Lệnh"], ["news", "Tin"],
];

export function ChartPanel() {
  const { overlays, toggleOverlay } = useUi();
  return (
    <>
      <Group gap="md" px="sm" py={6} wrap="wrap" style={{ borderBottom: "1px solid var(--mantine-color-dark-5)" }}>
        <Text size="xs" c="dimmed">Hiển thị</Text>
        {OVERLAYS.map(([key, label]) => (
          <Checkbox key={key} size="xs" label={label} checked={overlays[key]} onChange={() => toggleOverlay(key)} />
        ))}
        <div style={{ flex: 1 }} />
        <Text size="xs" c="dimmed">Nguồn lệnh</Text>
        <SourceSelect />
      </Group>
      <PriceChart />
    </>
  );
}
