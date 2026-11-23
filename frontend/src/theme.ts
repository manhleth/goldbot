import { createTheme, type MantineColorsTuple } from "@mantine/core";

/** Nền tối dịu (không đen tuyệt đối), chữ xám sáng thay vì trắng để đỡ chói. */
const dark: MantineColorsTuple = [
  "#c9ccd3", "#aeb2bc", "#8c919e", "#6b7080", "#363b47", "#2a2e38", "#20232b", "#181a21", "#131519", "#0e0f13",
];

export const theme = createTheme({
  primaryColor: "blue",
  defaultRadius: "md",
  fontFamily: "Inter, 'Segoe UI', Roboto, Arial, sans-serif",
  fontFamilyMonospace: "'JetBrains Mono', Consolas, monospace",
  colors: { dark },
});

/** Màu biểu đồ: cặp đối nghịch xanh/đỏ (đã kiểm tra tương phản & mù màu trên nền tối). */
export const CHART = {
  positive: "#3987e5",
  negative: "#e66767",
  grid: "#262a33",
  axis: "#6b7080",
  text: "#aeb2bc",
  surface: "#181a21",
  candleUp: "#26a69a",
  candleDown: "#ef5350",
  emas: ["#3987e5", "#c98500", "#d55181", "#199e70"],
  warn: "#fab219",
};
