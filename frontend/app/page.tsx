"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getPortfolio, analyzeStock, PortfolioItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TrendingUp, TrendingDown, RefreshCcw, Zap } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from 'react-markdown';

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Analysis State
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [activeTicker, setActiveTicker] = useState<string>("");

  const { isAuthenticated, login } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  useEffect(() => {
    // Small delay to allow AuthContext to load
    const timer = setTimeout(() => {
      if (!isAuthenticated && !localStorage.getItem("token")) {
        router.push("/login");
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, router]);

  const fetchData = async () => {
    // Prevent fetch if no token (double check)
    if (!localStorage.getItem("token")) return;

    setLoading(true);
    try {
      const data = await getPortfolio();
      setPortfolio(data);
    } catch (error) {
      console.error("Failed to fetch portfolio", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated]);

  const handleAnalyze = async (ticker: string) => {
    setAnalyzing(ticker);
    try {
      const result = await analyzeStock(ticker);
      setActiveTicker(ticker);
      setAnalysisResult(result.analysis);
      setIsDialogOpen(true);
    } catch (error) {
      console.error("Analysis failed", error);
      alert("Analysis failed. Please try again.");
    } finally {
      setAnalyzing(null);
    }
  };

  return (
    <div className="container mx-auto p-4 space-y-6">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Investment Advisor</h1>
          <p className="text-muted-foreground">AI-Powered Portfolio Insights</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchData} variant="outline" size="sm">
            <RefreshCcw className={clsx("mr-2 h-4 w-4", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button onClick={() => { localStorage.removeItem("token"); window.location.href = "/login"; }} variant="destructive" size="sm">
            Log out
          </Button>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${portfolio.reduce((acc, item) => acc + item.market_value, 0).toFixed(2)}
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>My Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Avg Cost</TableHead>
                <TableHead>Current Price</TableHead>
                <TableHead>Market Value</TableHead>
                <TableHead>Unrealized P&L</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {portfolio.map((item) => (
                <TableRow key={item.ticker}>
                  <TableCell className="font-medium">{item.ticker}</TableCell>
                  <TableCell>{item.quantity}</TableCell>
                  <TableCell>${item.avg_cost.toFixed(2)}</TableCell>
                  <TableCell>${item.current_price.toFixed(2)}</TableCell>
                  <TableCell>${item.market_value.toFixed(2)}</TableCell>
                  <TableCell className={clsx(
                    item.unrealized_pl >= 0 ? "text-green-600" : "text-red-600",
                    "font-bold"
                  )}>
                    {item.unrealized_pl >= 0 ? "+" : ""}{item.unrealized_pl.toFixed(2)} ({item.pl_percent.toFixed(2)}%)
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleAnalyze(item.ticker)}
                      disabled={analyzing === item.ticker}
                    >
                      <Zap className={clsx("mr-2 h-4 w-4 fill-yellow-500 text-yellow-500", analyzing === item.ticker && "animate-pulse")} />
                      {analyzing === item.ticker ? "Thinking..." : "Analyze"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {portfolio.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-10 text-muted-foreground">
                    No positions found. Use the API or wait for UI update to add.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>AI Analysis: {activeTicker}</DialogTitle>
            <DialogDescription>
              Generated by Gemini 1.5 Flash based on real-time market data.
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60svh] p-4 border rounded-md bg-slate-50 dark:bg-slate-900">
            <div className="prose dark:prose-invert text-sm">
              <ReactMarkdown>
                {analysisResult || ""}
              </ReactMarkdown>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
