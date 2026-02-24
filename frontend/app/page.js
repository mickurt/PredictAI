"use client";
import { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { ArrowUpRight, ArrowDownRight, Activity, DollarSign, Wallet, RefreshCw, Zap, TrendingUp, TrendingDown, Clock, ExternalLink, Trash2, AlertCircle } from 'lucide-react';

export default function Dashboard() {
    const [status, setStatus] = useState(null);
    const [history, setHistory] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [settings, setSettings] = useState({ stocks: true, crypto: true, polymarket: true });
    const [timeframe, setTimeframe] = useState('ALL');
    const [loading, setLoading] = useState(false);

    const getAssetLink = (asset) => {
        if (!asset) return '#';

        // Polymarket
        if (asset.startsWith('POLY:')) {
            let slug = asset.replace('POLY:', '');
            if (slug.includes(':')) {
                slug = slug.split(':')[0];
            }
            return `https://polymarket.com/event/${slug}`;
        }

        // Stocks (e.g. COIN -> COIN:NASDAQ)
        // If it doesn't have a dash (Crypto) and isn't Polymarket, assume Stock/NASDAQ
        if (!asset.includes('-') && !asset.includes(':')) {
            return `https://www.google.com/finance/quote/${asset}:NASDAQ`;
        }

        // Crypto (BTC-USD) or fallback
        return `https://www.google.com/finance/quote/${asset}`;
    };

    const fetchData = async () => {
        try {
            const [statusRes, historyRes, txRes, settingsRes] = await Promise.all([
                fetch('http://localhost:8000/api/status'),
                fetch('http://localhost:8000/api/history'),
                fetch('http://localhost:8000/api/transactions'),
                fetch('http://localhost:8000/api/settings')
            ]);

            const s = await statusRes.json();
            const h = await historyRes.json();
            const t = await txRes.json();
            const set = await settingsRes.json();

            setStatus(s);
            setSettings(set);

            const formattedHistory = h.map(item => ({
                time: new Date(item[0]).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                value: item[1]
            }));
            setHistory(formattedHistory);
            setTransactions(t);
        } catch (err) {
            console.error("Failed to fetch data:", err);
        }
    };

    const toggleSetting = async (key) => {
        const newSettings = { ...settings, [key]: !settings[key] };
        setSettings(newSettings);
        try {
            await fetch('http://localhost:8000/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: newSettings[key] })
            });
        } catch (e) {
            console.error("Failed to update settings", e);
        }
    };

    const handleManualRun = async () => {
        setLoading(true);
        try {
            await fetch('http://localhost:8000/api/run', { method: 'POST' });
            await new Promise(r => setTimeout(r, 1000)); // Fake delay for UX
            await fetchData();
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        if (!confirm("⚠️ WARNING: This will delete all transaction history and reset your balance to $100. Are you sure?")) return;
        setLoading(true);
        try {
            await fetch('http://localhost:8000/api/reset', { method: 'POST' });
            await new Promise(r => setTimeout(r, 1000));
            // Reset local state to show clean slate immediately
            setStatus(null);
            setHistory([]);
            setTransactions([]);
            await fetchData();
        } catch (e) {
            console.error("Reset failed", e);
            alert("Reset failed. Check console.");
        } finally {
            setLoading(false);
        }
    };

    const handleDeposit = async () => {
        setLoading(true);
        try {
            await fetch('http://localhost:8000/api/deposit', { method: 'POST' });
            await new Promise(r => setTimeout(r, 500));
            await fetchData();
        } catch (e) {
            console.error("Deposit failed", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const currentVal = status ? status.total_value : 100;

    // Use backend calculated performance if available (handles deposits correctly)
    const rawPercent = status && status.performance_pct !== undefined
        ? status.performance_pct
        : ((currentVal - 100) / 100) * 100;

    const percent = rawPercent.toFixed(2);
    const isPositive = rawPercent >= 0;

    // Render Skeleton or Data
    if (!status && history.length === 0) return (
        <div className="flex h-screen w-full items-center justify-center bg-slate-950 text-slate-500">
            <div className="flex flex-col items-center gap-4 animate-pulse">
                <div className="h-12 w-12 rounded-full border-4 border-t-cyan-500 border-slate-800 animate-spin"></div>
                <p className="tracking-widest text-xs uppercase font-medium">Initializing Neural Core...</p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 font-sans selection:bg-cyan-500/30 selection:text-cyan-200 pb-20">
            <div className="bg-gradient-animate"></div>

            {/* Navbar */}
            <nav className="border-b border-white/5 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                            <Zap className="w-5 h-5 text-white fill-white" />
                        </div>
                        <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                            PredictAI
                        </span>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-white/5 text-xs font-medium text-slate-400">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                            <span>ENGINE ONLINE</span>
                        </div>
                        <button
                            onClick={handleManualRun}
                            disabled={loading}
                            className={`
                group relative px-5 py-2 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600
                text-white font-medium text-sm shadow-lg shadow-cyan-500/25
                hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]
                transition-all duration-200 disabled:opacity-70 disabled:cursor-not-allowed overflow-hidden
              `}
                        >
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            <span className="hidden sm:inline">{loading ? 'Analyzing...' : 'Run Analysis'}</span>
                        </button>

                        <button
                            onClick={handleDeposit}
                            disabled={loading}
                            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm font-bold hover:bg-emerald-500/20 hover:border-emerald-500 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Add $1000 Test Funds"
                        >
                            <DollarSign className="w-4 h-4" />
                            <span className="hidden sm:inline">+$1k</span>
                        </button>

                        <button
                            onClick={handleReset}
                            disabled={loading}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-rose-400 border border-rose-500/30 rounded-lg text-sm font-bold hover:bg-rose-500/10 hover:border-rose-500 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Reset Database"
                        >
                            <Trash2 className="w-4 h-4" />
                            <span className="hidden sm:inline">Reset</span>
                        </button>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">

                {/* Trading Preferences */}
                <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center gap-6 shadow-sm">
                    <div className="flex items-center gap-2 text-slate-400">
                        <Activity className="w-5 h-5" />
                        <span className="font-semibold">Active Markets:</span>
                    </div>

                    {['polymarket', 'crypto', 'stocks'].map(market => (
                        <label key={market} className="flex items-center gap-3 cursor-pointer group select-none">
                            <div className={`
                                w-5 h-5 rounded border flex items-center justify-center transition-all duration-200
                                ${settings[market]
                                    ? 'bg-cyan-500 border-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                                    : 'border-slate-600 group-hover:border-slate-500 bg-slate-900'}
                            `}>
                                {settings[market] && <div className="w-2.5 h-2.5 bg-white rounded-[1px]" />}
                            </div>
                            <input
                                type="checkbox"
                                className="hidden"
                                checked={settings[market]}
                                onChange={() => toggleSetting(market)}
                            />
                            <span className={`capitalize font-medium transition-colors ${settings[market] ? 'text-cyan-100' : 'text-slate-500'}`}>
                                {market}
                            </span>
                        </label>
                    ))}
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

                    {/* Main Balance Card */}
                    <div className="lg:col-span-2 glass-card rounded-2xl p-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500">
                            <Activity className="w-32 h-32 text-cyan-500" />
                        </div>

                        <div className="relative z-10">
                            <h2 className="text-slate-400 text-sm font-medium mb-1 tracking-wide uppercase">Total Portfolio Value</h2>
                            <div className="flex items-baseline gap-1 mb-4">
                                <span className="text-5xl font-bold tracking-tighter text-white drop-shadow-lg">
                                    ${currentVal.toFixed(2)}
                                </span>
                            </div>

                            <div className="flex items-center gap-4">
                                <div className={`
                  flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold border backdrop-blur-sm
                  ${isPositive
                                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                        : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}
                `}>
                                    {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    <span>{isPositive ? '+' : ''}{percent}%</span>
                                </div>
                                <span className="text-slate-500 text-sm font-medium"> Net Return (All Time)</span>
                            </div>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="lg:col-span-2 grid grid-cols-2 gap-4">
                        <div className="glass-panel rounded-xl p-5 hover:bg-slate-800/50 transition-colors duration-300 group">
                            <div className="bg-slate-800/80 w-10 h-10 rounded-lg flex items-center justify-center mb-3 group-hover:bg-cyan-500/20 transition-colors">
                                <Wallet className="w-5 h-5 text-slate-400 group-hover:text-cyan-400" />
                            </div>
                            <div className="text-2xl font-bold text-slate-100">${status?.balance.toFixed(2) || '0.00'}</div>
                            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mt-1">Available Cash</div>
                        </div>

                        <div className="glass-panel rounded-xl p-5 hover:bg-slate-800/50 transition-colors duration-300 group">
                            <div className="bg-slate-800/80 w-10 h-10 rounded-lg flex items-center justify-center mb-3 group-hover:bg-purple-500/20 transition-colors">
                                <Activity className="w-5 h-5 text-slate-400 group-hover:text-purple-400" />
                            </div>
                            <div className="text-2xl font-bold text-slate-100">{transactions.length}</div>
                            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mt-1">Total Trades</div>
                        </div>

                        <div className="col-span-2 glass-panel rounded-xl p-5 flex items-center justify-between hover:bg-slate-800/50 transition-colors duration-300 group cursor-default">
                            <div>
                                <div className="text-sm font-medium text-slate-300 mb-1 group-hover:text-white transition-colors">Gemini AI Model</div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                                    <div className="text-xs text-slate-500">Status: Operational & Learning</div>
                                </div>
                            </div>
                            <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 px-3 py-1.5 rounded text-xs font-medium text-indigo-300">
                                v1.0.2-beta
                            </div>
                        </div>
                    </div>
                </div>

                {/* Charts & Holdings Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Chart Section */}
                    <div className="lg:col-span-2 glass-card rounded-2xl p-6 min-h-[400px] flex flex-col">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-lg font-semibold text-white">Performance Analytics</h3>
                                <p className="text-xs text-slate-500 mt-0.5">Real-time portfolio valuation tracking</p>
                            </div>
                            <div className="flex bg-slate-900/50 p-1 rounded-lg border border-white/5">
                                {['1H', '1D', '1W', '1M', 'ALL'].map((tf) => (
                                    <button
                                        key={tf}
                                        onClick={() => setTimeframe(tf)}
                                        className={`
                      px-3 py-1 rounded-md text-xs font-semibold transition-all duration-200
                      ${timeframe === tf
                                                ? 'bg-slate-700 text-white shadow-sm'
                                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}
                    `}
                                    >
                                        {tf}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="flex-1 w-full min-h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={history.slice(-30)}> {/* Last 30 points for demo */}
                                    <defs>
                                        <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2} />
                                            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                    <XAxis
                                        dataKey="time"
                                        stroke="#475569"
                                        tick={{ fontSize: 10, fill: '#64748b' }}
                                        tickLine={false}
                                        axisLine={false}
                                        dy={10}
                                    />
                                    <YAxis
                                        stroke="#475569"
                                        tick={{ fontSize: 10, fill: '#64748b' }}
                                        tickLine={false}
                                        axisLine={false}
                                        domain={[(dataMin) => (dataMin * 0.95), (dataMax) => (dataMax * 1.05)]}
                                        tickFormatter={(val) => `$${val.toFixed(0)}`}
                                        dx={-10}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                            borderColor: 'rgba(255,255,255,0.1)',
                                            borderRadius: '12px',
                                            color: '#fff',
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                                            backdropFilter: 'blur(8px)'
                                        }}
                                        itemStyle={{ color: '#fff', fontSize: '12px', fontWeight: 500 }}
                                        labelStyle={{ color: '#94a3b8', fontSize: '10px', marginBottom: '4px' }}
                                        cursor={{ stroke: '#38bdf8', strokeWidth: 1, strokeDasharray: '4 4' }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#06b6d4"
                                        strokeWidth={2}
                                        fillOpacity={1}
                                        fill="url(#colorVal)"
                                        activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#06b6d4' }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Holdings Section */}
                    <div className="lg:col-span-1 glass-card rounded-2xl p-6 flex flex-col">
                        <h3 className="text-lg font-semibold text-white mb-4">Active Holdings</h3>
                        <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2 max-h-[400px]">

                            {/* Cash Item */}
                            <div className="flex justify-between items-center p-3 rounded-xl bg-emerald-900/10 border border-emerald-500/20 hover:border-emerald-500/40 transition-all duration-300">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold shadow-inner">
                                        <DollarSign className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <div className="font-semibold text-sm text-emerald-100">USD CASH</div>
                                        <div className="text-[10px] text-emerald-400/60 uppercase tracking-wider font-medium">Liquidity</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-bold font-mono text-emerald-400">
                                        {status ? `$${status.balance.toFixed(2)}` : '---'}
                                    </div>
                                    <div className="text-[10px] text-emerald-500/50 flex items-center justify-end gap-1">
                                        <Activity className="w-3 h-3" /> Available
                                    </div>
                                </div>
                            </div>

                            {status && Object.entries(status.portfolio).length > 0 ? (
                                Object.entries(status.portfolio).map(([asset, value]) => (
                                    <div key={asset} className="flex justify-between items-center p-3 rounded-xl bg-slate-800/30 border border-white/5 hover:border-cyan-500/30 hover:bg-slate-800/50 transition-all duration-300 group">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-sm font-bold text-white shadow-inner group-hover:from-cyan-900/50 group-hover:to-blue-900/50 transition-colors">
                                                {asset.substring(0, 2)}
                                            </div>
                                            <div>
                                                <a href={getAssetLink(asset)} target="_blank" rel="noopener noreferrer" className="font-semibold text-sm text-white hover:text-cyan-400 flex items-center gap-1 transition-colors">
                                                    {asset}
                                                    <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                                                </a>
                                                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Equity</div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold text-sm text-cyan-50">${value.toFixed(2)}</div>
                                            <div className="text-[10px] text-emerald-400 flex items-center justify-end gap-1">
                                                <TrendingUp className="w-3 h-3" /> Live
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3 py-10 opacity-60">
                                    <div className="p-4 rounded-full bg-slate-800/50 border border-slate-700/50">
                                        <Wallet className="w-6 h-6" />
                                    </div>
                                    <p className="text-sm font-medium">No active positions</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Transactions Table */}
                <div className="glass-card rounded-2xl overflow-hidden">
                    <div className="p-6 border-b border-white/5 flex justify-between items-center">
                        <h3 className="text-lg font-semibold text-white">Execution Log</h3>
                        <span className="text-xs font-medium px-2 py-1 rounded bg-slate-800 text-slate-400 border border-white/5">
                            Wait time: 5m
                        </span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-slate-900/50 text-xs uppercase text-slate-400 font-semibold tracking-wider">
                                <tr>
                                    <th className="px-6 py-4">Timestamp</th>
                                    <th className="px-6 py-4">Action</th>
                                    <th className="px-6 py-4">Asset</th>
                                    <th className="px-6 py-4">Amount</th>
                                    <th className="px-6 py-4">Price</th>
                                    <th className="px-6 py-4">Gain</th>
                                    <th className="px-6 py-4 hidden sm:table-cell">AI Reasoning</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-sm">
                                {transactions.length > 0 ? (
                                    transactions.map((tx) => (
                                        <tr key={tx[0]} className="hover:bg-white/[0.02] transition-colors group">
                                            <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-3 h-3 opacity-50" />
                                                    {new Date(tx[1]).toLocaleTimeString()}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`
                          inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border
                          ${tx[2] === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                                        tx[2] === 'SELL' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                                            'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'}
                        `}>
                                                    {tx[2]}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 font-semibold text-slate-200">
                                                <a href={getAssetLink(tx[4])} target="_blank" rel="noopener noreferrer" className="hover:text-cyan-400 inline-flex items-center gap-1 transition-colors">
                                                    {tx[4]}
                                                    {tx[4] && tx[4].startsWith('POLY:') && <ExternalLink className="w-3 h-3 opacity-50" />}
                                                </a>
                                            </td>
                                            <td className="px-6 py-4 font-mono text-slate-300">
                                                {['HOLD', 'WATCH'].includes(tx[2]) ? (
                                                    <span className="text-slate-600 font-sans tracking-widest text-xs">---</span>
                                                ) : (
                                                    `$${parseFloat(tx[3]).toFixed(2)}`
                                                )}
                                            </td>
                                            <td className="px-6 py-4 font-mono text-slate-300">
                                                {tx[6] && tx[6] > 0 ? `$${parseFloat(tx[6]).toFixed(2)}` : <span className="text-slate-600">-</span>}
                                            </td>
                                            <td className="px-6 py-4 font-mono">
                                                {tx[2] === 'SELL' ? (
                                                    <span className={tx[7] >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                                        {tx[7] >= 0 ? "+" : ""}{parseFloat(tx[7]).toFixed(2)}%
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-600">-</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-slate-400 hidden sm:table-cell max-w-sm group-hover:text-slate-300 transition-colors">
                                                <p className="whitespace-normal break-words leading-relaxed">{tx[5]}</p>
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="7" className="px-6 py-12 text-center text-slate-500 text-sm italic">
                                            No transactions recorded yet. AI waiting for market signal.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                    {transactions.length > 0 && (
                        <div className="bg-slate-900/30 px-6 py-3 border-t border-white/5 text-center">
                            <button className="text-xs font-medium text-cyan-400 hover:text-cyan-300 transition-colors">
                                View All History
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <footer className="text-center py-8 text-xs text-slate-600 font-medium tracking-wide">
                    <p>POWERED BY GEMINI PRO • SECURE CONNECTION ESTABLISHED</p>
                </footer>

            </main>
        </div>
    );
}
