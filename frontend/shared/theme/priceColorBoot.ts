/** 首屏前执行的内联脚本（服务端组件可用），默认绿涨红跌。 */
export const PRICE_COLOR_BOOT_SCRIPT = `try{var m=localStorage.getItem("price_color_mode");document.documentElement.dataset.updown=m==="red_up"?"red_up":"green_up"}catch(e){document.documentElement.dataset.updown="green_up"}`;
