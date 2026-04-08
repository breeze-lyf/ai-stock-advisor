import api from "@/shared/api/client";

export interface EconomicEvent {
    id: string;
    event_name: string;
    country: string;
    event_date: string;
    event_time?: string;
    importance: number;
    event_type: string;
    actual?: string;
    forecast?: string;
    previous?: string;
    impact?: string;
}

export interface EarningsEvent {
    id: string;
    ticker: string;
    company_name: string;
    report_date: string;
    report_time?: string;
    quarter?: string;
    fiscal_year?: number;
    eps_estimate?: number;
    eps_actual?: number;
    revenue_estimate?: number;
}

export interface CalendarAlert {
    id: string;
    user_id: string;
    alert_type: string;
    ticker?: string;
    country?: string;
    importance_min: number;
    remind_before_minutes: number;
    created_at: string;
}

export async function getEconomicEvents(
    filters: {
        start_date?: string;
        end_date?: string;
        country?: string;
        importance?: number;
        event_type?: string;
        limit?: number;
    } = {},
    limit = 50
): Promise<{ status: string; count: number; events: EconomicEvent[] }> {
    const response = await api.get(`/api/v1/calendar/economic`, {
        params: { ...filters, limit },
    });
    return response.data;
}

export async function getHighImpactEvents(
    daysAhead = 7
): Promise<{ status: string; count: number; events: EconomicEvent[] }> {
    const response = await api.get(`/api/v1/calendar/economic/high-impact`, {
        params: { days_ahead: daysAhead },
    });
    return response.data;
}

export async function getEarningsEvents(
    filters: {
        tickers?: string;
        start_date?: string;
        end_date?: string;
        limit?: number;
    } = {},
    limit = 50
): Promise<{ status: string; count: number; events: EarningsEvent[] }> {
    const response = await api.get(`/api/v1/calendar/earnings`, {
        params: { ...filters, limit },
    });
    return response.data;
}

export async function getPortfolioEarnings(
    daysAhead = 14
): Promise<{ status: string; count: number; events: EarningsEvent[] }> {
    const response = await api.get(`/api/v1/calendar/earnings/portfolio`, {
        params: { days_ahead: daysAhead },
    });
    return response.data;
}

export async function getMegaCapEarnings(
    daysAhead = 30
): Promise<{ status: string; count: number; events: EarningsEvent[] }> {
    const response = await api.get(`/api/v1/calendar/earnings/mega-cap`, {
        params: { days_ahead: daysAhead },
    });
    return response.data;
}

export async function getEventsByCountry(
    countries: string[],
    daysAhead = 14
): Promise<{ status: string; countries: string[]; events: EconomicEvent[] }> {
    const response = await api.get(`/api/v1/calendar/events/by-country`, {
        params: { countries: countries.join(","), days_ahead: daysAhead },
    });
    return response.data;
}

export async function getUserAlerts(): Promise<{ status: string; alerts: CalendarAlert[] }> {
    const response = await api.get(`/api/v1/calendar/alerts`);
    return response.data;
}

export async function createAlert(
    alertType: "economic" | "earnings",
    options: {
        ticker?: string;
        country?: string;
        importance_min?: number;
        remind_before_minutes?: number;
    } = {}
): Promise<{ status: string; alert: CalendarAlert }> {
    const response = await api.post(`/api/v1/calendar/alerts`, undefined, {
        params: {
            alert_type: alertType,
            ...options,
        },
    });
    return response.data;
}
