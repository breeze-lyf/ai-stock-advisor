import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Tailwind 类合并辅助函数
 * 职责：结合 clsx 和 tailwind-merge，处理动态类名并解决冲突
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 全局日期时间格式化工具
 * 职责：根据用户设置的时区，统一格式化 ISO 字符串
 */
export const formatDateTime = (
  date: string | Date, 
  timezone: string = "Asia/Shanghai",
  formatStr: string = "MM-dd HH:mm"
): string => {
  if (!date) return "--";
  
  let dateObj: Date;
  if (typeof date === "string") {
    // 鲁棒性处理：如果后端返回的是无 Z 标志的 UTC 字符串 (如 "2026-03-04 06:02:00")
    // 浏览器会将其解释为本地时间。我们需要强制将其视为 UTC。
    let dateStr = date;
    if (!dateStr.includes("Z") && !dateStr.includes("+") && !dateStr.includes("T")) {
        dateStr = dateStr.replace(" ", "T") + "Z";
    } else if (dateStr.includes("T") && !dateStr.includes("Z") && !dateStr.includes("+")) {
        dateStr += "Z";
    }
    dateObj = new Date(dateStr);
  } else {
    dateObj = date;
  }
  
  try {
    // 使用 Intl.DateTimeFormat 进行时区转换
    const formatter = new Intl.DateTimeFormat("zh-CN", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    
    const parts = formatter.formatToParts(dateObj);
    const map: Record<string, string> = {};
    parts.forEach(p => { map[p.type] = p.value; });
    
    // 调试日志（仅开发环境可见）
    // console.log(`Formatting ${date} with ${timezone}`, map);

    return formatStr
      .replace("YYYY", map["year"] || "")
      .replace("MM", map["month"] || "")
      .replace("dd", map["day"] || "")
      .replace("HH", map["hour"] || "00")
      .replace("mm", map["minute"] || "00")
      .replace("ss", map["second"] || "00");
  } catch (error) {
    console.error("Format date error:", error);
    return dateObj.toLocaleString();
  }
};
