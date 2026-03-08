import React from 'react';
import { CheckCircle2, Search, Zap, AlertTriangle, Target } from 'lucide-react';
import { clsx } from 'clsx';

interface LogicStep {
  step: string;
  content: string;
}

interface LogicChainProps {
  steps: LogicStep[];
}

const stepIcons: Record<string, React.ReactNode> = {
  "观察": <Search className="w-4 h-4" />,
  "推导": <Zap className="w-4 h-4" />,
  "风险评估": <AlertTriangle className="w-4 h-4" />,
  "结论": <Target className="w-4 h-4" />,
};

const stepColors: Record<string, string> = {
  "观察": "text-slate-500 bg-slate-100",
  "推导": "text-blue-600 bg-blue-50",
  "风险评估": "text-rose-600 bg-rose-50",
  "结论": "text-emerald-600 bg-emerald-50",
};

export const LogicChain: React.FC<LogicChainProps> = ({ steps }) => {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="space-y-4 py-4">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-1 h-4 bg-blue-600 rounded-full" />
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">AI 思辨逻辑链 (Thought Process)</h3>
      </div>
      
      <div className="relative ml-3">
        {/* Vertical Line */}
        <div className="absolute left-0 top-2 bottom-2 w-px bg-slate-200" />

        <div className="space-y-8">
          {steps.map((item, index) => (
            <div key={index} className="relative pl-8">
              {/* Dot Icon */}
              <div className={clsx(
                "absolute left-[-14px] top-0 w-7 h-7 rounded-full flex items-center justify-center border-4 border-white z-10 shadow-sm",
                stepColors[item.step] || "bg-slate-100 text-slate-500"
              )}>
                {stepIcons[item.step] || <CheckCircle2 className="w-4 h-4" />}
              </div>

              <div className="flex flex-col gap-1">
                <span className={clsx(
                  "text-[10px] font-bold uppercase tracking-widest",
                  stepColors[item.step]?.split(' ')[0] || "text-slate-500"
                )}>
                  {item.step}
                </span>
                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                  {item.content}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
