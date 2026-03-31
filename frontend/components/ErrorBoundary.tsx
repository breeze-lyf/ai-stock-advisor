"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] gap-4 p-8 text-center">
          <h2 className="text-xl font-semibold text-destructive">页面出现错误</h2>
          <p className="text-muted-foreground text-sm max-w-md">
            {this.state.error?.message ?? "未知错误，请刷新页面或联系支持。"}
          </p>
          <Button variant="outline" onClick={this.handleReset}>
            重试
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
