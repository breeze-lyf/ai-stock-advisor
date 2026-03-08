"use client";

import { useState, useEffect } from "react";
import { Loader2, TrendingUp, TrendingDown, Target, ShieldAlert, CheckCircle2, XCircle, Clock } from "lucide-react";
import { getSimulatedTrades } from "@/lib/api";
import { SimulatedTrade } from "@/types";

export function PaperTradingDashboard() {
  const [loading, setLoading] = useState(true);
  const [trades, setTrades] = useState<SimulatedTrade[]>([]);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        setLoading(true);
        const data = await getSimulatedTrades();
        setTrades(data);
      } catch (err) {
        console.error("Failed to load paper trades", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrades();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-slate-500 text-sm">正在同步远航模拟舱数据...</p>
      </div>
    );
  }

  const activeTrades = trades.filter(t => t.status === "OPEN");
  const closedTrades = trades.filter(t => t.status !== "OPEN");

  // Calculate some basic stats
  const totalClosed = closedTrades.length;
  const profitableTrades = closedTrades.filter(t => t.unrealized_pnl_pct > 0);
  const winRate = totalClosed > 0 ? (profitableTrades.length / totalClosed) * 100 : 0;
  
  const totalPnlPct = closedTrades.reduce((acc, curr) => acc + curr.unrealized_pnl_pct, 0) + 
                      activeTrades.reduce((acc, curr) => acc + curr.unrealized_pnl_pct, 0);

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 flex items-center gap-2">
            <Target className="w-6 h-6 text-blue-600" />
            远航模拟舱 (Paper Trading)
          </h1>
          <p className="text-slate-500 mt-2 text-sm md:text-base">实时追踪 AI 决策，在真实时光线中验证量化模型与策略的回测表现。</p>
        </div>
      </div>

      {/* Scoreboard (总体看板) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
         <div className="bg-white dark:bg-slate-900 border dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-center">
            <p className="text-sm font-medium text-slate-500 mb-1">累计基准盈亏 (Total PnL %)</p>
             <div className={`text-3xl font-bold flex items-center gap-2 ${totalPnlPct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
               {totalPnlPct >= 0 ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
               {totalPnlPct > 0 ? "+" : ""}{totalPnlPct.toFixed(2)}%
            </div>
         </div>
         <div className="bg-white dark:bg-slate-900 border dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-center">
            <p className="text-sm font-medium text-slate-500 mb-1">历史胜率 (Win Rate)</p>
            <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">
               {winRate.toFixed(1)}%
               <span className="text-sm text-slate-400 font-normal ml-2">({profitableTrades.length}/{totalClosed})</span>
            </div>
         </div>
         <div className="bg-white dark:bg-slate-900 border dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-center">
            <p className="text-sm font-medium text-slate-500 mb-1">激战中 (Active Trades)</p>
            <div className="text-3xl font-bold text-blue-600">
               {activeTrades.length} <span className="text-sm text-slate-400 font-normal">个标的</span>
            </div>
         </div>
      </div>

      {/* Active Trades */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold border-l-4 border-blue-600 pl-3 flex items-center gap-2">
           <Clock className="w-5 h-5 text-blue-600" />
           进行中的战役 (Active Trades)
        </h2>
        {activeTrades.length === 0 ? (
           <div className="bg-white dark:bg-slate-900 border border-dashed dark:border-slate-700 rounded-2xl p-10 text-center text-slate-500">
             目前没有进行中的模拟交易，点击雷达发现机会并加入。
           </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeTrades.map(trade => (
              <TradeCard key={trade.id} trade={trade} />
            ))}
          </div>
        )}
      </div>
      
      {/* Closed Trades */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold border-l-4 border-slate-500 pl-3 flex items-center gap-2">
           <CheckCircle2 className="w-5 h-5 text-slate-500" />
           历史记录 (Closed Trades)
        </h2>
        {closedTrades.length === 0 ? (
           <div className="bg-white dark:bg-slate-900 border border-dashed dark:border-slate-700 rounded-2xl p-10 text-center text-slate-500">
             暂无已平仓的记录。
           </div>
        ) : (
          <div className="bg-white dark:bg-slate-900 border dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500">
                  <tr>
                    <th className="px-6 py-4 font-medium">标的</th>
                    <th className="px-6 py-4 font-medium">状态</th>
                    <th className="px-6 py-4 font-medium text-right">买入价</th>
                    <th className="px-6 py-4 font-medium text-right">平仓价</th>
                    <th className="px-6 py-4 font-medium text-right">最终盈亏</th>
                    <th className="px-6 py-4 font-medium">平仓时间</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {closedTrades.map(trade => (
                    <tr key={trade.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-6 py-4 font-bold">{trade.stock_ticker}</td>
                      <td className="px-6 py-4">
                         <TradeStatusBadge status={trade.status} />
                      </td>
                      <td className="px-6 py-4 text-right">{trade.entry_price.toFixed(2)}</td>
                      <td className="px-6 py-4 text-right">{trade.current_price.toFixed(2)}</td>
                       <td className={`px-6 py-4 text-right font-bold ${trade.unrealized_pnl_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                         {trade.unrealized_pnl_pct > 0 ? "+" : ""}{trade.unrealized_pnl_pct.toFixed(2)}%
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                         {trade.exit_date ? new Date(trade.exit_date).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------- Helper Components ----------------

function TradeCard({ trade }: { trade: SimulatedTrade }) {
  const isProfit = trade.unrealized_pnl_pct >= 0;
  
  return (
    <div className="bg-white dark:bg-slate-900 border dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
      {/* Decorative colored strip on left */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${isProfit ? "bg-emerald-600" : "bg-rose-600"}`} />
      
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">{trade.stock_ticker}</h3>
          <p className="text-xs text-slate-500 mt-1">
             买入于 {new Date(trade.entry_date).toLocaleDateString('zh-CN')}
          </p>
        </div>
        <div className={`text-right ${isProfit ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50"} dark:bg-opacity-10 px-3 py-1.5 rounded-lg flex items-center gap-1.5`}>
          {isProfit ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          <span className="font-bold text-lg">{isProfit ? "+" : ""}{trade.unrealized_pnl_pct.toFixed(2)}%</span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-y-4 gap-x-6 mb-4">
        <div>
          <p className="text-xs text-slate-500 mb-1">买入价</p>
          <p className="font-medium">{trade.entry_price.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">现价 (MTM)</p>
          <p className="font-medium bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded inline-block">
             {trade.current_price.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
             <Target className="w-3 h-3 text-blue-600" /> 目标止盈
          </p>
          <p className="font-medium">{trade.target_price ? trade.target_price.toFixed(2) : "未设置"}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
             <ShieldAlert className="w-3 h-3 text-orange-500" /> 目标止损
          </p>
          <p className="font-medium">{trade.stop_loss_price ? trade.stop_loss_price.toFixed(2) : "未设置"}</p>
        </div>
      </div>
      
      {trade.entry_reason && (
        <div className="mt-4 pt-4 border-t dark:border-slate-800">
           <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">研判逻辑 / 入场理由</p>
           <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-3 leading-relaxed">
             {trade.entry_reason}
           </p>
        </div>
      )}
    </div>
  );
}

function TradeStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'CLOSED_PROFIT':
      return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"><TrendingUp className="w-3 h-3" /> 获利平仓</span>;
    case 'CLOSED_LOSS':
      return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-100 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400"><TrendingDown className="w-3 h-3" /> 止损平仓</span>;
    case 'CLOSED_MANUAL':
      return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"><XCircle className="w-3 h-3" /> 手动平仓</span>;
    case 'CLOSED_SYSTEM':
      return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400">系统接管</span>;
    default:
      return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">进行中</span>;
  }
}

