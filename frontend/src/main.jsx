import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, AlertTriangle, Bell, Database, Gauge, Radio, Send, Wifi, WifiOff } from "lucide-react";
import "./styles.css";

const SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"];
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || API_BASE.replace("http", "ws");

const seeds = {
  "BTC-USD": 68100,
  "ETH-USD": 3425,
  "SOL-USD": 148,
};

function emptyMetric(symbol) {
  return {
    symbol,
    price: seeds[symbol],
    volatility: 0,
    spread: 0,
    spread_bps: 0,
    vwap: seeds[symbol],
    rolling_price_change: 0,
    liquidity_score: 80,
    volume_imbalance: 0,
    timestamp: new Date().toISOString(),
  };
}

function nextMockMetric(previous) {
  const shock = (Math.random() - 0.48) * 0.012;
  const price = Math.max(0.01, previous.price * (1 + shock));
  const spread = Math.max(0.0002, Math.random() * 0.003);
  const liquidity = Math.max(10, Math.min(100, previous.liquidity_score + (Math.random() - 0.5) * 12));
  return {
    ...previous,
    price,
    volatility: Math.min(0.035, Math.abs(shock) * 2.5 + Math.random() * 0.003),
    spread,
    spread_bps: spread * 10000,
    vwap: previous.vwap * 0.96 + price * 0.04,
    rolling_price_change: (price - previous.vwap) / previous.vwap,
    liquidity_score: liquidity,
    volume_imbalance: (Math.random() - 0.5) * 1.2,
    timestamp: new Date().toISOString(),
  };
}

