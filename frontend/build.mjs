// Chạy `vite build` trong tiến trình con với cwd và đường dẫn vite đều là đường dẫn thật
// (D:\gold-bot có thể là junction; Rollup lỗi khi thấy hai đường dẫn cho cùng một file).
import { spawnSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { join } from "node:path";

const cwd = realpathSync.native(process.cwd());
const vite = join(cwd, "node_modules", "vite", "bin", "vite.js");
const result = spawnSync(process.execPath, [vite, "build"], { cwd, stdio: "inherit" });
process.exit(result.status ?? 1);
