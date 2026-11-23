import { useEffect, useRef, useState } from "react";
import { Button, Group, ScrollArea, SegmentedControl, Stack, Switch } from "@mantine/core";
import { useLog } from "../../api/hooks";

export function LogsPanel() {
  const [name, setName] = useState("bot_swing");
  const [auto, setAuto] = useState(true);
  const log = useLog(name, auto);
  const viewport = useRef<HTMLDivElement>(null);
  useEffect(() => { viewport.current?.scrollTo({ top: viewport.current.scrollHeight }); }, [log.data]);
  return (
    <Stack gap="xs">
      <Group gap="sm">
        <SegmentedControl size="xs" value={name} onChange={setName}
          data={[{ value: "bot_swing", label: "Bot swing" }, { value: "bot_day", label: "Bot trong ngày" },
            { value: "live", label: "Bot cũ" }, { value: "backtest", label: "Backtest" }, { value: "web", label: "Web" }]} />
        <Button size="xs" variant="default" onClick={() => log.refetch()}>Làm mới</Button>
        <Switch size="xs" label="Tự làm mới" checked={auto} onChange={(e) => setAuto(e.currentTarget.checked)} />
      </Group>
      <ScrollArea h={420} viewportRef={viewport}>
        <pre className="pre">{log.error ? log.error.message : log.data?.text || "(trống)"}</pre>
      </ScrollArea>
    </Stack>
  );
}