function App() {
  const [selected, setSelected] = useState("BTC-USD");
  const [metrics, setMetrics] = useState(() => Object.fromEntries(SYMBOLS.map((symbol) => [symbol, emptyMetric(symbol)])));
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState(() => Object.fromEntries(SYMBOLS.map((symbol) => [symbol, [emptyMetric(symbol)]])));
  const [status, setStatus] = useState("connecting");
  const [mockMode, setMockMode] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [direction, setDirection] = useState("above");
  const [smsStatus, setSmsStatus] = useState("");
  const [liveCheck, setLiveCheck] = useState(null);
  const [liveCheckStatus, setLiveCheckStatus] = useState("");
  const mockRef = useRef(null);

  useEffect(() => {
    let socket;
    let closed = false;

    async function loadSnapshot() {
      try {
        const [metricRes, alertRes] = await Promise.all([fetch(`${API_BASE}/metrics`), fetch(`${API_BASE}/alerts`)]);
        if (metricRes.ok) {
          const data = await metricRes.json();
          if (Object.keys(data).length) setMetrics((current) => ({ ...current, ...data }));
        }
        if (alertRes.ok) setAlerts(await alertRes.json());
      } catch {
        setMockMode(true);
      }
    }

    function connect() {
      setStatus("connecting");
      socket = new WebSocket(`${WS_BASE}/ws`);
      socket.onopen = () => {
        setStatus("connected");
        setMockMode(false);
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "snapshot") {
          setMetrics((current) => ({ ...current, ...message.metrics }));
          setAlerts(message.alerts || []);
        }
        if (message.type === "market_update") {
          const metric = message.metric;
          setMetrics((current) => ({ ...current, [metric.symbol]: metric }));
          setHistory((current) => ({
            ...current,
            [metric.symbol]: [...(current[metric.symbol] || []), metric].slice(-48),
          }));
          if (message.alerts?.length) setAlerts((current) => [...message.alerts, ...current].slice(0, 30));
        }
      };
      socket.onerror = () => {
        setStatus("offline");
        setMockMode(true);
      };
      socket.onclose = () => {
        if (!closed) {
          setStatus("offline");
          setMockMode(true);
        }
      };
    }

    loadSnapshot();
    connect();
    return () => {
      closed = true;
      socket?.close();
    };
  }, []);

  useEffect(() => {
    if (!mockMode) {
      clearInterval(mockRef.current);
      mockRef.current = null;
      return;
    }
    setStatus("mock");
    mockRef.current = setInterval(() => {
      setMetrics((current) => {
        const updates = { ...current };
        SYMBOLS.forEach((symbol) => {
          updates[symbol] = nextMockMetric(updates[symbol] || emptyMetric(symbol));
        });
        setHistory((historyState) => {
          const next = { ...historyState };
          SYMBOLS.forEach((symbol) => {
            next[symbol] = [...(next[symbol] || []), updates[symbol]].slice(-48);
          });
          return next;
        });
        return updates;
      });
    }, 1000);
    return () => clearInterval(mockRef.current);
  }, [mockMode]);

  const current = metrics[selected] || emptyMetric(selected);
  const points = history[selected] || [current];
  const trend = current.rolling_price_change >= 0 ? "positive" : "negative";
  const visibleAlerts = useMemo(() => alerts.filter((alert) => !alert.symbol || alert.symbol === selected).slice(0, 8), [alerts, selected]);

  async function submitSmsAlert(event) {
    event.preventDefault();
    setSmsStatus("Creating alert...");
    try {
      const response = await fetch(`${API_BASE}/sms/price-alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: phoneNumber,
          symbol: selected,
          direction,
          target_price: Number(targetPrice),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Could not create SMS alert");
      }
      const data = await response.json();
      setSmsStatus(data.sms_mode === "twilio" ? "SMS alert armed" : "Dry-run alert armed");
      setTargetPrice("");
    } catch (error) {
      setSmsStatus(error.message || "Backend unavailable");
    }
  }

  async function checkLivePrice() {
    setLiveCheckStatus("Checking live market...");
    try {
      const response = await fetch(`${API_BASE}/market-data/live/${selected}`);
      if (!response.ok) throw new Error("Live market data unavailable");
      const data = await response.json();
      setLiveCheck(data);
      setLiveCheckStatus("Live price updated");
    } catch (error) {
      setLiveCheckStatus(error.message || "Live market data unavailable");
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Real-time risk and liquidity</p>
          <h1>Crypto Market Monitor</h1>
        </div>
        <div className={`status ${status}`}>
          {status === "connected" ? <Wifi size={18} /> : status === "mock" ? <Database size={18} /> : <WifiOff size={18} />}
          <span>{status === "connected" ? "Live backend" : status === "mock" ? "Mock data" : "Connecting"}</span>
        </div>
      </header>

      <section className="toolbar">
        <div className="symbol-tabs">
          {SYMBOLS.map((symbol) => (
            <button key={symbol} className={symbol === selected ? "active" : ""} onClick={() => setSelected(symbol)}>
              {symbol}
            </button>
          ))}
        </div>
        <label className="toggle">
          <input type="checkbox" checked={mockMode} onChange={(event) => setMockMode(event.target.checked)} />
          <span>Mock mode</span>
        </label>
      </section>

      <section className="dashboard-grid">
        <article className="price-panel">
          <div className="panel-heading">
            <Radio size={18} />
            <span>{selected}</span>
          </div>
          <strong>${formatNumber(current.price)}</strong>
          <p className={trend}>{formatPercent(current.rolling_price_change)} rolling move</p>
          <div className="source-row">
            <span>Stream: {current.source || (mockMode ? "mock" : "simulated")}</span>
            <button type="button" onClick={checkLivePrice}>Check Live Price</button>
          </div>
          {liveCheck && (
            <div className="live-check">
              <span>Coinbase live</span>
              <strong>${formatNumber(liveCheck.price)}</strong>
              <small>Bid ${formatNumber(liveCheck.bid)} / Ask ${formatNumber(liveCheck.ask)}</small>
            </div>
          )}
          {liveCheckStatus && <p className="live-status">{liveCheckStatus}</p>}
          <PriceChart points={points} />
        </article>

        <MetricCard icon={<Activity />} label="Volatility" value={formatPercent(current.volatility)} tone={current.volatility > 0.018 ? "danger" : "normal"} />
        <MetricCard icon={<Gauge />} label="Spread" value={`${current.spread_bps?.toFixed(1) || "0.0"} bps`} tone={current.spread > 0.0035 ? "warning" : "normal"} />
        <MetricCard icon={<Database />} label="VWAP" value={`$${formatNumber(current.vwap)}`} />
        <MetricCard icon={<Gauge />} label="Liquidity" value={current.liquidity_score?.toFixed(1) || "0.0"} tone={current.liquidity_score < 35 ? "danger" : "normal"} />
        <MetricCard icon={<Activity />} label="Volume Imbalance" value={formatPercent(current.volume_imbalance)} tone={Math.abs(current.volume_imbalance) > 0.55 ? "warning" : "normal"} />

        <article className="sms-panel">
          <div className="panel-heading">
            <Bell size={18} />
            <span>SMS Price Alert</span>
          </div>
          <form onSubmit={submitSmsAlert} className="sms-form">
            <label>
              <span>Phone</span>
              <input value={phoneNumber} onChange={(event) => setPhoneNumber(event.target.value)} placeholder="+15551234567" required />
            </label>
            <div className="sms-row">
              <label>
                <span>Direction</span>
                <select value={direction} onChange={(event) => setDirection(event.target.value)}>
                  <option value="above">Above</option>
                  <option value="below">Below</option>
                </select>
              </label>
              <label>
                <span>Price</span>
                <input
                  value={targetPrice}
                  onChange={(event) => setTargetPrice(event.target.value)}
                  inputMode="decimal"
                  placeholder={current.price ? current.price.toFixed(2) : "0.00"}
                  required
                />
              </label>
            </div>
            <button type="submit">
              <Send size={16} />
              <span>Create Alert</span>
            </button>
          </form>
          {smsStatus && <p className="sms-status">{smsStatus}</p>}
        </article>

        <article className="alerts-panel">
          <div className="panel-heading">
            <AlertTriangle size={18} />
            <span>Alerts</span>
          </div>
          {visibleAlerts.length === 0 ? (
            <p className="empty">No active alerts for {selected}</p>
          ) : (
            <div className="alert-list">
              {visibleAlerts.map((alert) => (
                <div key={alert.id || `${alert.type}-${alert.timestamp}`} className={`alert-item ${alert.severity}`}>
                  <span>{alert.type?.replaceAll("_", " ")}</span>
                  <strong>{alert.severity}</strong>
                  <small>{new Date(alert.timestamp).toLocaleTimeString()}</small>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

function MetricCard({ icon, label, value, tone = "normal" }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div>{React.cloneElement(icon, { size: 18 })}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function PriceChart({ points }) {
  const width = 680;
  const height = 240;
  const prices = points.map((point) => Number(point.price));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const path = prices
    .map((price, index) => {
      const x = (index / Math.max(prices.length - 1, 1)) * width;
      const y = height - ((price - min) / range) * (height - 24) - 12;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Real-time price chart">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(2)}%`;
}

createRoot(document.getElementById("root")).render(<App />);
