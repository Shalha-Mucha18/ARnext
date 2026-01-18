"use client";

import { useEffect, useRef, useState } from "react";
import MessageContent from "@/components/MessageContent";
import ToastNotification from "@/components/ToastNotification";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// --- Types ---

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type SalesMetricsResponse = {
  current_month: {
    month: string;
    order_count: number;
    qty: number;
    revenue: number;
  };
  last_12_months: Array<{
    month: string;
    order_count: number;
    qty: number;
    revenue: number;
  }>;
};

type RegionContributionResponse = {
  top_regions: { name: string; quantity: number; orders: number }[];
  bottom_regions: { name: string; quantity: number; orders: number }[];
  total_volume: number;
};

type CreditSalesRatioResponse = {
  month: string;
  credit: { percentage: number; revenue: number; order_count: number };
  cash: { percentage: number; revenue: number; order_count: number };
  both: { percentage: number; revenue: number; order_count: number };
  other: { percentage: number; revenue: number; order_count: number };
  total_revenue: number;
};

type ConcentrationRiskResponse = {
  concentration_ratio: number;
  top_10_customers: { name: string; quantity: number; percentage: number }[];
  total_quantity: number;
};

type TerritoryPerformanceResponse = {
  top_territories: { name: string; quantity: number; orders: number }[];
  bottom_territories: { name: string; quantity: number; orders: number }[];
};


type YtdStatsResponse = {
  current_ytd: {
    total_orders: number;
    total_quantity: number;
    total_revenue: number;
    period_start: string;
    period_end: string;
    year?: number;
  };
  last_ytd: {
    total_orders: number;
    total_quantity: number;
    total_revenue: number;
    period_start: string;
    period_end: string;
    year?: number;
  };
  growth_metrics: {
    order_growth_pct: number;
    quantity_growth_pct: number;
    revenue_growth_pct: number;
    order_change: number;
    quantity_change: number;
    revenue_change: number;
  };
};

type ForecastChartPoint = {
  month: string;
  actual: number | null;
  forecast: number | null;
};

type ForecastResponse = {
  global_chart: ForecastChartPoint[];
  items_charts: any[];
  territories_charts: any[];
};

// --- Helpers ---

const makeId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
};

const formatCurrency = (val: number) => {
  if (val >= 1000000) return `${(val / 1000000).toFixed(2)}M`;
  if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
  return val.toString();
};

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

// --- Components ---

