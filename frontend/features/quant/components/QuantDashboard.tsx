"use client";

import { useState } from "react";
import { useQuantFactors, useFactorAnalysis, useFactorBacktest, useStrategies, useBacktest, useOptimizer } from "@/features/quant/hooks/useQuant";
import { LineChart, BarChart } from "@/components/charts";
import { Plus, Trash2, Play, Settings, TrendingUp, PieChart, Activity, Shield } from "lucide-react";

type MainTab = "factors" | "optimizer" | "strategies" | "backtest" | "risk";
type FactorSubTab = "list" | "ic" | "turnover" | "decay" | "layered";

const OPTIMIZER_TYPES = [
  { value: "mean_variance" as const, label: "均值方差" },
  { value: "black_litterman" as const, label: "Black-Litterman" },
  { value: "risk_parity" as const, label: "风险平价" },
  { value: "hrp" as const, label: "层次风险平价" },
  { value: "min_volatility" as const, label: "最小波动率" },
  { value: "max_sharpe" as const, label: "最大夏普" },
] as const;

export default function QuantDashboard() {
  const [mainTab, setMainTab] = useState<MainTab>("factors");
  const [factorSubTab, setFactorSubTab] = useState<FactorSubTab>("list");
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({ start: "2025-01-01", end: "2026-04-07" });

  const { factors, loading: factorsLoading, refresh: refreshFactors } = useQuantFactors();
  const { icData, turnoverData, decayData, loading: analysisLoading, fetchICAnalysis, fetchTurnover, fetchDecay } = useFactorAnalysis(selectedFactor || "", dateRange.start, dateRange.end);
  const { data: backtestData, fetchBacktest } = useFactorBacktest(selectedFactor || "", dateRange.start, dateRange.end);
  const { strategies, refresh: refreshStrategies, createStrategy, generateSignals } = useStrategies();
  const { run: runBacktest, result: backtestResult } = useBacktest();
  const { optimize, result: optimizeResult } = useOptimizer();

  const [newFactor, setNewFactor] = useState({ name: "", code_name: "", category: "CUSTOM", formula: "" });
  const [selectedOptimizer, setSelectedOptimizer] = useState<"mean_variance" | "black_litterman" | "risk_parity" | "hrp" | "min_volatility" | "max_sharpe">("mean_variance");

  const handleCreateFactor = async () => {
    try {
      const { createFactor } = await import("@/features/quant/api");
      await createFactor(newFactor);
      await refreshFactors();
      setNewFactor({ name: "", code_name: "", category: "CUSTOM", formula: "" });
    } catch (e: any) {
      alert("创建失败：" + e.message);
    }
  };

  const handleDeleteFactor = async (factorId: string) => {
    if (!confirm("确定删除此因子？")) return;
    try {
      const { deleteFactor } = await import("@/features/quant/api");
      await deleteFactor(factorId);
      await refreshFactors();
    } catch (e: any) {
      alert("删除失败：" + e.message);
    }
  };

  const handleRunBacktest = async () => {
    try {
      await runBacktest({
        name: "Factor Backtest",
        start_date: dateRange.start,
        end_date: dateRange.end,
        factor_ids: selectedFactor ? [selectedFactor] : [],
        initial_capital: 1000000,
        rebalance_frequency: "WEEKLY",
      });
    } catch (e: any) {
      alert("回测失败：" + e.message);
    }
  };

  const handleOptimize = async () => {
    try {
      await optimize({
        optimizer_type: selectedOptimizer,
        expected_returns: {},
        cov_matrix: {},
      });
    } catch (e: any) {
      alert("优化失败：" + e.message);
    }
  };

  const handleGenerateSignals = async (strategyId: string) => {
    try {
      const result = await generateSignals(strategyId);
      alert(`生成 ${result.signals.length} 个信号`);
    } catch (e: any) {
      alert("生成信号失败：" + e.message);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">量化因子研究</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">因子分析、组合优化、策略回测、风险管理</p>
          </div>
        </div>

        {/* Main Tabs */}
        <div className="flex gap-2 mt-4">
          <TabButton active={mainTab === "factors"} onClick={() => setMainTab("factors")} icon={<TrendingUp />} label="因子研究" />
          <TabButton active={mainTab === "optimizer"} onClick={() => setMainTab("optimizer")} icon={<PieChart />} label="组合优化" />
          <TabButton active={mainTab === "strategies"} onClick={() => setMainTab("strategies")} icon={<Activity />} label="策略管理" />
          <TabButton active={mainTab === "backtest"} onClick={() => setMainTab("backtest")} icon={<Play />} label="量化回测" />
          <TabButton active={mainTab === "risk"} onClick={() => setMainTab("risk")} icon={<Shield />} label="风险管理" />
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* 因子研究 */}
        {mainTab === "factors" && (
          <div>
            {/* Sub Tabs */}
            <div className="flex gap-2 mb-6">
              <SubTabButton active={factorSubTab === "list"} onClick={() => setFactorSubTab("list")} label="因子列表" />
              <SubTabButton active={factorSubTab === "ic"} onClick={() => setFactorSubTab("ic")} disabled={!selectedFactor} label="IC 分析" />
              <SubTabButton active={factorSubTab === "turnover"} onClick={() => { setFactorSubTab("turnover"); fetchTurnover(); }} disabled={!selectedFactor} label="换手率" />
              <SubTabButton active={factorSubTab === "decay"} onClick={() => { setFactorSubTab("decay"); fetchDecay(); }} disabled={!selectedFactor} label="衰减分析" />
              <SubTabButton active={factorSubTab === "layered"} onClick={() => { setFactorSubTab("layered"); fetchBacktest(); }} disabled={!selectedFactor} label="分层回测" />
            </div>

            {/* 因子列表 */}
            {factorSubTab === "list" && (
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex gap-4">
                  <input
                    type="text"
                    placeholder="因子名称"
                    value={newFactor.name}
                    onChange={(e) => setNewFactor({ ...newFactor, name: e.target.value })}
                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="代码名称"
                    value={newFactor.code_name}
                    onChange={(e) => setNewFactor({ ...newFactor, code_name: e.target.value })}
                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                  />
                  <select
                    value={newFactor.category}
                    onChange={(e) => setNewFactor({ ...newFactor, category: e.target.value })}
                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                  >
                    <option value="MOMENTUM">动量</option>
                    <option value="VALUE">价值</option>
                    <option value="GROWTH">成长</option>
                    <option value="QUALITY">质量</option>
                    <option value="VOLATILITY">波动率</option>
                    <option value="LIQUIDITY">流动性</option>
                    <option value="TECHNICAL">技术</option>
                    <option value="CUSTOM">自定义</option>
                  </select>
                  <button onClick={handleCreateFactor} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 flex items-center gap-2">
                    <Plus size={16} /> 创建因子
                  </button>
                </div>
                <table className="w-full">
                  <thead className="bg-slate-50 dark:bg-slate-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">名称</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">类别</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">IC 均值</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ICIR</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">年化收益</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">夏普</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {factorsLoading ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">加载中...</td></tr>
                    ) : factors.length === 0 ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">暂无因子</td></tr>
                    ) : (
                      factors.map((f) => (
                        <tr key={f.id} className={`hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer ${selectedFactor === f.id ? "bg-blue-50 dark:bg-blue-900/20" : ""}`} onClick={() => setSelectedFactor(f.id)}>
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-900 dark:text-white">{f.name}</div>
                            <div className="text-xs text-slate-500">{f.code_name}</div>
                          </td>
                          <td className="px-4 py-3"><span className="px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">{f.category}</span></td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{f.ic_mean ? (f.ic_mean * 100).toFixed(2) + "%" : "-"}</td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{f.ic_ir ? f.ic_ir.toFixed(2) : "-"}</td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{f.annual_return ? (f.annual_return * 100).toFixed(2) + "%" : "-"}</td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{f.sharpe_ratio ? f.sharpe_ratio.toFixed(2) : "-"}</td>
                          <td className="px-4 py-3">
                            <button onClick={(e) => { e.stopPropagation(); handleDeleteFactor(f.id); }} className="text-red-600 hover:text-red-700 p-1">
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* IC 分析 */}
            {factorSubTab === "ic" && selectedFactor && (
              <div className="space-y-6">
                <button onClick={() => fetchICAnalysis()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行 IC 分析</button>
                {analysisLoading === "ic" && <div className="text-slate-500">加载中...</div>}
                {icData && (
                  <>
                    <div className="grid grid-cols-4 gap-4">
                      <StatCard label="IC 均值" value={(icData.ic_mean * 100).toFixed(2) + "%"} positive={icData.ic_mean > 0} />
                      <StatCard label="ICIR" value={icData.ic_ir.toFixed(2)} positive={icData.ic_ir > 0} />
                      <StatCard label="T 统计量" value={icData.t_stat.toFixed(2)} />
                      <StatCard label="样本数" value={icData.sample_size.toString()} />
                    </div>
                    {icData.ic_series.length > 0 && (
                      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
                        <h3 className="text-lg font-semibold mb-4">IC 时序</h3>
                        <LineChart data={icData.ic_series.map(d => ({ x: d.trade_date, y: d.ic }))} xAxisLabel="日期" yAxisLabel="IC" width={800} height={300} />
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* 换手率 */}
            {factorSubTab === "turnover" && selectedFactor && (
              <div className="space-y-6">
                <button onClick={() => fetchTurnover()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行换手率分析</button>
                {analysisLoading === "turnover" && <div className="text-slate-500">加载中...</div>}
                {turnoverData && (
                  <div className="grid grid-cols-2 gap-4">
                    <StatCard label="平均换手率" value={(turnoverData.avg_turnover * 100).toFixed(2) + "%"} />
                    <StatCard label="数据点数" value={turnoverData.turnover_series.length.toString()} />
                  </div>
                )}
              </div>
            )}

            {/* 衰减分析 */}
            {factorSubTab === "decay" && selectedFactor && (
              <div className="space-y-6">
                <button onClick={() => fetchDecay(20)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行衰减分析</button>
                {analysisLoading === "decay" && <div className="text-slate-500">加载中...</div>}
                {decayData && (
                  <div className="grid grid-cols-2 gap-4">
                    <StatCard label="初始 IC" value={(decayData.ic_decay[0]?.ic_mean * 100).toFixed(2) + "%"} />
                    <StatCard label="半衰期" value={`${decayData.half_life} 天`} />
                  </div>
                )}
              </div>
            )}

            {/* 分层回测 */}
            {factorSubTab === "layered" && selectedFactor && (
              <div className="space-y-6">
                <button onClick={() => fetchBacktest()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行分层回测</button>
                {backtestData && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <StatCard label="多空收益" value={(backtestData.long_short_return * 100).toFixed(2) + "%"} positive={backtestData.long_short_return > 0} />
                      <StatCard label="分层数" value={backtestData.layers.toString()} />
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
                      <h3 className="text-lg font-semibold mb-4">各层收益</h3>
                      <div className="grid grid-cols-5 gap-2">
                        {Object.entries(backtestData.final_equity).map(([layer, equity]) => (
                          <div key={layer} className="text-center p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
                            <div className="text-xs text-slate-500">{layer}</div>
                            <div className={`text-lg font-bold ${Number(equity) > 1 ? "text-green-600" : "text-red-600"}`}>{((Number(equity) - 1) * 100).toFixed(2)}%</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* 组合优化 */}
        {mainTab === "optimizer" && (
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold mb-4">组合优化器</h2>
            <div className="grid grid-cols-3 gap-4 mb-6">
              {OPTIMIZER_TYPES.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSelectedOptimizer(opt.value)}
                  className={`p-3 rounded-lg border text-sm ${selectedOptimizer === opt.value ? "border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-600" : "border-slate-200 dark:border-slate-700"}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button onClick={handleOptimize} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行优化</button>
            {optimizeResult && (
              <div className="mt-6 grid grid-cols-3 gap-4">
                <StatCard label="预期收益" value={(optimizeResult.expected_return * 100).toFixed(2) + "%"} />
                <StatCard label="波动率" value={(optimizeResult.volatility * 100).toFixed(2) + "%"} />
                <StatCard label="夏普比率" value={optimizeResult.sharpe_ratio?.toFixed(2) || "-"} />
              </div>
            )}
          </div>
        )}

        {/* 策略管理 */}
        {mainTab === "strategies" && (
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold mb-4">策略管理</h2>
            <div className="space-y-4">
              {strategies.map((s) => (
                <div key={s.id} className="p-4 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center">
                  <div>
                    <div className="font-medium text-slate-900 dark:text-white">{s.name}</div>
                    <div className="text-sm text-slate-500">{s.strategy_type} | 调仓：{s.rebalance_frequency}</div>
                  </div>
                  <button onClick={() => handleGenerateSignals(s.id)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">生成信号</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 量化回测 */}
        {mainTab === "backtest" && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold mb-4">量化回测</h2>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <input type="date" value={dateRange.start} onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700" />
                <input type="date" value={dateRange.end} onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700" />
              </div>
              <button onClick={handleRunBacktest} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">运行回测</button>
            </div>
            {backtestResult && (
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold mb-4">回测结果</h3>
                <div className="grid grid-cols-4 gap-4">
                  <StatCard label="总收益" value={(backtestResult.total_return).toFixed(2) + "%"} positive={backtestResult.total_return > 0} />
                  <StatCard label="年化收益" value={(backtestResult.annual_return).toFixed(2) + "%"} />
                  <StatCard label="夏普比率" value={backtestResult.sharpe_ratio?.toFixed(2) || "-"} />
                  <StatCard label="最大回撤" value={(backtestResult.max_drawdown || 0).toFixed(2) + "%"} positive={false} />
                  <StatCard label="波动率" value={(backtestResult.volatility || 0).toFixed(2) + "%"} />
                  <StatCard label="胜率" value={(backtestResult.win_rate || 0).toFixed(2) + "%"} />
                  <StatCard label="总交易数" value={backtestResult.total_trades.toString()} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* 风险管理 */}
        {mainTab === "risk" && (
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold mb-4">风险管理</h2>
            <p className="text-slate-500">风险管理功能需要接入真实持仓数据，当前为演示版本。</p>
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div className="text-sm text-green-800 dark:text-green-200">当前风险等级：低</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${active ? "bg-blue-600 text-white" : "bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300"}`}>
      {icon}
      {label}
    </button>
  );
}

function SubTabButton({ active, onClick, label, disabled }: { active: boolean; onClick: () => void; label: string; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled} className={`px-4 py-2 rounded-lg text-sm font-medium ${active ? "bg-blue-600 text-white" : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}>
      {label}
    </button>
  );
}

function StatCard({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="text-center p-4 bg-slate-50 dark:bg-slate-700 rounded-lg">
      <div className="text-sm text-slate-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${positive === true ? "text-green-600" : positive === false ? "text-red-600" : "text-slate-900 dark:text-white"}`}>{value}</div>
    </div>
  );
}