"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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
  };
  sales_trend: Array<{
    month: string;
    order_count: number;
    qty: number;
  }>;
};

type RegionContributionResponse = {
  top_regions: { name: string; quantity: number; orders: number; uom?: string; percentage?: number; mom_percentage?: number | null; yo_percentage?: number | null }[];
  bottom_regions: { name: string; quantity: number; orders: number; uom?: string; percentage?: number; mom_percentage?: number | null; yo_percentage?: number | null }[];
  total_volume: number;
  error?: string;
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
  top_territories: { territory: string; uom: string; total_quantity: number; total_orders: number; quantity_percentage: number }[];
  bottom_territories?: { territory: string; uom: string; total_quantity: number; total_orders: number; quantity_percentage: number }[];
};


type YtdStatsResponse = {
  current_ytd: {
    total_orders: number;
    total_quantity: number;
    period_start: string;
    period_end: string;
    year?: number;
    month?: string;
    uom?: string;
  };
  last_ytd: {
    total_orders: number;
    total_quantity: number;
    period_start: string;
    period_end: string;
    year?: number;
    month?: string;
    uom?: string;
  };
  growth_metrics: {
    order_growth_pct: number;
    quantity_growth_pct: number;
    quantity_change: number;
  };
};

type MonthlySummaryResponse = {
  month: string;
  total_quantity: number;
  total_orders: number;
  uom?: string;
};

type ForecastChartPoint = {
  month: string;
  actual: number | null;
  forecast: number | null;
};

type ForecastResponse = {
  global_chart: ForecastChartPoint[];
  items_charts: { name: string; chart: ForecastChartPoint[] }[];
  territories_charts: { name: string; chart: ForecastChartPoint[] }[];
  unit_id: string | null;
};

type TopCustomersResponse = {
  top_customers: { name: string; orders: number; quantity: number; uom: string; percentage: number }[];
};

type AreaPerformanceResponse = {
  top_areas: { name: string; orders: number; quantity: number; uom: string; percentage: number }[];
};

interface MtdStatsResponse {
  current_month: {
    delivery_qty: number;
    total_orders: number;
    month?: string;
    year?: number;
    uom?: string;
  };
  previous_month: {
    delivery_qty: number;
    total_orders: number;
    month?: string;
    year?: number;
    uom?: string;
  };
  growth: {
    delivery_qty_pct: number;
    orders_pct: number;
  };
};

type Unit = {
  unit_id: string;
  business_unit_name: string;
};

type RFMCustomer = {
  customer_id: number;
  customer_name: string;
  Recency: number;
  Frequency: number;
  Monetary: number;
  R_rank_norm: number;
  F_rank_norm: number;
  M_rank_norm: number;
  RFM_Score: number;
  Customer_segment: string;
};

type RFMSegmentSummary = {
  segment: string;
  customer_count: number;
  total_orders: number;
  total_revenue: number;
  avg_rfm_score: number;
  customer_percentage: number;
  revenue_percentage: number;
};

type RFMAnalysisResponse = {
  customers: RFMCustomer[];
  segment_summary: RFMSegmentSummary[];
  metadata: {
    total_customers: number;
    total_transactions: number;
    total_revenue: number;
    analysis_date: string;
    unit_id: number | null;
    date_range: {
      start: string | null;
      end: string | null;
    };
  };
};

// --- Helpers ---

const makeId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
};

const formatCurrency = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '0';
  if (val >= 1000000) return `${(val / 1000000).toFixed(2)}M`;
  if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
  return val.toString();
};

const formatUom = (uom: string | undefined | null) => {
  if (!uom) return 'MT';
  return uom === 'Metric Tons' ? 'MT' : uom;
};

const _COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

// --- Components ---

const UnitLogo = ({ unit }: { unit: string }) => {
  const [error, setError] = useState(false);
  if (error || !unit) return <div className="logo-badge">AR</div>;
  return (
    // eslint-disable-next-line @next/next/no-img-alt
    <img
      src={`/logos/${unit}.png`}
      alt="Unit Logo"
      className="unit-logo-img"
      onError={() => setError(true)}
      style={{ display: 'block' }}
    />
  );
};

