/**
 * Frontend feature flags (build-time, NEXT_PUBLIC_*). Product is positioned as
 * "你的个人投资智能体": everything outside the core agent flow is hidden by default
 * (hidden, not deleted — pages stay reachable by URL and can be re-enabled per flag).
 */
const on = (v: string | undefined, dflt: boolean) => (v === undefined || v === "" ? dflt : v === "true" || v === "1");

export const FEATURES = {
  /** 订阅/会员/计费 UI（FREE/PRO 徽章等）。默认隐藏：尚无支付闭环。 */
  billing: on(process.env.NEXT_PUBLIC_FEATURE_BILLING, false),
  /** 量化因子工作台：与个人智能体主流程无关、面向专业用户、加载重。 */
  quant: on(process.env.NEXT_PUBLIC_FEATURE_QUANT, false),
  /** 模拟交易（纸面交易）：独立玩法，非主流程。 */
  paperTrading: on(process.env.NEXT_PUBLIC_FEATURE_PAPER_TRADING, false),
  /** 财经日历：信息类页面，智能体可通过新闻/宏观工具覆盖。 */
  calendar: on(process.env.NEXT_PUBLIC_FEATURE_CALENDAR, false),
  /** 宏观热点雷达独立 Tab：智能体已内置 macro_snapshot 工具。 */
  radar: on(process.env.NEXT_PUBLIC_FEATURE_RADAR, false),
  /** 选股器：预设策略筛选，非主流程。 */
  screener: on(process.env.NEXT_PUBLIC_FEATURE_SCREENER, false),
  /** 免登录试用 /try */
  trial: on(process.env.NEXT_PUBLIC_FEATURE_TRIAL, true),
};

export const BRAND = {
  name: "个人投资智能体",
  short: "投资智能体",
  en: "Personal Investment Agent",
  tagline: "记得你的持仓与风格，每天主动简报、每条建议可复盘的 AI 投研助理",
};
