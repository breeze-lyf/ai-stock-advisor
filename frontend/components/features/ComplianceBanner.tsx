/**
 * 合规性声明组件 (Compliance Banner)
 * 职责：全站显著位置展示风险提示和免责声明，满足公安备案/金融监管合规要求
 */
import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

export function ComplianceBanner() {
  return (
    <div className="bg-slate-50 dark:bg-zinc-900/50 border-b border-slate-200 dark:border-zinc-800 py-2 px-4 shadow-inner">
      <div className="max-w-[1400px] mx-auto flex items-center justify-center gap-3 text-slate-500 dark:text-slate-400">
        <AlertTriangle className="h-4 w-4 text-orange-500 shrink-0" />
        <p className="text-[11px] font-medium tracking-tight leading-relaxed">
          <span className="font-bold text-slate-700 dark:text-slate-300">风险提示：</span>
          本平台提供的所有分析数据与 AI 报告仅供技术研究参考，
          <span className="underline decoration-slate-300 underline-offset-2">不构成任何投资建议</span>。
          市场有风险，入市需谨慎。AI 诊断可能存在滞后或偏差，请结合专业意见独立决策。
        </p>
      </div>
    </div>
  );
}

export function FooterCompliance() {
  return (
    <footer className="mt-auto py-8 border-t border-slate-100 dark:border-zinc-800 flex flex-col items-center gap-4 text-slate-400">
      <div className="flex items-center gap-6 text-[10px] font-bold uppercase tracking-widest">
         <span>© 2025 AI Smart Advisor</span>
         <span className="h-3 w-px bg-slate-200 dark:bg-zinc-800" />
         <span>技术支持：硅基流动 DeepSeek-R1</span>
      </div>
      
      <div className="flex items-center gap-4 opacity-70 grayscale hover:grayscale-0 transition-all cursor-default">
        <div className="flex items-center gap-1.5 text-[10px] font-medium border border-slate-200 dark:border-zinc-800 px-2 py-1 rounded">
          <Info className="h-3.5 w-3.5" />
          <span>京ICP备XXXXXXXX号-1 (测试占位)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-medium border border-slate-200 dark:border-zinc-800 px-2 py-1 rounded">
            <img src="https://www.beian.gov.cn/portal/download/beian_icon.png" alt="PSB" className="h-3.5 w-3.5" />
            <span>京公网安备 XXXXXXXXXXXXXX号 (测试占位)</span>
        </div>
      </div>
    </footer>
  );
}