const Sidebar = ({
  activeSection,
  setActiveSection,
  selectedUnit,
  useFiscalYear: _useFiscalYear,
  setUseFiscalYear: _setUseFiscalYear
}: {
  activeSection: string,
  setActiveSection: (s: string) => void,
  selectedUnit: string,
  useFiscalYear: boolean,
  setUseFiscalYear: (v: boolean) => void
}) => {
  // UnitLogo component handles image error state internally with key reset
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-container">
          <UnitLogo unit={selectedUnit} key={selectedUnit} />
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
        <button
          className={`nav-item ${activeSection === 'market-intelligence' ? 'active' : ''}`}
          onClick={() => setActiveSection('market-intelligence')}
        >
          <i className="fa-solid fa-globe nav-icon"></i> Market Intelligence
        </button>

        <div className="nav-label">AI Modules</div>
        <button
          className={`nav-item ${activeSection === 'forecast' ? 'active' : ''}`}
          onClick={() => setActiveSection('forecast')}
        >
          <i className="fa-solid fa-wand-magic-sparkles nav-icon"></i> AI Forecast
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
            <div className="user-name">Blah</div>
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

  const [isChatOpen, setIsChatOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'info' | 'warning' | 'error' | 'success' } | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('light');

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


  const [activeSection, setActiveSection] = useState<string>('overview'); // Using string to allow placeholders

  // Data States
  const [salesMetrics, setSalesMetrics] = useState<SalesMetricsResponse | null>(null);
  const [regionalData, setRegionalData] = useState<RegionContributionResponse | null>(null);
  const [areaData, setAreaData] = useState<AreaPerformanceResponse | null>(null);
  const [customerData, setCustomerData] = useState<TopCustomersResponse | null>(null);
  const [creditRatio, setCreditRatio] = useState<CreditSalesRatioResponse | null>(null);
  const [_concentrationRisk, setConcentrationRisk] = useState<ConcentrationRiskResponse | null>(null);
  const [territoryPerformance, setTerritoryPerformance] = useState<TerritoryPerformanceResponse | null>(null);
  const [ytdStats, setYtdStats] = useState<YtdStatsResponse | null>(null);
  const [mtdStats, setMtdStats] = useState<MtdStatsResponse | null>(null);
  const [monthlySummary, setMonthlySummary] = useState<MonthlySummaryResponse | null>(null);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [rfmData, setRfmData] = useState<RFMAnalysisResponse | null>(null);

  // AI Insights States
  const [regionalInsights, setRegionalInsights] = useState<string | null>(null);
  const [ytdInsights, setYtdInsights] = useState<string | null>(null);
  const [mtdInsights, setMtdInsights] = useState<string | null>(null);
  const [territoryInsights, setTerritoryInsights] = useState<string | null>(null);
  const [concentrationInsights, setConcentrationInsights] = useState<string | null>(null);
  const [creditInsights, setCreditInsights] = useState<string | null>(null);
  const [forecastInsights, setForecastInsights] = useState<string | null>(null);
  const [areaInsights, setAreaInsights] = useState<string | null>(null);
  const [insightsLoading, setInsightsLoading] = useState<{ [key: string]: boolean }>({});

  const [units, setUnits] = useState<Unit[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  const [availableMonths, setAvailableMonths] = useState<{ value: string; label: string }[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");

  // Unit Search State
  const [unitSearch, setUnitSearch] = useState("");
  const [isUnitDropdownOpen, setIsUnitDropdownOpen] = useState(false);
  const [availableYears, setAvailableYears] = useState<string[]>([]);
  const [useFiscalYear, setUseFiscalYear] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('useFiscalYear');
      return saved === 'true';
    }
    return false;
  });
  const [notification, setNotification] = useState<string>("");
  const [selectedForecastItem, setSelectedForecastItem] = useState<string | null>(null);
  const [selectedForecastTerritory, setSelectedForecastTerritory] = useState<string | null>(null);

  const endRef = useRef<HTMLDivElement | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
            if (!selectedUnit) {
              setSelectedUnit(parsed[0].unit_id);
              setUnitSearch(parsed[0].business_unit_name);
            }
          }
        }
      } catch (e) { console.error("Cache read error", e); }

      // 2. Fetch Fresh Data
      try {
        const res = await fetch(`${apiBase}/api/v1/units/`);
        if (res.ok) {
          const response = await res.json();
          const data = response.data || response; // Unwrap StandardResponse
          setUnits(data);
          localStorage.setItem("units_cache", JSON.stringify(data));

          // Set default unit if none selected
          if (data.length > 0 && !selectedUnit) {
            setSelectedUnit(data[0].unit_id);
            setUnitSearch(data[0].business_unit_name);
          }
        }
      } catch (e) { console.error("Units error", e); }
    };
    fetchUnits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]); // removed 'selectedUnit' dependency to avoid loops

  const selectedUnitName = units.find(u => u.unit_id === selectedUnit)?.business_unit_name || "Select Business Unit...";

  // Sync search input with selection
  useEffect(() => {
    if (selectedUnitName && selectedUnitName !== "Select Business Unit...") {
      setUnitSearch(selectedUnitName);
    }
  }, [selectedUnitName]);

  // Load available months when unit or year changes
  useEffect(() => {
    if (selectedUnit && selectedYear) {
      // Generate 12 months for the selected year
      const months = [
        { value: `${selectedYear}-01`, label: 'January' },
        { value: `${selectedYear}-02`, label: 'February' },
        { value: `${selectedYear}-03`, label: 'March' },
        { value: `${selectedYear}-04`, label: 'April' },
        { value: `${selectedYear}-05`, label: 'May' },
        { value: `${selectedYear}-06`, label: 'June' },
        { value: `${selectedYear}-07`, label: 'July' },
        { value: `${selectedYear}-08`, label: 'August' },
        { value: `${selectedYear}-09`, label: 'September' },
        { value: `${selectedYear}-10`, label: 'October' },
        { value: `${selectedYear}-11`, label: 'November' },
        { value: `${selectedYear}-12`, label: 'December' }
      ];
      setAvailableMonths(months);
    } else {
      setAvailableMonths([]);
      setSelectedMonth("");
    }
  }, [selectedUnit, selectedYear]);

  // Generate available years based on fiscal year mode
  useEffect(() => {
    if (useFiscalYear) {
      // In fiscal year mode, only show current FY (2026 = FY 25-26)
      setAvailableYears(["2026"]);
      setSelectedYear("2026");
    } else {
      // In calendar year mode, show all years 2020-2026
      const years: string[] = [];
      for (let year = 2020; year <= 2026; year++) {
        years.push(year.toString());
      }
      setAvailableYears(years);
      setSelectedYear("2026");
    }
  }, [useFiscalYear]); // Re-run when fiscal year toggle changes

  // Persist fiscal year preference
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('useFiscalYear', useFiscalYear.toString());
    }
  }, [useFiscalYear]);

  // Render Section replacement
  // This section was commented out and is now removed as per instruction.

  // Load Data
  useEffect(() => {
    const controller = new AbortController();

    const loadSales = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/sales/metrics`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Add date filters
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month);
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setSalesMetrics(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadRegional = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/regional/regions`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Convert selectedMonth from "YYYY-MM" to integer month (1-12) and year
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month);
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (!res.ok) {
          const message = `${res.status} ${res.statusText}`;
          setRegionalData({ top_regions: [], bottom_regions: [], total_volume: 0, error: message });
          return;
        }
        const data = await res.json();
        const content = data.data || data;
        setRegionalData(content);
        // Check if data is empty
        if (selectedYear && (!content.top_regions || content.top_regions.length === 0)) {
          setNotification(`No regional data available for year ${selectedYear}`);
          setTimeout(() => setNotification(""), 5000);
        } else if (selectedMonth && (!content.top_regions || content.top_regions.length === 0)) {
          setNotification(`No regional data available for ${selectedMonth}`);
          setTimeout(() => setNotification(""), 5000);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') {
          console.error(e);
          setRegionalData({ top_regions: [], bottom_regions: [], total_volume: 0, error: e.message });
        }
      }
    };

    const loadAreaData = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/regional/areas`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Convert selectedMonth from "YYYY-MM" to separate month and year integers
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month); // Just the month number (1-12)
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          const content = data.data || data;
          setAreaData(content);
          // Check if data is empty
          if (selectedYear && (!content.top_areas || content.top_areas.length === 0)) {
            setNotification(`No area data available for year ${selectedYear}`);
            setTimeout(() => setNotification(""), 5000);
          } else if (selectedMonth && (!content.top_areas || content.top_areas.length === 0)) {
            setNotification(`No area data available for ${selectedMonth}`);
            setTimeout(() => setNotification(""), 5000);
          }
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') {
          console.error("Area Performance Load Error:", e);
          setAreaData(null); // Clear loading state on error
        }
      }
    };

    const loadCredit = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/analytics/credit-ratio`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        if (selectedMonth) {
          url.searchParams.append("month", selectedMonth);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setCreditRatio(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadCustomerData = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/analytics/top-customers`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Convert selectedMonth from "YYYY-MM" to separate month and year integers
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month); // Just the month number (1-12)
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          // API returns StandardResponse: {status, data: {top_customers}, message, errors}
          setCustomerData(data.data || data);
          // Check if data is empty
          const customers = data.data?.top_customers || data.top_customers;
          if (selectedYear && (!customers || customers.length === 0)) {
            setNotification(`No customer data available for year ${selectedYear}`);
            setTimeout(() => setNotification(""), 5000);
          } else if (selectedMonth && (!customers || customers.length === 0)) {
            setNotification(`No customer data available for ${selectedMonth}`);
            setTimeout(() => setNotification(""), 5000);
          }
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') {
          console.error("Customer Performance Load Error:", e);
        }
      }
    };

    const loadConcentration = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/analytics/concentration-risk`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (selectedMonth) url.searchParams.append("month", selectedMonth);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setConcentrationRisk(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadTerritories = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/regional/territories`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Convert selectedMonth from "YYYY-MM" to separate month and year integers
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month); // Just the month number (1-12)
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          const content = data.data || data;
          console.log("Territory Performance Data:", content);
          setTerritoryPerformance(content);
          // Check if data is empty
          if (selectedYear && (!content.top_territories || content.top_territories.length === 0)) {
            setNotification(`No territory data available for year ${selectedYear}`);
            setTimeout(() => setNotification(""), 5000);
          } else if (selectedMonth && (!content.top_territories || content.top_territories.length === 0)) {
            setNotification(`No territory data available for ${selectedMonth}`);
            setTimeout(() => setNotification(""), 5000);
          }
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadForecast = async () => {
      try {
        if (!selectedUnit) {
          setForecastData(null);
          return;
        }
        const url = new URL(`${apiBase}/api/v1/forecast`);
        url.searchParams.append("unit_id", selectedUnit);
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setForecastData(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };


    const loadYtdStats = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/sales/ytd`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
        if (useFiscalYear) url.searchParams.append("fiscal_year", "true");

        // Add date filters
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month);
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        console.log("Fetching YTD from:", url.toString()); // DEBUG
        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          console.log("YTD Data:", data); // DEBUG
          setYtdStats(data.data || data);
        } else {
          console.error("YTD Fetch Failed:", res.status, res.statusText);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadMtdStats = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/sales/mtd`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        // Convert selectedMonth from "YYYY-MM" to month (1-12) and year
        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month); // month as integer (1-12)
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          url.searchParams.append("year", selectedYear);
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setMtdStats(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadMonthlySummary = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/sales/monthly-summary`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        if (selectedMonth) {
          const [year, month] = selectedMonth.split('-');
          url.searchParams.append("month", month);
          url.searchParams.append("year", year);
        } else if (selectedYear) {
          // If Year selected (but no specific month), send year for "Monthly Average"
          url.searchParams.append("year", selectedYear);
        } else {
          // Default to current month if nothing selected
          const currentMonth = new Date().getMonth() + 1;
          const currentYear = new Date().getFullYear();
          url.searchParams.append("month", currentMonth.toString());
          url.searchParams.append("year", (selectedYear || currentYear).toString());
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setMonthlySummary(data.data || data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    const loadRFM = async () => {
      try {
        const url = new URL(`${apiBase}/api/v1/rfm/analysis`);
        if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

        if (selectedYear) {
          if (useFiscalYear) {
            const yearInt = parseInt(selectedYear);
            // Fiscal Year: July 1st of Prev Year to June 30th of Selected Year
            url.searchParams.append("start_date", `${yearInt - 1}-07-01`);
            url.searchParams.append("end_date", `${yearInt}-06-30`);
          } else {
            // Calendar Year: Jan 1st to Dec 31st
            url.searchParams.append("start_date", `${selectedYear}-01-01`);
            url.searchParams.append("end_date", `${selectedYear}-12-31`);
          }
        }

        const res = await fetch(url.toString(), { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setRfmData(data);
        }
      } catch (e) {
        if (e instanceof Error && e.name !== 'AbortError') console.error(e);
      }
    };

    if (activeSection === 'overview') {
      setIsDataLoading(true);
      Promise.all([loadSales(), loadRegional(), loadAreaData(), loadCredit(), loadCustomerData(), loadConcentration(), loadTerritories(), loadYtdStats(), loadMtdStats(), loadMonthlySummary()])
        .finally(() => setIsDataLoading(false));
    } else if (activeSection === 'forecast') {
      setIsDataLoading(true);
      loadForecast()
        .finally(() => setIsDataLoading(false));
    } else if (activeSection === 'market-intelligence') {
      setIsDataLoading(true);
      loadRFM()
        .finally(() => setIsDataLoading(false));
    }

    return () => controller.abort();
  }, [activeSection, selectedUnit, selectedMonth, selectedYear, useFiscalYear, apiBase]);

  // AI Insights Handlers
  const loadRegionalInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, regional: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/regional/insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString(), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        console.log('Regional insights response:', data);
        setRegionalInsights(data.data?.analysis || data.analysis || data.insights || data.error || "No insights available");
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
      const url = new URL(`${apiBase}/api/v1/sales/ytd-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      if (useFiscalYear) url.searchParams.append("fiscal_year", "true");
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        // Extract insights from the response
        const insightsData = data.data?.insights || data.insights || {};
        const insightsText = insightsData.analysis || insightsData || "No insights available";
        setYtdInsights(insightsText);
      } else {
        setYtdInsights(`Failed to generate insights: ${res.status} ${res.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load YTD insights", e);
      setYtdInsights("Failed to generate insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, ytd: false }));
    }
  };

  const loadMtdInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, mtd: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/sales/mtd-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

      // Convert selectedMonth from "YYYY-MM" to month (1-12) and year
      if (selectedMonth) {
        const [year, month] = selectedMonth.split('-');
        url.searchParams.append("month", month);
        url.searchParams.append("year", year);
      }

      const res = await fetch(url.toString());
      if (!res.ok) {
        console.warn(`MTD insights returned ${res.status}`);
        setMtdInsights("Insights temporarily unavailable");
        return;
      }
      const data = await res.json();
      // Extract insights from the response
      const insightsData = data.data?.insights || data.insights || {};
      const insightsText = insightsData.analysis || insightsData || "No insights available";
      setMtdInsights(insightsText);
    } catch (e) {
      console.error("Failed to load MTD insights", e);
      setMtdInsights("Insights temporarily unavailable");
    } finally {
      setInsightsLoading(prev => ({ ...prev, mtd: false }));
    }
  };

  const loadTerritoryInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, territory: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/regional/territory-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      if (selectedMonth) {
        const [y, m] = selectedMonth.split('-');
        url.searchParams.append("year", y);
        url.searchParams.append("month", m);
      }

      const res = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (res.ok) {
        const data = await res.json();
        setTerritoryInsights(data.data?.analysis || data.analysis || "No insights available");
      } else {
        console.error('Territory insights failed:', res.status);
        setTerritoryInsights("Failed to generate territory insights");
      }
    } catch (e) {
      console.error("Failed to load territory insights", e);
      setTerritoryInsights("Error generating insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, territory: false }));
    }
  };

  const loadConcentrationInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, concentration: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/analytics/concentration-risk-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        const insightsData = data.data?.insights || data.insights || {};
        const insightsText = typeof insightsData === 'string' ? insightsData : (insightsData.analysis || "No insights available");
        setConcentrationInsights(insightsText);
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
      const url = new URL(`${apiBase}/api/v1/analytics/credit-ratio`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      if (selectedMonth) {
        url.searchParams.append("month", selectedMonth);
      }
      url.searchParams.append("generate_insights", "true");

      const res = await fetch(url.toString(), { method: 'GET' });

      if (res.ok) {
        const data = await res.json();
        // Check for ai_insights (backend key) or other variants
        const insightsData = data.data?.ai_insights || data.data?.insights || data.insights || {};
        const insightsText = typeof insightsData === 'string' ? insightsData : (insightsData.analysis || "No insights available");
        setCreditInsights(insightsText);
      } else {
        console.error('Credit insights failed:', res.status);
        setCreditInsights("Failed to generate credit insights");
      }
    } catch (e) {
      console.error("Failed to load credit insights:", e);
      setCreditInsights("Error generating insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, credit: false }));
    }
  };


  const loadForecastInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, forecast: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/forecast/insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

      const res = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (res.ok) {
        const data = await res.json();
        const insightsData = data.data?.analysis || data.analysis || "No insights available";
        setForecastInsights(insightsData);
      } else {
        console.error('Forecast insights failed:', res.status);
        setForecastInsights("Failed to generate forecast insights");
      }
    } catch (e) {
      console.error("Failed to load forecast insights:", e);
      setForecastInsights("Error generating insights");
    } finally {
      setInsightsLoading(prev => ({ ...prev, forecast: false }));
    }
  };

  const loadCustomerData = useCallback(async () => {
    try {
      const url = new URL(`${apiBase}/api/v1/analytics/top-customers`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);

      // Convert selectedMonth from "YYYY-MM" to separate month and year integers
      if (selectedMonth) {
        const [year, month] = selectedMonth.split('-');
        url.searchParams.append("month", month); // Just the month number (1-12)
        url.searchParams.append("year", year);
      } else if (selectedYear) {
        url.searchParams.append("year", selectedYear);
      }

      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        const content = data.data || data;
        setCustomerData(content);
        // Check if data is empty
        const customers = content.top_customers;
        if (selectedYear && (!customers || customers.length === 0)) {
          setNotification(`No customer data available for year ${selectedYear}`);
          setTimeout(() => setNotification(""), 5000);
        } else if (selectedMonth && (!customers || customers.length === 0)) {
          setNotification(`No customer data available for ${selectedMonth}`);
          setTimeout(() => setNotification(""), 5000);
        }
      }
    } catch (e) {
      console.error("Failed to load customer data:", e);
    }
  }, [apiBase, selectedUnit, selectedMonth]);

  useEffect(() => {
    void loadCustomerData();
  }, [loadCustomerData]);

  const loadAreaInsights = async () => {
    setInsightsLoading(prev => ({ ...prev, area: true }));
    try {
      const url = new URL(`${apiBase}/api/v1/regional/area-insights`);
      if (selectedUnit) url.searchParams.append("unit_id", selectedUnit);
      if (selectedMonth) {
        const [y, m] = selectedMonth.split('-');
        url.searchParams.append("year", y);
        url.searchParams.append("month", m);
      }

      const res = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (res.ok) {
        const data = await res.json();
        setAreaInsights(data.data?.analysis || data.analysis || "No insights available");
      } else {
        console.error('Area insights failed:', res.status);
        setAreaInsights("Failed to generate area insights");
      }
    } catch (e) {
      console.error("Failed to load area insights:", e);
      setAreaInsights("Error generating insights");
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

    try {
      const res = await fetch(`${apiBase}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, session_id: threadId ?? makeId() }),
      });
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      if (data.session_id) setThreadId(data.session_id);
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", content: data.answer || "No answer." }]);
    } catch {
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", content: "Error connecting to backend." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-layout">

      {/* --- Sidebar --- */}
      <Sidebar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        selectedUnit={selectedUnit}
        useFiscalYear={useFiscalYear}
        setUseFiscalYear={setUseFiscalYear}
      />

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
            <div className="unit-selector" style={{ position: 'relative', width: '280px' }}>
              <div
                className="input-icon left"
                style={{ zIndex: 10, left: '12px' }}
              >
                <i className="fa-solid fa-building text-blue"></i>
              </div>
              <input
                type="text"
                placeholder="Search Business Unit..."
                className="unit-select cosmic-search"
                value={unitSearch}
                onChange={(e) => {
                  setUnitSearch(e.target.value);
                  setIsUnitDropdownOpen(true);
                }}
                onFocus={() => setIsUnitDropdownOpen(true)}
                onBlur={() => setTimeout(() => setIsUnitDropdownOpen(false), 200)}
              />
              <div
                className="input-icon right"
                style={{ right: '12px', cursor: 'pointer' }}
                onClick={() => setIsUnitDropdownOpen(!isUnitDropdownOpen)}
              >
                <i className={`fa-solid fa-chevron-${isUnitDropdownOpen ? 'up' : 'down'}`}></i>
              </div>

              {/* Cosmic Dropdown */}
              {isUnitDropdownOpen && (
                <div className="cosmic-dropdown">
                  {units.filter(u => {
                    const isExactMatch = selectedUnitName && unitSearch === selectedUnitName;
                    return isExactMatch || u.business_unit_name.toLowerCase().includes(unitSearch.toLowerCase());
                  }).length > 0 ? (
                    units.filter(u => {
                      const isExactMatch = selectedUnitName && unitSearch === selectedUnitName;
                      return isExactMatch || u.business_unit_name.toLowerCase().includes(unitSearch.toLowerCase());
                    }).map(u => (
                      <div
                        key={u.unit_id}
                        onClick={() => {
                          setSelectedUnit(u.unit_id);
                          setUnitSearch(u.business_unit_name);
                          setIsUnitDropdownOpen(false);
                        }}
                        className={`cosmic-item ${selectedUnit === u.unit_id ? 'selected' : ''}`}
                      >
                        <div className="dot-indicator"></div>
                        {u.business_unit_name}
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '12px', color: 'var(--muted)', fontSize: '0.85rem', textAlign: 'center' }}>
                      No units found
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Fiscal Year Toggle */}
            <button
              onClick={() => setUseFiscalYear(!useFiscalYear)}
              className={`filter-btn ${useFiscalYear ? 'active' : ''}`}
              title={useFiscalYear ? "Switch to Calendar Year" : "Switch to Fiscal Year (July-June)"}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '0 12px',
                height: '40px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                background: useFiscalYear ? 'rgba(59, 130, 246, 0.1)' : 'var(--panel-bg)',
                color: useFiscalYear ? '#3b82f6' : 'var(--text-color)',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              <i className={`fa-solid ${useFiscalYear ? 'fa-calendar-check' : 'fa-calendar'} ${useFiscalYear ? 'text-blue' : ''}`}></i>
              {useFiscalYear ? 'FY 25-26' : 'CY'}
            </button>

            {/* Year Filter */}
            <div className="input-wrapper">
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                className="unit-select"
                disabled={!selectedUnit}
              >
                {availableYears.map(y => {
                  let label = y;
                  if (useFiscalYear) {
                    const yr = parseInt(y);
                    const currentShort = y.slice(-2);
                    const prevShort = (yr - 1).toString().slice(-2);
                    // User requested "25-24" format (Current-Previous)
                    label = `${currentShort}-${prevShort}`;
                  }
                  return <option key={y} value={y}>{label}</option>
                })}
              </select>
            </div>

            {/* Month Filter */}
            <div className="input-wrapper">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="unit-select"
                disabled={!selectedUnit || !selectedYear}
              >
                <option value="">All Months</option>
                {availableMonths.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
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
              <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="panel dashboard-panel" style={{ borderLeft: '4px solid #10b981' }}>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2>{useFiscalYear ? 'Fiscal YTD Summary' : 'Year to Date Summary'}</h2>
                      <p style={{ fontSize: '0.75rem', color: mutedColor, margin: '4px 0 0 0', fontWeight: '400' }}>
                        Compares Jan 1 - Today vs. same period last year
                      </p>
                    </div>
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

                  {ytdStats && ytdStats.current_ytd && ytdStats.last_ytd && (
                    <div style={{ marginTop: '10px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>
                            {useFiscalYear ? 'Current FYTD' : 'Current Year'}
                          </div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '400', color: textColor }}>{ytdStats.current_ytd.total_quantity.toLocaleString()} {formatUom(ytdStats.current_ytd.uom)}</div>
                        </div>
                        <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>
                            {useFiscalYear ? 'Previous FYTD' : 'Same Period Last Year'}
                          </div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '300', color: textColor }}>{ytdStats.last_ytd.total_quantity.toLocaleString()} {formatUom(ytdStats.last_ytd.uom)}</div>
                        </div>
                      </div>
                      <div className={`metric-badge ${ytdStats.growth_metrics.quantity_growth_pct >= 0 ? 'badge-green' : 'badge-red'}`} style={{ marginTop: '12px', display: 'inline-block' }}>
                        {ytdStats.growth_metrics.quantity_growth_pct > 0 ? '+' : ''}{ytdStats.growth_metrics.quantity_growth_pct.toFixed(1)}% Growth vs {useFiscalYear ? 'PFYTD' : 'Last Year'}
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

                {/* MTD Summary Card */}
                <div className="panel dashboard-panel" style={{ borderLeft: '4px solid #3b82f6' }}>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2>Month to Date Summary</h2>
                      <p style={{ fontSize: '0.75rem', color: mutedColor, margin: '4px 0 0 0', fontWeight: '400' }}>
                        Compares {(() => {
                          if (selectedMonth) {
                            const [y, m] = selectedMonth.split('-');
                            const d = new Date(parseInt(y), parseInt(m) - 1);
                            return (
                              <span>
                                {d.toLocaleString('default', { month: 'short' })} 1 - End vs Previous Month
                                <br />
                                <span style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                                  (Full Month Comparison)
                                </span>
                              </span>
                            );
                          } else if (selectedYear) {
                            return `Jan 1 - Dec 31 ${selectedYear} (Monthly Avg)`;
                          }
                          // Current Month Logic
                          return (
                            <span>
                              {new Date().toLocaleString('default', { month: 'short' })} 1 - {new Date().toLocaleString('default', { month: 'short', day: 'numeric' })} vs Prev Month Same Period
                              <br />
                              <span style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                                (Apple-to-Apple: Comparing exact same day range)
                              </span>
                            </span>
                          );
                        })()}
                      </p>
                    </div>
                    <button
                      onClick={loadMtdInsights}
                      disabled={insightsLoading.mtd}
                      title="Generate AI Insights"
                      style={{
                        padding: '4px 8px',
                        background: mtdInsights ? '#3b82f6' : (insightsLoading.mtd ? '#64748b' : 'transparent'),
                        color: mtdInsights ? 'white' : '#3b82f6',
                        border: mtdInsights ? 'none' : '1px solid #3b82f6',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        cursor: insightsLoading.mtd ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {insightsLoading.mtd ? '⏳' : (mtdInsights ? '✓ Insights' : '✨ AI')}
                    </button>
                  </div>

                  {mtdStats && mtdStats.current_month && mtdStats.previous_month && (
                    <div style={{ marginTop: '10px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>
                            Current Month
                          </div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '400', color: textColor }}>
                            {mtdStats.current_month.delivery_qty.toLocaleString()} {formatUom(mtdStats.current_month.uom)}
                          </div>
                        </div>
                        <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
                          <div style={{ fontSize: '0.75rem', color: mutedColor, marginBottom: '4px' }}>
                            Previous Month
                          </div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '300', color: textColor }}>
                            {mtdStats.previous_month.delivery_qty.toLocaleString()} {formatUom(mtdStats.previous_month.uom)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {mtdInsights && (
                    <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(59, 130, 246, 0.05)', borderRadius: '4px', borderLeft: '3px solid #3b82f6', position: 'relative' }}>
                      <button
                        onClick={() => setMtdInsights(null)}
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
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{mtdInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>

                {/* Monthly Summary Card */}
                <div className="panel dashboard-panel" style={{ borderLeft: '4px solid #8b5cf6' }}>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2>Monthly Summary</h2>
                      <p style={{ fontSize: '0.75rem', color: mutedColor, margin: '4px 0 0 0', fontWeight: '400' }}>
                        performance metrics for the selected month
                      </p>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: mutedColor }}>
                      {monthlySummary?.month || 'No Data'}
                    </span>
                  </div>

                  {monthlySummary ? (
                    <div style={{ marginTop: '10px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>Total Quantity</div>
                          <div style={{ fontSize: '1rem', fontWeight: '500', color: textColor }}>
                            {(monthlySummary.total_quantity || 0).toLocaleString()} {formatUom(monthlySummary.uom)}
                          </div>
                        </div>
                        <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '15px' }}>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>Total Orders</div>
                          <div style={{ fontSize: '1rem', fontWeight: '500', color: textColor }}>
                            {(monthlySummary.total_orders || 0).toLocaleString()}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '20px', textAlign: 'center', color: mutedColor, fontSize: '0.875rem' }}>
                      Loading data...
                    </div>
                  )}
                </div>
              </div>




              {/* Chart + Insights */}
              <div className="dashboard-grid">
                <div className="panel dashboard-panel wide">
                  <div className="panel-header">
                    <div>
                      <h2>Sales Trend Analysis</h2>

                    </div>
                  </div>
                  <div style={{ height: '300px' }}>
                    {salesMetrics?.sales_trend ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={salesMetrics.sales_trend}>
                          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                          <XAxis dataKey="month" stroke={mutedColor} tick={{ fontSize: 12 }} />
                          <YAxis stroke={mutedColor} tick={{ fontSize: 12 }} />
                          <RechartsTooltip contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }} itemStyle={{ color: textColor }} />
                          <Line type="monotone" dataKey="qty" stroke="#10b981" strokeWidth={3} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : <div className="loading-text">Loading Trend...</div>}
                  </div>
                  <div style={{ marginTop: '10px', padding: '0 4px' }}>
                    <p style={{ fontSize: '0.75rem', color: mutedColor, margin: '0', fontWeight: '400', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.9rem' }}>📈</span> Visualizing delivery volume trends {selectedYear ? `for ${selectedYear}` : 'over time'}
                    </p>
                  </div>
                </div>

                <div className="panel dashboard-panel" style={{ gridColumn: 'span 2' }}>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Regional Performance</h2>
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
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'minmax(150px, 1fr) minmax(120px, 1fr) minmax(180px, 1.5fr) minmax(180px, 1.5fr) minmax(100px, 0.8fr)',
                        gap: '12px',
                        marginBottom: '8px',
                        padding: '0 4px',
                        fontSize: '0.7rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: mutedColor,
                        fontWeight: '600'
                      }}
                    >
                      <div>Region</div>
                      <div style={{ textAlign: 'right' }}>Sales Volume</div>
                      <div style={{ textAlign: 'right' }}>Growth Percentage vs Previous Month</div>
                      <div style={{ textAlign: 'right' }}>Growth Percentage vs Same Month Last Year</div>
                      <div style={{ textAlign: 'right' }}>Contribution</div>
                    </div>
                    {regionalData?.top_regions?.slice(0, 5).map((r, i) => {
                      const momValue = r.mom_percentage;
                      const yotValue = r.yo_percentage;
                      const momText = (momValue === null || momValue === undefined) ? "n/a" : `${Number(momValue).toFixed(1)}%`;
                      const yotText = (yotValue === null || yotValue === undefined) ? "n/a" : `${Number(yotValue).toFixed(1)}%`;
                      const qty = Number(r.quantity ?? 0);
                      const total = regionalData?.total_volume ?? 1;
                      return (
                        <div
                          key={`region-row-${i}`}
                          className="rank-row"
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'minmax(150px, 1fr) minmax(120px, 1fr) minmax(180px, 1.5fr) minmax(180px, 1.5fr) minmax(100px, 0.8fr)',
                            gap: '12px',
                            alignItems: 'center',
                            padding: '8px 4px'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                            <div className="rank-badge" style={{ background: '#3b82f6', color: 'white', flexShrink: 0 }}>{i + 1}</div>
                            <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={r.name}>{r.name}</div>
                          </div>

                          <div style={{ fontWeight: '700', color: textColor, fontSize: '0.875rem', textAlign: 'right' }}>
                            {qty.toLocaleString()} <span style={{ fontSize: '0.75rem', color: mutedColor }}>{r.uom || 'MT'}</span>
                          </div>

                          <div style={{ fontSize: '0.8rem', fontWeight: '600', color: textColor, textAlign: 'right' }}>{momText}</div>
                          <div style={{ fontSize: '0.8rem', fontWeight: '600', color: textColor, textAlign: 'right' }}>{yotText}</div>

                          <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#10b981', textAlign: 'right' }}>
                            {((qty / total) * 100).toFixed(1)}%
                          </div>
                        </div>
                      );
                    })}
                    {!regionalData && (
                      <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>
                        Loading regions...
                      </div>
                    )}
                    {regionalData && (!regionalData.top_regions || regionalData.top_regions.length === 0) && (
                      <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>
                        {regionalData.error ? `Regional data error: ${regionalData.error}` : "No regional data available"}
                      </div>
                    )}
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

                {/* Customers Performance (Added to Top Grid) */}
                <div className="panel dashboard-panel wide">
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>Customers Performance</h2>
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
                    <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr 160px 120px', padding: '0 0 8px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.75rem', fontWeight: '700', color: mutedColor, alignItems: 'center' }}>
                      <div></div> {/* Empty rank header for alignment */}
                      <div>Customer</div>
                      <div style={{ textAlign: 'right' }}>Sales Volume</div>
                      <div style={{ textAlign: 'right' }}>Contribution</div>
                    </div>

                    {customerData?.top_customers?.slice(0, 5).map((c, i) => (
                      <div key={i} className="rank-row" style={{ display: 'grid', gridTemplateColumns: '40px 1fr 160px 120px', alignItems: 'center', padding: '12px 0' }}>
                        <div className="rank-badge" style={{ background: '#3b82f6', color: 'white' }}>{i + 1}</div>
                        <div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' }} title={c.name}>{c.name}</div>
                          <div style={{ fontSize: '0.75rem', color: mutedColor }}>{c.orders} Orders</div>
                        </div>
                        <div style={{ fontSize: '0.875rem', fontWeight: '700', color: textColor, textAlign: 'right' }}>
                          {c.quantity.toLocaleString()} {c.uom || 'MT'}
                        </div>
                        <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#3b82f6', textAlign: 'right' }}>
                          {c.percentage}%
                        </div>
                      </div>
                    ))}
                    {!customerData && <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>Loading customers...</div>}
                    {customerData && (!customerData.top_customers || customerData.top_customers.length === 0) && (
                      <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>No customer data available</div>
                    )}
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
                      <div style={{ fontSize: '0.75rem', lineHeight: '1.5', color: textColor, whiteSpace: 'pre-wrap', paddingRight: '20px' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{concentrationInsights}</ReactMarkdown>
                      </div>
                    </div>
                  )}



                  <div style={{ marginTop: '4px', padding: '0 4px', borderTop: '1px solid var(--border-color)', paddingTop: '8px' }}>
                    <p style={{ fontSize: '0.75rem', color: mutedColor, margin: '0', fontWeight: '400', textAlign: 'right' }}>
                      {(() => {
                        if (selectedMonth) {
                          const [y, m] = selectedMonth.split('-');
                          const date = new Date(parseInt(y), parseInt(m) - 1);
                          return `for ${date.toLocaleString('default', { month: 'long', year: 'numeric' })}`;
                        } else if (selectedYear) {
                          return `for ${selectedYear}`;
                        }
                        return 'for current period';
                      })()}
                    </p>
                  </div>
                </div>



                {/* Areas & Territory Performance Row */}
                <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr', gridColumn: 'span 2' }}>
                  {/* Top Areas */}
                  <div className="panel dashboard-panel">
                    <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h2>Areas Performance</h2>
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
                    <div style={{ overflowX: 'auto' }}>
                      {areaData?.top_areas && areaData.top_areas.length > 0 ? (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                          <thead>
                            <tr style={{ borderBottom: `2px solid ${gridColor}` }}>
                              <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '60px' }}></th>
                              <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '15%' }}>Area Name</th>
                              <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '15%' }}>Sales Volume</th>
                              <th style={{ padding: '12px 8px', textAlign: 'center', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '25%' }}>Growth Percentage vs Previous Month</th>
                              <th style={{ padding: '12px 8px', textAlign: 'center', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '25%' }}>Growth Percentage vs same Month last Year</th>
                              <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: '600', color: mutedColor, fontSize: '0.75rem', textTransform: 'uppercase', width: '12%' }}>Contribution</th>
                            </tr>
                          </thead>
                          <tbody>
                            {areaData.top_areas.slice(0, 5).map((a, i) => {
                              const momValue = a.mom_percentage;
                              const yotValue = a.yo_percentage;
                              const momText = (momValue === null || momValue === undefined) ? "n/a" : `${Number(momValue).toFixed(1)}%`;
                              const yotText = (yotValue === null || yotValue === undefined) ? "n/a" : `${Number(yotValue).toFixed(1)}%`;
                              return (
                                <tr key={i} style={{ borderBottom: `1px solid ${gridColor}` }}>
                                  <td style={{ padding: '12px 8px' }}>
                                    <div className="rank-badge" style={{ background: '#10b981', color: 'white', display: 'inline-block' }}>{i + 1}</div>
                                  </td>
                                  <td style={{ padding: '12px 8px' }}>
                                    <div style={{ fontWeight: '600', color: textColor }}>{a.name}</div>
                                  </td>
                                  <td style={{ padding: '12px 8px', textAlign: 'right', fontWeight: '600', color: textColor }}>
                                    {a.quantity.toLocaleString()} <span style={{ fontSize: '0.75rem', color: mutedColor }}>{a.uom || 'MT'}</span>
                                  </td>
                                  <td style={{ padding: '12px 8px', textAlign: 'center', fontWeight: '600', color: textColor }}>
                                    {momText}
                                  </td>
                                  <td style={{ padding: '12px 8px', textAlign: 'center', fontWeight: '600', color: textColor }}>
                                    {yotText}
                                  </td>
                                  <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                    <span style={{ fontSize: '0.875rem', color: '#10b981', fontWeight: '700' }}>
                                      {a.percentage}%
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      ) : !areaData ? (
                        <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>Loading areas...</div>
                      ) : (
                        <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>No area data available</div>
                      )}
                    </div>
                  </div>

                  {/* Territory Performance */}
                  <div className="panel dashboard-panel">
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
                    <div style={{ overflowX: 'auto' }}>
                      {territoryPerformance?.top_territories && territoryPerformance.top_territories.length > 0 ? (
                        <div className="rank-list">
                          <div
                            style={{
                              display: 'grid',
                              gridTemplateColumns: 'minmax(150px, 1fr) minmax(120px, 1fr) minmax(180px, 1.5fr) minmax(180px, 1.5fr) minmax(100px, 0.8fr)',
                              gap: '12px',
                              marginBottom: '8px',
                              padding: '0 4px',
                              fontSize: '0.7rem',
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em',
                              color: mutedColor,
                              fontWeight: '600'
                            }}
                          >
                            <div>Territory Name</div>
                            <div style={{ textAlign: 'right' }}>Sales Volume</div>
                            <div style={{ textAlign: 'right' }}>Growth Percentage vs Previous Month</div>
                            <div style={{ textAlign: 'right' }}>Growth Percentage vs Same Month Last Year</div>
                            <div style={{ textAlign: 'right' }}>Contribution</div>
                          </div>

                          {territoryPerformance.top_territories.slice(0, 5).map((t: any, i) => {
                            const momValue = t.mom_percentage;
                            const yotValue = t.yo_percentage;
                            const momText = (momValue === null || momValue === undefined) ? "n/a" : `${Number(momValue).toFixed(1)}%`;
                            const yotText = (yotValue === null || yotValue === undefined) ? "n/a" : `${Number(yotValue).toFixed(1)}%`;
                            return (
                              <div
                                key={i}
                                className="rank-row"
                                style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'minmax(150px, 1fr) minmax(120px, 1fr) minmax(180px, 1.5fr) minmax(180px, 1.5fr) minmax(100px, 0.8fr)',
                                  gap: '12px',
                                  alignItems: 'center',
                                  padding: '8px 4px'
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                                  <div className="rank-badge" style={{ background: '#ec4899', color: 'white', flexShrink: 0 }}>{i + 1}</div>
                                  <div style={{ fontSize: '0.875rem', fontWeight: '600', color: textColor, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={t.name}>{t.name}</div>
                                </div>

                                <div style={{ fontWeight: '700', color: textColor, fontSize: '0.875rem', textAlign: 'right' }}>
                                  {t.quantity?.toLocaleString()} <span style={{ fontSize: '0.75rem', color: mutedColor }}>{t.uom || 'MT'}</span>
                                </div>

                                <div style={{ fontSize: '0.8rem', fontWeight: '600', color: textColor, textAlign: 'right' }}>{momText}</div>
                                <div style={{ fontSize: '0.8rem', fontWeight: '600', color: textColor, textAlign: 'right' }}>{yotText}</div>

                                <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#ec4899', textAlign: 'right' }}>
                                  {t.quantity_percentage}%
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : !territoryPerformance ? (
                        <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>Loading Territories...</div>
                      ) : (
                        <div style={{ color: mutedColor, textAlign: 'center', fontSize: '0.875rem', padding: '20px' }}>No territory data available</div>
                      )}
                    </div>
                  </div>

                  {/* Combined Insights Sub-row (Dynamic) */}
                  {(areaInsights || territoryInsights) && (
                    <div style={{ gridColumn: '1 / -1', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '12px' }}>
                      <div>
                        {areaInsights && (
                          <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '4px', borderLeft: '3px solid #10b981', position: 'relative' }}>
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
                                borderRadius: '3px'
                              }}
                            >
                              ✕
                            </button>
                            <div style={{ fontSize: '0.75rem', lineHeight: '1.5', color: textColor }}>
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{areaInsights}</ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </div>
                      <div>
                        {territoryInsights && (
                          <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '4px', borderLeft: '3px solid #ec4899', position: 'relative' }}>
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
                                borderRadius: '3px'
                              }}
                            >
                              ✕
                            </button>
                            <div style={{ fontSize: '0.8rem', lineHeight: '1.5', color: textColor, whiteSpace: 'pre-wrap' }}>
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{territoryInsights}</ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Credit Mix */}
                <div className="panel dashboard-panel wide">
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
                                { name: 'Credit', value: creditRatio.credit?.revenue || 0 },
                                { name: 'Cash', value: creditRatio.cash?.revenue || 0 },
                                { name: 'Both', value: creditRatio.both?.revenue || 0 }
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
                          <div style={{ color: '#3b82f6', fontSize: '1.5rem', fontWeight: '700' }}>{(creditRatio.credit?.percentage || 0).toFixed(1)}%</div>
                          <div style={{ color: mutedColor, fontSize: '0.75rem' }}>{(creditRatio.credit?.revenue || 0).toLocaleString()} MT</div>
                          <div style={{ color: mutedColor, fontSize: '0.7rem' }}>{creditRatio.credit?.order_count || 0} Orders</div>
                        </div>
                        <div>
                          <div style={{ color: mutedColor, fontSize: '0.875rem' }}>Cash Sales</div>
                          <div style={{ color: '#10b981', fontSize: '1.5rem', fontWeight: '700' }}>{(creditRatio.cash?.percentage || 0).toFixed(1)}%</div>
                          <div style={{ color: mutedColor, fontSize: '0.75rem' }}>{(creditRatio.cash?.revenue || 0).toLocaleString()} MT</div>
                          <div style={{ color: mutedColor, fontSize: '0.7rem' }}>{creditRatio.cash.order_count} Orders</div>
                        </div>
                        <div>
                          <div style={{ color: mutedColor, fontSize: '0.875rem' }}>Both</div>
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
                  )
                  }
                </div>
              </div>

            </>
          )
          }




          {/* FORECAST VIEW */}
          {
            activeSection === 'forecast' && (
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
                      {selectedUnit ? (
                        forecastData?.global_chart ? (
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
                        ) : (
                          <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>
                            {insightsLoading.forecast || isDataLoading ? "Loading forecast data..." : "No forecast data available for this unit"}
                          </div>
                        )
                      ) : (
                        <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>
                          Please select a Business Unit to view AI Forecast
                        </div>
                      )}
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
            )
          }

          {/* MARKET INTELLIGENCE VIEW - RFM ANALYSIS */}
          {
            activeSection === 'market-intelligence' && (
              <>
                <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
                  {/* RFM Overview Stats */}
                  <div className="panel dashboard-panel">
                    <div className="panel-header">
                      <h2>RFM Analysis Overview</h2>
                    </div>
                    <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                      <div className="kpi-card">
                        <div className="kpi-label">Total Customers</div>
                        <div className="kpi-value">{rfmData?.metadata.total_customers.toLocaleString() || '0'}</div>
                      </div>
                      <div className="kpi-card">
                        <div className="kpi-label">Total Transactions</div>
                        <div className="kpi-value">{rfmData?.metadata.total_transactions.toLocaleString() || '0'}</div>
                      </div>
                      <div className="kpi-card">
                        <div className="kpi-label">Total Volume</div>
                        <div className="kpi-value">{rfmData?.metadata.total_revenue.toLocaleString()}</div>
                      </div>
                      <div className="kpi-card">
                        <div className="kpi-label">Analysis Period</div>
                        <div className="kpi-value" style={{ fontSize: '0.9rem' }}>
                          {rfmData?.metadata.date_range.start && rfmData?.metadata.date_range.end
                            ? `${rfmData.metadata.date_range.start} to ${rfmData.metadata.date_range.end}`
                            : 'All Time'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Customer Segment Distribution */}
                  <div className="panel dashboard-panel">
                    <div className="panel-header">
                      <h2>Customer Segment Distribution</h2>
                    </div>
                    <div style={{ height: '300px' }}>
                      {rfmData?.segment_summary && rfmData.segment_summary.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={rfmData.segment_summary}
                              dataKey="customer_count"
                              nameKey="segment"
                              cx="50%"
                              cy="50%"
                              outerRadius={100}
                              label={(entry: any) => `${entry.segment}: ${entry.customer_percentage}%`}
                            >
                              {rfmData.segment_summary.map((entry, index) => {
                                const colors: { [key: string]: string } = {
                                  'Platinum': '#FFD700',
                                  'Gold': '#FFA500',
                                  'Silver': '#C0C0C0',
                                  'Occasional': '#87CEEB',
                                  'Inactive': '#D3D3D3'
                                };
                                return <Cell key={`cell-${index}`} fill={colors[entry.segment] || _COLORS[index % _COLORS.length]} />;
                              })}
                            </Pie>
                            <RechartsTooltip
                              contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }}
                              itemStyle={{ color: textColor }}
                            />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>
                          {isDataLoading ? 'Loading RFM data...' : 'No RFM data available'}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Revenue by Segment */}
                  <div className="panel dashboard-panel">
                    <div className="panel-header">
                      <h2>Volume Distribution by Segment</h2>
                    </div>
                    <div style={{ height: '300px' }}>
                      {rfmData?.segment_summary && rfmData.segment_summary.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={rfmData.segment_summary}
                              dataKey="total_revenue"
                              nameKey="segment"
                              cx="50%"
                              cy="50%"
                              outerRadius={100}
                              label={(entry: any) => `${entry.segment}: ${entry.revenue_percentage}%`}
                            >
                              {rfmData.segment_summary.map((entry, index) => {
                                const colors: { [key: string]: string } = {
                                  'Platinum': '#FFD700',
                                  'Gold': '#FFA500',
                                  'Silver': '#C0C0C0',
                                  'Occasional': '#87CEEB',
                                  'Inactive': '#D3D3D3'
                                };
                                return <Cell key={`cell-${index}`} fill={colors[entry.segment] || _COLORS[index % _COLORS.length]} />;
                              })}
                            </Pie>
                            <RechartsTooltip
                              contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }}
                              itemStyle={{ color: textColor }}
                            />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>
                          {isDataLoading ? 'Loading RFM data...' : 'No RFM data available'}
                        </div>
                      )}
                    </div>
                  </div>



                  {/* Top Customers by Segment */}
                  <div className="panel dashboard-panel full" style={{ gridColumn: '1 / -1' }}>
                    <div className="panel-header">
                      <h2>Top Customers (Platinum & Gold)</h2>
                    </div>
                    <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                      {rfmData?.customers && rfmData.customers.length > 0 ? (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-primary)', zIndex: 1 }}>
                            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                              <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Customer</th>
                              <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>Segment</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>Recency (days)</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>Frequency</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>Volume</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>RFM Score</th>
                            </tr>
                          </thead>
                          <tbody>
                            {rfmData.customers
                              .filter(c => c.Customer_segment === 'Platinum' || c.Customer_segment === 'Gold')
                              .sort((a, b) => b.RFM_Score - a.RFM_Score)
                              .slice(0, 20)
                              .map((customer, idx) => {
                                const segmentColors: { [key: string]: string } = {
                                  'Platinum': '#FFD700',
                                  'Gold': '#FFA500'
                                };
                                return (
                                  <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                                    <td style={{ padding: '12px' }}>{customer.customer_name}</td>
                                    <td style={{ padding: '12px', textAlign: 'center' }}>
                                      <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '12px',
                                        backgroundColor: segmentColors[customer.Customer_segment],
                                        color: '#000',
                                        fontSize: '0.75rem',
                                        fontWeight: 600
                                      }}>
                                        {customer.Customer_segment}
                                      </span>
                                    </td>
                                    <td style={{ padding: '12px', textAlign: 'right' }}>{customer.Recency}</td>
                                    <td style={{ padding: '12px', textAlign: 'right' }}>{customer.Frequency}</td>
                                    <td style={{ padding: '12px', textAlign: 'right' }}>{customer.Monetary.toLocaleString()}</td>
                                    <td style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>{customer.RFM_Score.toFixed(2)}</td>
                                  </tr>
                                );
                              })}
                          </tbody>
                        </table>
                      ) : (
                        <div style={{ padding: '40px', textAlign: 'center', color: mutedColor }}>
                          {isDataLoading ? 'Loading customer data...' : 'No customer data available'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )
          }
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
            {messages.map((m) => (
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
                  Today&apos;s Revenue
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
    </div>
  );
}