const Sidebar = ({ activeSection, setActiveSection, selectedUnit }: { activeSection: string, setActiveSection: (s: string) => void, selectedUnit: string }) => {
  const [imgError, setImgError] = useState(false);

  // Reset error state when unit changes to try loading new logo
  useEffect(() => {
    setImgError(false);
  }, [selectedUnit]);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-container">
          {selectedUnit && !imgError ? (
            <img
              key={selectedUnit} // Force re-render on unit change
              src={`/logos/${selectedUnit}.png`}
              alt="Unit Logo"
              className="unit-logo-img"
              onError={() => setImgError(true)}
              style={{ display: 'block' }}
            />
          ) : (
            <div className="logo-badge">AR</div>
          )}
        </div>
        <div>
          <div className="logo-text">ARNext</div>
          <div className="logo-sub">Intelligence</div>
        </div>
      </div>

      <div className="sidebar-nav">
        <div className="nav-label">Dashboard</div>
        <button
          className={`nav-item ${activeSection === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveSection('overview')}
        >
          <i className="fa-solid fa-chart-pie nav-icon"></i> Executive View
        </button>
        <button className="nav-item">
          <i className="fa-solid fa-globe nav-icon"></i> Market Intelligence
        </button>

        <div className="nav-label">AI Modules</div>
        <button
          className={`nav-item ${activeSection === 'forecast' ? 'active' : ''}`}
          onClick={() => setActiveSection('forecast')}
        >
          <i className="fa-solid fa-wand-magic-sparkles nav-icon"></i> Predictive Forecast
        </button>
        <button className="nav-item">
          <i className="fa-solid fa-microscope nav-icon"></i> Smart Diagnostics
        </button>

        <div className="nav-label">System</div>
        <button className="nav-item">
          <i className="fa-solid fa-database nav-icon"></i> Data Sources
        </button>
      </div>

      <div className="user-profile">
        <div className="user-card">
          <div className="avatar">BC</div>
          <div className="user-info">
            <div className="user-name">Bakhtiar C.</div>
            <div className="user-status">● Online</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

// --- Main Page ---

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([{
    id: "welcome",
    role: "assistant",
    content: "Ready to analyze your revenue data.",
  }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'info' | 'warning' | 'error' | 'success' } | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  // Theme Handling
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Derived colors for charts/inline styles ensuring visibility
  const textColor = theme === 'light' ? '#000000' : '#ffffff';
  const mutedColor = theme === 'light' ? '#525252' : '#94a3b8';
  const gridColor = theme === 'light' ? '#e5e7eb' : '#334155';
  const tooltipBg = theme === 'light' ? '#ffffff' : '#0f172a';
  const tooltipBorder = theme === 'light' ? '#e2e8f0' : '#1e293b';

  type SectionType = 'overview' | 'forecast';
  const [activeSection, setActiveSection] = useState<string>('overview'); // Using string to allow placeholders

  // Data States
  const [salesMetrics, setSalesMetrics] = useState<SalesMetricsResponse | null>(null);
  const [regionalData, setRegionalData] = useState<RegionContributionResponse | null>(null);
  const [areaData, setAreaData] = useState<any>(null);
  const [customerData, setCustomerData] = useState<any>(null);
  const [creditRatio, setCreditRatio] = useState<CreditSalesRatioResponse | null>(null);
  const [concentrationRisk, setConcentrationRisk] = useState<ConcentrationRiskResponse | null>(null);
  const [territoryPerformance, setTerritoryPerformance] = useState<TerritoryPerformanceResponse | null>(null);
  const [ytdStats, setYtdStats] = useState<YtdStatsResponse | null>(null);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);

  // AI Insights States
  const [regionalInsights, setRegionalInsights] = useState<string | null>(null);
  const [ytdInsights, setYtdInsights] = useState<string | null>(null);
  const [territoryInsights, setTerritoryInsights] = useState<string | null>(null);
  const [concentrationInsights, setConcentrationInsights] = useState<string | null>(null);
  const [creditInsights, setCreditInsights] = useState<string | null>(null);
  const [forecastInsights, setForecastInsights] = useState<string | null>(null);
  const [areaInsights, setAreaInsights] = useState<string | null>(null);
  const [insightsLoading, setInsightsLoading] = useState<{ [key: string]: boolean }>({});

  const [units, setUnits] = useState<any[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  const [availableMonths, setAvailableMonths] = useState<any[]>([]);
  const [notification, setNotification] = useState<string>("");
  const [selectedForecastItem, setSelectedForecastItem] = useState<string | null>(null);
  const [selectedForecastTerritory, setSelectedForecastTerritory] = useState<string | null>(null);

  const endRef = useRef<HTMLDivElement | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  // Scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, isChatOpen]);

  // Load Units (with Cache)
  useEffect(() => {
    const fetchUnits = async () => {
      // 1. Try Cache First
      try {
        const cached = localStorage.getItem("units_cache");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setUnits(parsed);
            if (!selectedUnit) setSelectedUnit(parsed[0].unit_id);
          }
        }
      } catch (e) { console.error("Cache read error", e); }

      // 2. Fetch Fresh Data
      try {
        const res = await fetch(`${apiBase}/v1/units`);
        if (res.ok) {
          const data = await res.json();
          setUnits(data);
          localStorage.setItem("units_cache", JSON.stringify(data));

          // Set default only if not set yet (fetching might be faster than effect or race conditions)
          // But strict React strict mode might cause issues, safe check:
          if (data.length > 0) {
            // If we didn't have a selected unit yet (e.g. invalid cache), set it now
            // Or if we rely on state updates, we can just let user selection persist if valid.
            // For simplicity, defaulting to first if empty is fine.
            // Logic: If selectedUnit is empty, set it.
            // Note: can't easily check 'selectedUnit' inside async closure without ref or functional update,
            // but `selectedUnit` is a dependency of other effects, not this one.
            // We'll trust the visual selection.
            // Ideally we check if `selectedUnit` value exists in new data.
          }
          // Use state setter callback if strictly needed, but here simple set is okay for typical flow.
          if (data.length > 0 && !localStorage.getItem("units_selected_id")) {
            setSelectedUnit(data[0].unit_id);
          }
        }
      } catch (e) { console.error("Units error", e); }
    };
    fetchUnits();
  }, [apiBase]); // removed 'selectedUnit' dependency to avoid loops

  const selectedUnitName = units.find(u => u.unit_id === selectedUnit)?.business_unit_name || "Select Business Unit...";

  const loadAvailableMonths = async () => {
    try {
      const url = new URL(`${apiBase}/v1/available-months`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setAvailableMonths(data.months);
      }
    } catch (e) {
      console.error("Failed to load months:", e);
    }
  };

  // Load available months when unit changes
  useEffect(() => {
    if (selectedUnit) {
      loadAvailableMonths();
    } else {
      setAvailableMonths([]);
      setSelectedMonth("");
    }
  }, [selectedUnit]);

  // Render Section replacement
  /*
     Replace lines 319-334 with:
  */
  // This section was commented out and is now removed as per instruction.

  // Load Data
  useEffect(() => {
    const controller = new AbortController();

    const loadSales = async () => {
      try {
        const url = new URL(`${apiBase}/v1/sales-metrics`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) setSalesMetrics(await res.json());
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadRegional = async () => {
      try {
        const url = new URL(`${apiBase}/v1/regional-insights`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setRegionalData(data);
          // Check if data is empty
          if (selectedMonth && (!data.top_regions || data.top_regions.length === 0)) {
            setNotification(`No regional data available for ${selectedMonth}`);
            setTimeout(() => setNotification(""), 5000);
          }
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadAreaData = async () => {
      try {
        const url = new URL(`${apiBase}/v1/area-insights`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setAreaData(data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') {
          console.error("Top Areas Load Error:", e);
          setAreaData({}); // Clear loading state on error
        }
      }
    };

    const loadCredit = async () => {
      try {
        const url = new URL(`${apiBase}/v1/credit-sales-ratio`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) setCreditRatio(await res.json());
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadCustomerData = async () => {
      try {
        const url = new URL(`${apiBase}/v1/top-customers`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setCustomerData(data); // Assuming state matches API format {"top_customers": ...} or fixed in state set
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadConcentration = async () => {
      try {
        const url = new URL(`${apiBase}/v1/concentration-risk`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) setConcentrationRisk(await res.json());
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadTerritories = async () => {
      try {
        const url = new URL(`${apiBase}/v1/territory-performance`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          console.log("Territory Performance Data:", data);
          setTerritoryPerformance(data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadForecast = async () => {
      try {
        const url = new URL(`${apiBase}/v1/forecast`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) setForecastData(await res.json());
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadYtdStats = async () => {
      try {
        const url = new URL(`${apiBase}/v1/ytd-sales`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) setYtdStats(await res.json());
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    if (activeSection === 'overview') {
      setIsDataLoading(true);
      Promise.all([loadSales(), loadRegional(), loadAreaData(), loadCredit(), loadCustomerData(), loadConcentration(), loadTerritories(), loadYtdStats()])
        .finally(() => setIsDataLoading(false));
    } else if (activeSection === 'forecast') {
      setIsDataLoading(true);
      loadForecast()
        .finally(() => setIsDataLoading(false));
    }

    return () => controller.abort();
  }, [activeSection, selectedUnit, selectedMonth, apiBase]);

  // AI Insights Handlers
  const loadRegionalInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, regional: true }));
    try {
      const url = new URL(`${apiBase}/v1/regional-insights/generate`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString(), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        console.log('Regional insights response:', data);
        setRegionalInsights(data.analysis || data.insights || data.error || "No insights available");
      } else {
        console.error('Regional insights failed:', res.status, res.statusText);
        setRegionalInsights(`Failed to generate insights: ${res.status} ${res.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load regional insights", e);
      setRegionalInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, regional: false }));
    }
  };

  const loadYtdInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, ytd: true }));
    try {
      const url = new URL(`${apiBase}/v1/ytd-sales-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setYtdInsights(data.insights || "No insights available");
      }
    } catch (e) {
      console.error("Failed to load YTD insights", e);
      setYtdInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, ytd: false }));
    }
  };

  const loadTerritoryInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, territory: true }));
    try {
      const url = new URL(`${apiBase}/v1/territory-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString(), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        console.log('Territory insights response:', data);
        setTerritoryInsights(data.analysis || data.insights || data.error || "No insights available");
      } else {
        console.error('Territory insights failed:', res.status, res.statusText);
        setTerritoryInsights(`Failed to generate insights: ${res.status} ${res.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load territory insights", e);
      setTerritoryInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, territory: false }));
    }
  };

  const loadConcentrationInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, concentration: true }));
    try {
      const url = new URL(`${apiBase}/v1/concentration-risk-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setConcentrationInsights(data.insights || "No insights available");
      }
    } catch (e) {
      console.error("Failed to load concentration insights", e);
      setConcentrationInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, concentration: false }));
    }
  };

  const loadCreditInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, credit: true }));
    try {
      const url = new URL(`${apiBase}/v1/credit-sales-insights/generate`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString(), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        // Handle nested insights object from backend
        const content = typeof data.insights === 'object' ? data.insights.analysis : data.insights;
        setCreditInsights(content || "No insights available");
      } else {
        setCreditInsights("Failed to generate insights");
      }
    } catch (e) {
      console.error("Failed to load credit insights", e);
      setCreditInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, credit: false }));
    }
  };

  const loadForecastInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, forecast: true }));
    try {
      const res = await fetch(`${apiBase}/v1/forecast/generate-insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit_id: selectedUnit || null })
      });
      if (res.ok) {
        const data = await res.json();
        setForecastInsights(data.insights);
      }
    } catch (e) {
      console.error("Failed to load forecast insights:", e);
    } finally {
      setInsightsLoading(prev => ({ ...prev, forecast: false }));
    }
  };

  const loadCustomerData = async () => {
    try {
      const url = new URL(`${apiBase}/v1/top-customers`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      if (selectedMonth) url.searchParams.append("month", selectedMonth);
      else if (selectedYear) url.searchParams.append("year", selectedYear);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setCustomerData(data);
      }
    } catch (e) {
      console.error("Failed to load customer data:", e);
    }
  };

  const loadAreaInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, area: true }));
    try {
      const res = await fetch(`${apiBase}/v1/area-insights/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit_id: selectedUnit || null })
      });
      if (res.ok) {
        const data = await res.json();
        setAreaInsights(data.analysis);
      }
    } catch (e) {
      console.error("Failed to load area insights:", e);
    } finally {
      setInsightsLoading(prev => ({ ...prev, area: false }));
    }
  };

  // Chat Handler
  const sendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    const userMessage: Message = { id: makeId(), role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, session_id: threadId ?? makeId() }),
      });
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      if (data.session_id) setThreadId(data.session_id);
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", content: data.answer || "No answer." }]);
    } catch {
      setError("Failed to reach API.");
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", content: "Error connecting to backend." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-layout">

      {/* --- Sidebar --- */}
      <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} selectedUnit={selectedUnit} />

      {/* --- Main Content Area --- */}
      <div className="main-area">

        {/* Notification Toast */}
        {notification && (
          <div style={{
            position: 'fixed',
            top: '80px',
            right: '20px',
            background: '#f59e0b',
            color: 'white',
            padding: '12px 20px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 9999,
            fontSize: '0.875rem',
            fontWeight: '500',
            animation: 'slideIn 0.3s ease-out'
          }}>
            <i className="fa-solid fa-circle-info" style={{ marginRight: '8px' }}></i>
            {notification}
          </div>
        )}

        {/* Header */}
        <header className="top-header">
          <div className="header-left">
            <div className="unit-selector">
              <div className="input-icon left">
                <i className="fa-solid fa-building text-blue"></i>
              </div>
              <select
                value={selectedUnit}
                onChange={(e) => setSelectedUnit(e.target.value)}
                className="unit-select"
              >
                <option value="" disabled>Select Business Unit...</option>
                {units.map(u => <option key={u.unit_id} value={u.unit_id}>{u.business_unit_name}</option>)}
              </select>
              <div className="input-icon right">
                <i className="fa-solid fa-chevron-down"></i>
              </div>
            </div>

            {/* Month Filter */}
            <div className="input-wrapper">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="unit-select"
                disabled={!selectedUnit}
              >
                <option value="">Current Month</option>
                {availableMonths.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>

              <div className="input-icon right">
                <i className="fa-solid fa-calendar"></i>
              </div>
            </div>
          </div>

          <div className="header-actions">
            <button
              className="ask-agent-btn"
              onClick={() => setIsChatOpen(true)}
            >
              <i className="fa-solid fa-sparkles"></i> Ask Agent
            </button>
            <div className="divider-vertical"></div>
            <button
              className="icon-btn"
              title="Toggle Theme"
              onClick={() => setTheme(prev => prev === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? <i className="fa-solid fa-moon"></i> : <i className="fa-solid fa-sun text-warning"></i>}
            </button>
            <button className="icon-btn">
              <i className="fa-regular fa-bell"></i>
              <span className="notification-dot"></span>
            </button>
          </div>
        </header>


        {/* Scrollable Dashboard Content */}
        <div className={`content-scroll ${isDataLoading ? 'blur-content' : ''}`}>


          {/* EXECUTIVE OVERVIEW */}
          {activeSection === 'overview' && (
            <>
              {/* Metrics Row */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel">
                  <div className="panel-header"><h2>Current YTD Volume</h2></div>
                  <div className="metric-value-row">
                    <span className="metric-value" style={{ color: textColor }}>
                      {ytdStats ? ytdStats.current_ytd.total_quantity.toLocaleString() : '...'}
                    </span>
                    <span className="metric-unit" style={{ color: mutedColor }}>MT</span>
                  </div>
                  {ytdStats && (
                    <div className={`metric-badge ${ytdStats.growth_metrics.quantity_growth_pct >= 0 ? 'badge-green' : 'badge-red'}`}>
                      {ytdStats.growth_metrics.quantity_growth_pct > 0 ? '+' : ''}{ytdStats.growth_metrics.quantity_growth_pct.toFixed(1)}% vs Prev YTD
                    </div>
                  )}
                </div>

                <div className="panel dashboard-panel">
                  <div className="panel-header"><h2>Current YTD Orders</h2></div>
                  <div className="metric-value-row">
                    <span className="metric-value" style={{ color: textColor }}>
                      {ytdStats ? ytdStats.current_ytd.total_orders.toLocaleString() : '...'}
                    </span>
                    <span className="metric-unit" style={{ color: mutedColor }}>Orders</span>
                  </div>
                  {ytdStats && (
                    <div className={`metric-badge ${ytdStats.growth_metrics.order_growth_pct >= 0 ? 'badge-green' : 'badge-red'}`}>
                      {ytdStats.growth_metrics.order_growth_pct > 0 ? '+' : ''}{ytdStats.growth_metrics.order_growth_pct.toFixed(1)}% vs Prev YTD
                    </div>
                  )}
                </div>

                <div className="panel dashboard-panel">
                  <div className="panel-header"><h2>Previous YTD Orders</h2></div>
                  <div className="metric-value-row">
                    <span className="metric-value" style={{ color: textColor }}>
                      {ytdStats ? ytdStats.last_ytd.total_orders.toLocaleString() : '...'}
                    </span>
                  </div>
                  {ytdStats && (
                    <div style={{ marginTop: '8px', fontSize: '0.75rem', color: mutedColor }}>
                      <div>{ytdStats.last_ytd.total_quantity.toLocaleString()} MT</div>
                      <div>Year: {ytdStats.last_ytd.year || 'N/A'}</div>
                    </div>
                  )}
                </div>

                <div className="panel dashboard-panel" style={{ borderLeft: '4px solid #10b981' }}>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>YTD Summary</h2>
                    <button
                      onClick={loadYtdInsights}
                      disabled={insightsLoading.ytd}
                      title="Generate AI Insights"
                      style={{
                        padding: '4px 8px',
                        background: ytdInsights ? '#10b981' : (insightsLoading.ytd ? '#64748b' : 'transparent'),
                        color: ytdInsights ? 'white' : '#10b981',
                        border: ytdInsights ? 'none' : '1px solid #10b981',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.ytd ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.ytd ? '⏳' : (ytdInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>

                  {ytdStats && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>Current YTD</div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor }}>{ytdStats.current_ytd.total_quantity.toLocaleString()} MT</div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>{ytdStats.current_ytd.total_orders} Orders</div>
                        </div>
                        <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>Previous YTD</div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor }}>{ytdStats.last_ytd.total_quantity.toLocaleString()} MT</div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>{ytdStats.last_ytd.total_orders} Orders</div>
                        </div>
                      </div>
                      <div className={`metric-badge ${ytdStats.growth_metrics.quantity_growth_pct >= 0 ? 'badge-green' : 'badge-red'}`} style={{ marginTop: '12px', display: 'inline-block' }}>
                        {ytdStats.growth_metrics.quantity_growth_pct > 0 ? '+' : ''}{ytdStats.growth_metrics.quantity_growth_pct.toFixed(1)}% Growth YoY
                      </div>
                    </div>
                  )}
                  {ytdInsights && (
                    <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '4px', borderLeft: '3px solid #10b981', position: 'relative' }}>
                      <button
                        onClick={() => setYtdInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.75rem', lineHeight: '1.5', color: textColor, paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{ytdInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              </div>




              {/* Chart + Insights */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel wide">
                  <div className="panel-header"><h2>Sales Trend Analysis</h2></div>
                  <div style={{ height: '300px' }}>
                    {salesMetrics?.last_12_months ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={salesMetrics.last_12_months}>
                          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                          <XAxis dataKey="month" stroke={mutedColor} tick={{ fontSize: 12 }} />
                          <YAxis stroke={mutedColor} tick={{ fontSize: 12 }} />
                          <RechartsTooltip contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }} itemStyle={{ color: textColor }} />
                          <Line type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={3} dot={false} />
                          <Line type="monotone" dataKey="qty" stroke="#10b981" strokeWidth={3} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : <div className="loading-text">Loading Trend...</div>}
                  </div>
                </div>

                <div className="panel dashboard-panel wide">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Top Regions (Volume)</h2>
                    <button
                      onClick={loadRegionalInsights}
                      disabled={insightsLoading.regional}
                      title="Generate Regional Insights"
                      style={{
                        padding: '4px 8px',
                        background: regionalInsights ? '#8b5cf6' : (insightsLoading.regional ? '#64748b' : 'transparent'),
                        color: regionalInsights ? 'white' : '#8b5cf6',
                        border: regionalInsights ? 'none' : '1px solid #8b5cf6',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.regional ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.regional ? '⏳' : (regionalInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>
                  <div className="rank-list">
                    {regionalData?.top_regions?.slice(0, 4).map((r, i) => (
                      <div key={i} className="rank-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div className="rank-badge" style={{ background: '#3b82f6', color: 'white' }}>{i + 1}</div>
                          <div>
                            <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor }}>{r.name}</div>
                            <div style={{ fontSize: '0.75rem', color: mutedColor }}>{r.orders} Orders</div>
                          </div>
                        </div>
                        <div style={{ fontWeight: '700', color: textColor, fontSize: '0.875rem' }}>{r.quantity.toLocaleString()} MT</div>
                      </div>
                    ))}
                  </div>
                  {regionalInsights && (
                    <div style={{ padding: '12px', background: 'rgba(139, 92, 246, 0.05)', borderRadius: '4px', marginTop: '12px', borderLeft: '3px solid #8b5cf6', position: 'relative' }}>
                      <button
                        onClick={() => setRegionalInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.75rem', lineHeight: '1.5', color: textColor, paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{regionalInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>

                {/* Top Areas */}
                <div className="panel dashboard-panel wide">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Top Areas (Volume)</h2>
                    <button
                      onClick={loadAreaInsights}
                      disabled={insightsLoading.area}
                      title="Generate Area Insights"
                      style={{
                        padding: '4px 8px',
                        background: areaInsights ? '#10b981' : (insightsLoading.area ? '#64748b' : 'transparent'),
                        color: areaInsights ? 'white' : '#10b981',
                        border: areaInsights ? 'none' : '1px solid #10b981',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.area ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.area ? '⏳' : (areaInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>
                  <div className="rank-list">
                    {areaData?.top_areas?.slice(0, 5).map((a: any, i: number) => (
                      <div key={i} className="rank-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div className="rank-badge" style={{ background: '#10b981', color: 'white' }}>{i + 1}</div>
                          <div>
                            <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor }}>{a.name}</div>
                            <div style={{ fontSize: '0.75rem', color: mutedColor }}>{a.orders} Orders</div>
                          </div>
                        </div>
                        <div style={{ fontWeight: '700', color: textColor, fontSize: '0.875rem' }}>{a.quantity.toLocaleString()} MT</div>
                      </div>
                    ))}
                    {!areaData && <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>Loading areas...</div>}
                    {areaData && (!areaData.top_areas || areaData.top_areas.length === 0) && (
                      <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>No area data available</div>
                    )}
                  </div>
                  {areaInsights && (
                    <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '4px', marginTop: '12px', borderLeft: '3px solid #10b981', position: 'relative' }}>
                      <button
                        onClick={() => setAreaInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.75rem', lineHeight: '1.5', color: textColor, paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{areaInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Concentration & Territories */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel wide">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Top 10 Customers</h2>
                    <button
                      onClick={loadConcentrationInsights}
                      disabled={insightsLoading.concentration}
                      title="Generate Customer Insights"
                      style={{
                        padding: '4px 8px',
                        background: concentrationInsights ? '#3b82f6' : (insightsLoading.concentration ? '#64748b' : 'transparent'),
                        color: concentrationInsights ? 'white' : '#3b82f6',
                        border: concentrationInsights ? 'none' : '1px solid #3b82f6',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.concentration ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.concentration ? '⏳' : (concentrationInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>

                  <div className="rank-list">
                    {concentrationRisk?.top_10_customers?.slice(0, 5).map((c, i) => (
                      <div key={i} className="rank-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div className="avatar" style={{ width: '32px', height: '32px', fontSize: '0.8rem', background: 'var(--brand-700)', border: 'none' }}>{c.name.slice(0, 2)}</div>
                          <div>
                            <div style={{ fontSize: '0.875rem', fontWeight: '500', color: textColor }}>{c.name}</div>
                            <div style={{ fontSize: '0.75rem', color: mutedColor }}>Share: {c.percentage.toFixed(1)}%</div>
                          </div>
                        </div>
                        <div style={{ fontWeight: '600', color: textColor, fontSize: '0.875rem' }}>{c.quantity.toLocaleString()} MT</div>
                      </div>
                    ))}
                    {!concentrationRisk && <div style={{ color: '#64748b', textAlign: 'center', fontSize: '0.875rem' }}>Loading Concentration...</div>}
                  </div>
                  {concentrationInsights && (
                    <div style={{ padding: '12px', borderTop: '1px solid var(--border-color)', background: 'rgba(59, 130, 246, 0.05)', position: 'relative' }}>
                      <button
                        onClick={() => setConcentrationInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.8rem', lineHeight: '1.5', color: textColor, whiteSpace: 'pre-wrap', paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{concentrationInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>

                <div className="panel dashboard-panel wide">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Territory Performance</h2>
                    <button
                      onClick={loadTerritoryInsights}
                      disabled={insightsLoading.territory}
                      title="Generate Territory Insights"
                      style={{
                        padding: '4px 8px',
                        background: territoryInsights ? '#10b981' : (insightsLoading.territory ? '#64748b' : 'transparent'),
                        color: territoryInsights ? 'white' : '#10b981',
                        border: territoryInsights ? 'none' : '1px solid #10b981',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.territory ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.territory ? '⏳' : (territoryInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>
                  <div className="rank-list">
                    {territoryPerformance?.top_territories?.slice(0, 5).map((t, i) => (
                      <div key={i} className="rank-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div className="rank-badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>{i + 1}</div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '500', color: textColor }}>{t.name}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontWeight: '600', color: textColor, fontSize: '0.875rem' }}>{t.quantity.toLocaleString()} MT</div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>
                            {t.orders} Orders
                          </div>
                        </div>
                      </div>
                    ))}
                    {!territoryPerformance && <div style={{ color: '#64748b', textAlign: 'center', fontSize: '0.875rem' }}>Loading Territories...</div>}
                    {territoryPerformance && (!territoryPerformance.top_territories || territoryPerformance.top_territories.length === 0) && (
                      <div style={{ color: '#64748b', textAlign: 'center', fontSize: '0.875rem' }}>No Data Available</div>
                    )}
                  </div>
                  {territoryInsights && (
                    <div style={{ padding: '12px', borderTop: '1px solid var(--border-color)', background: 'rgba(16, 185, 129, 0.05)', position: 'relative' }}>
                      <button
                        onClick={() => setTerritoryInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.8rem', lineHeight: '1.5', color: textColor, whiteSpace: 'pre-wrap', paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{territoryInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Credit Mix */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel full">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Credit vs Cash Split</h2>
                    <button
                      onClick={loadCreditInsights}
                      disabled={insightsLoading.credit}
                      title="Generate Credit Insights"
                      style={{
                        padding: '4px 8px',
                        background: creditInsights ? '#3b82f6' : (insightsLoading.credit ? '#64748b' : 'transparent'),
                        color: creditInsights ? 'white' : '#3b82f6',
                        border: creditInsights ? 'none' : '1px solid #3b82f6',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.credit ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.credit ? '⏳' : (creditInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>
                  {creditRatio ? (
                    <div style={{ display: 'flex', gap: '48px', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
                      <div style={{ width: '180px', height: '180px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={[
                                { name: 'Credit', value: creditRatio.credit.revenue },
                                { name: 'Cash', value: creditRatio.cash.revenue },
                                { name: 'Both', value: creditRatio.both.revenue }
                              ]}
                              innerRadius={55}
                              outerRadius={75}
                              paddingAngle={5}
                              dataKey="value"
                            >
                              <Cell key="cell-0" fill="#3b82f6" />
                              <Cell key="cell-1" fill="#10b981" />
                              <Cell key="cell-2" fill="#f59e0b" />
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div style={{ display: 'flex', gap: '32px' }}>
                        <div>
                          <div style={{ color: mutedColor, fontSize: '0.875rem' }}>Credit Sales</div>
                          <div style={{ color: '#3b82f6', fontSize: '1.5rem', fontWeight: '700' }}>{creditRatio.credit.percentage.toFixed(1)}%</div>
                          <div style={{ color: mutedColor, fontSize: '0.75rem' }}>{creditRatio.credit.revenue.toLocaleString()} MT</div>
                          <div style={{ color: mutedColor, fontSize: '0.7rem' }}>{creditRatio.credit.order_count} Orders</div>
                        </div>
                        <div>
                          <div style={{ color: mutedColor, fontSize: '0.875rem' }}>Cash Sales</div>
                          <div style={{ color: '#10b981', fontSize: '1.5rem', fontWeight: '700' }}>{creditRatio.cash.percentage.toFixed(1)}%</div>
                          <div style={{ color: mutedColor, fontSize: '0.75rem' }}>{creditRatio.cash.revenue.toLocaleString()} MT</div>
                          <div style={{ color: mutedColor, fontSize: '0.7rem' }}>{creditRatio.cash.order_count} Orders</div>
                        </div>
                        <div>
                          <div style={{ color: mutedColor, fontSize: '0.875rem' }}>Both (Credit+Cash)</div>
                          <div style={{ color: '#f59e0b', fontSize: '1.5rem', fontWeight: '700' }}>{creditRatio.both.percentage.toFixed(1)}%</div>
                          <div style={{ color: mutedColor, fontSize: '0.75rem' }}>{creditRatio.both.revenue.toLocaleString()} MT</div>
                          <div style={{ color: mutedColor, fontSize: '0.7rem' }}>{creditRatio.both.order_count} Orders</div>
                        </div>
                      </div>
                    </div>
                  ) : <div>Loading Credit Mix...</div>}

                  {creditInsights && (
                    <div style={{ padding: '12px', borderTop: '1px solid var(--border-color)', background: 'rgba(59, 130, 246, 0.05)', position: 'relative' }}>
                      <button
                        onClick={() => setCreditInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.8rem', lineHeight: '1.5', color: textColor, whiteSpace: 'pre-wrap', paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{creditInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* FORECAST VIEW */}
          {activeSection === 'forecast' && (
            <>
              {/* Global/Total Forecast */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel full">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Overall Volume Forecast</h2>
                    <button
                      onClick={loadForecastInsights}
                      disabled={insightsLoading.forecast}
                      title="Generate CEO Insights"
                      style={{
                        padding: '4px 8px',
                        background: forecastInsights ? '#8b5cf6' : (insightsLoading.forecast ? '#64748b' : 'transparent'),
                        color: forecastInsights ? 'white' : '#8b5cf6',
                        border: forecastInsights ? 'none' : '1px solid #8b5cf6',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.forecast ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.forecast ? '⏳' : (forecastInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>
                  <div style={{ height: '400px' }}>
                    {forecastData?.global_chart ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={forecastData.global_chart}>
                          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                          <XAxis dataKey="month" stroke={mutedColor} />
                          <YAxis stroke={mutedColor} />
                          <RechartsTooltip contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }} itemStyle={{ color: textColor }} />
                          <Legend />
                          <Line type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={3} name="Actual Volume" />
                          <Line type="monotone" dataKey="forecast" stroke="#8b5cf6" strokeWidth={3} strokeDasharray="5 5" name="AI Forecast" />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>Loading forecast data...</div>}
                  </div>

                  {/* AI Insights Display */}
                  {forecastInsights && (
                    <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(139, 92, 246, 0.05)', borderRadius: '4px', borderLeft: '3px solid #8b5cf6', position: 'relative' }}>
                      <button
                        onClick={() => setForecastInsights(null)}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          background: 'transparent',
                          border: 'none',
                          color: mutedColor,
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        title="Close insights"
                      >
                        ✕
                      </button>
                      <div style={{ fontSize: '0.8rem', lineHeight: '1.5', color: textColor, paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{forecastInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Item Forecast */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel full">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Item Forecast</h2>
                    {forecastData?.items_charts && forecastData.items_charts.length > 0 && (
                      <select
                        value={selectedForecastItem || ''}
                        onChange={(e) => setSelectedForecastItem(e.target.value)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: `1px solid ${gridColor}`,
                          background: 'var(--background-color)',
                          color: textColor,
                          fontSize: '0.875rem',
                          cursor: 'pointer'
                        }}
                      >
                        {forecastData.items_charts.map((item, idx) => (
                          <option key={idx} value={item.name}>{item.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div style={{ height: '400px' }}>
                    {forecastData?.items_charts && forecastData.items_charts.length > 0 ? (
                      (() => {
                        const selectedItem = forecastData.items_charts.find(i => i.name === selectedForecastItem) || forecastData.items_charts[0];
                        return (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={selectedItem.chart}>
                              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                              <XAxis dataKey="month" stroke={mutedColor} />
                              <YAxis stroke={mutedColor} />
                              <RechartsTooltip contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }} itemStyle={{ color: textColor }} />
                              <Legend />
                              <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={3} name="Actual" />
                              <Line type="monotone" dataKey="forecast" stroke="#f59e0b" strokeWidth={3} strokeDasharray="5 5" name="Forecast" />
                            </LineChart>
                          </ResponsiveContainer>
                        );
                      })()
                    ) : <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>No item forecast data available</div>}
                  </div>
                </div>
              </div>

              {/* Territory Forecast */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel full">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Territory Forecast</h2>
                    {forecastData?.territories_charts && forecastData.territories_charts.length > 0 && (
                      <select
                        value={selectedForecastTerritory || ''}
                        onChange={(e) => setSelectedForecastTerritory(e.target.value)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: `1px solid ${gridColor}`,
                          background: 'var(--background-color)',
                          color: textColor,
                          fontSize: '0.875rem',
                          cursor: 'pointer'
                        }}
                      >
                        {forecastData.territories_charts.map((terr, idx) => (
                          <option key={idx} value={terr.name}>{terr.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div style={{ height: '400px' }}>
                    {forecastData?.territories_charts && forecastData.territories_charts.length > 0 ? (
                      (() => {
                        const selectedTerritory = forecastData.territories_charts.find(t => t.name === selectedForecastTerritory) || forecastData.territories_charts[0];
                        return (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={selectedTerritory.chart}>
                              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                              <XAxis dataKey="month" stroke={mutedColor} />
                              <YAxis stroke={mutedColor} />
                              <RechartsTooltip contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }} itemStyle={{ color: textColor }} />
                              <Legend />
                              <Line type="monotone" dataKey="actual" stroke="#ef4444" strokeWidth={3} name="Actual" />
                              <Line type="monotone" dataKey="forecast" stroke="#8b5cf6" strokeWidth={3} strokeDasharray="5 5" name="Forecast" />
                            </LineChart>
                          </ResponsiveContainer>
                        );
                      })()
                    ) : <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>No territory forecast data available</div>}
                  </div>
                </div>
              </div>
            </>
          )}

        </div>
      </div>

      {/* --- Chat Overlay (Backdrop) --- */}
      <div
        className={`chat-overlay ${isChatOpen ? 'open' : ''}`}
        onClick={() => setIsChatOpen(false)}
      ></div>

      {/* --- Chat Panel (Attachment Style) --- */}
      <div className={`chat-sidebar ${isChatOpen ? 'open' : ''}`}>
        <div className="chat-header-styled">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="agent-icon-gradient">
              <i className="fa-solid fa-sparkles"></i>
            </div>
            <div>
              <h3 style={{ fontWeight: '700', fontSize: '1rem', color: textColor, margin: 0 }}>AR Agent</h3>
              <div style={{ fontSize: '0.75rem', color: '#3b82f6' }}>Live Context Active</div>
            </div>
          </div>
          <button className="chat-close-btn" onClick={() => setIsChatOpen(false)}>&times;</button>
        </div>

        <div className="chat-body-styled">
          {messages.map((m, i) => (
            <div key={m.id} className={`chat-row ${m.role}`}>
              {m.role === 'assistant' && (
                <div className="agent-avatar-small">
                  <i className="fa-solid fa-robot"></i>
                </div>
              )}
              <div className={`chat-bubble-styled ${m.role}`}>
                <MessageContent content={m.content} role={m.role} />
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="chat-row assistant">
              <div className="agent-avatar-small"><i className="fa-solid fa-robot"></i></div>
              <div className="chat-bubble-styled assistant loading-pulse">
                Thinking...
              </div>
            </div>
          )}
          {messages.length === 1 && !isLoading && (
            <div style={{ padding: '20px', textAlign: 'center', color: mutedColor, fontSize: '0.8rem' }}>
              <i className="fa-solid fa-wand-magic-sparkles" style={{ fontSize: '2rem', marginBottom: '1rem', opacity: 0.5 }}></i>
              <p>I can analyze revenue, forecast trends, and spot risks.</p>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="chat-input-area">
          {messages.length > 1 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingBottom: '8px' }}>
              <button
                style={{ fontSize: '0.7rem', color: '#64748b', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => setMessages([{ id: "welcome", role: "assistant", content: "Ready to analyze your revenue data." }])}
              >
                Clear Chat
              </button>
            </div>
          )}
          {messages.length === 1 && (
            <div className="chat-suggestions">
              <button className="suggestion-chip" onClick={() => sendMessage("Show me today's revenue")}>
                Today's Revenue
              </button>
              <button className="suggestion-chip" onClick={() => sendMessage("Analyze top regions")}>
                Top Regions
              </button>
              <button className="suggestion-chip" onClick={() => sendMessage("Forecast for next month")}>
                Forecast Volume
              </button>
            </div>
          )}

          <form className="chat-composer-styled" onSubmit={(e) => { e.preventDefault(); void sendMessage(input); }}>
            <input
              placeholder="Ask anything about your data..."
              value={input}
              onChange={e => setInput(e.target.value)}
            />
            <button type="submit" disabled={isLoading || !input.trim()}>
              <i className="fa-solid fa-paper-plane"></i>
            </button>
          </form>
        </div>
      </div>

      {/* --- Floating Action Button --- */}
      <button
        className="fab-btn"
        onClick={() => setIsChatOpen(true)}
        title="Ask Agent"
      >
        <i className="fa-solid fa-sparkles"></i>
      </button>

      {toast && <ToastNotification message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>

  );
}
