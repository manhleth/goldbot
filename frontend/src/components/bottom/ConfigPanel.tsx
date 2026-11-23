import { useEffect, useState } from "react";
import { Button, Group, Stack, Text, Textarea } from "@mantine/core";
import { IconDeviceFloppy, IconRefresh } from "@tabler/icons-react";
import { actions, useAction, useConfigText } from "../../api/hooks";

export function ConfigPanel() {
  const config = useConfigText();
  const [text, setText] = useState("");
  const [message, setMessage] = useState("Mỗi thay đổi quy tắc/tham số: ghi lý do vào CHANGELOG.md và chạy lại backtest.");
  useEffect(() => { if (config.data) setText(config.data.text); }, [config.data]);
  const save = useAction(actions.saveConfig, {
    success: (r) => {
      setMessage(`Đã lưu (bản cũ: ${r.backup}).${r.bot_running ? " Bot đang chạy: dừng rồi chạy lại để áp dụng." : ""}`);
      return "Đã lưu cấu hình";
    },
    invalidate: [["config"], ["analysis"], ["status"], ["news"]],
  });
  const dirty = config.data ? text !== config.data.text : false;
  return (
    <Stack gap="xs" h="100%">
      <Group gap="xs">
        <Button size="xs" leftSection={<IconDeviceFloppy size={14} />} disabled={!dirty} loading={save.isPending} onClick={() => save.mutate(text)}>Lưu cấu hình</Button>
        <Button size="xs" variant="default" leftSection={<IconRefresh size={14} />} onClick={() => config.data && setText(config.data.text)}>Hoàn tác</Button>
        <Text size="xs" c={save.isError ? "red" : "dimmed"}>{save.isError ? save.error.message : message}</Text>
      </Group>
      <Textarea value={text} onChange={(e) => setText(e.currentTarget.value)} spellCheck={false} autosize={false}
        styles={{ root: { flex: 1 }, wrapper: { height: "100%" }, input: { height: "100%", minHeight: 300, fontFamily: "var(--mantine-font-family-monospace)", fontSize: 12 } }} />
    </Stack>
  );
}
