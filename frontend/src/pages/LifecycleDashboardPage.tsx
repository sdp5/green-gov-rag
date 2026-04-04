import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Leaf, ArrowLeft, LogIn, LogOut, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LifecycleSummaryChart } from '@/components/lifecycle/LifecycleSummaryChart';
import { LGADocumentTable } from '@/components/lifecycle/LGADocumentTable';
import { DocumentTimeline } from '@/components/lifecycle/DocumentTimeline';
import { RegisterDocumentForm } from '@/components/lifecycle/RegisterDocumentForm';
import { lifecycleAPI } from '@/api/lifecycle';
import { useAuthStore } from '@/store/authStore';
import type { LifecycleSummary, LGADocumentGroup, LifecycleDocumentEntry, LifecycleState } from '@/types/lifecycle';

const LIFECYCLE_STATES: Array<{ value: string; label: string }> = [
  { value: 'all', label: 'All States' },
  { value: 'available_for_search', label: 'In Search' },
  { value: 'url_dead', label: 'URL Dead' },
  { value: 'detect', label: 'Detected' },
  { value: 'fetch', label: 'Fetching' },
  { value: 'chunk', label: 'Chunking' },
  { value: 'embed', label: 'Embedding' },
  { value: 'mark_superseded', label: 'Superseded' },
  { value: 'removed_from_search', label: 'Removed' },
];

export default function LifecycleDashboardPage() {
  const { isAdmin, login, logout } = useAuthStore();

  const [summary, setSummary] = useState<LifecycleSummary | null>(null);
  const [allGroups, setAllGroups] = useState<LGADocumentGroup[]>([]);
  const [filteredGroups, setFilteredGroups] = useState<LGADocumentGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [stateFilter, setStateFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Timeline panel
  const [timelineDoc, setTimelineDoc] = useState<LifecycleDocumentEntry | null>(null);

  // Login modal
  const [showLogin, setShowLogin] = useState(false);
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  const fetchData = async (state?: string) => {
    setLoading(true);
    try {
      const [summaryData, lgaData] = await Promise.all([
        lifecycleAPI.getSummary(),
        lifecycleAPI.getByLGA(state && state !== 'all' ? state : undefined),
      ]);
      setSummary(summaryData);
      setAllGroups(lgaData.groups);
      setFilteredGroups(lgaData.groups);
    } catch (err) {
      console.error('Failed to load lifecycle data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(stateFilter);
  }, [stateFilter]);

  // Client-side search filter
  useEffect(() => {
    if (!search.trim()) {
      setFilteredGroups(allGroups);
      return;
    }
    const q = search.toLowerCase();
    setFilteredGroups(
      allGroups
        .map(group => ({
          ...group,
          documents: group.documents.filter(
            d => d.title.toLowerCase().includes(q) || d.topic.toLowerCase().includes(q)
          ),
        }))
        .filter(g => g.documents.length > 0)
    );
  }, [search, allGroups]);

  const handleLogin = () => {
    const ok = login(loginPassword);
    if (ok) {
      setShowLogin(false);
      setLoginPassword('');
      setLoginError('');
    } else {
      setLoginError('Incorrect password.');
    }
  };

  const handleStateChartClick = (state: LifecycleState | 'all') => {
    setStateFilter(state);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b bg-white shadow-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-gradient-to-br from-emerald-500 to-green-600 rounded-md flex items-center justify-center">
                <Leaf className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-lg font-bold text-slate-800">Document Lifecycle Dashboard</h1>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/">
                <Button variant="ghost" size="sm" className="gap-1 text-slate-600">
                  <ArrowLeft className="h-4 w-4" /> Playground
                </Button>
              </Link>
              {isAdmin ? (
                <Button variant="outline" size="sm" onClick={logout} className="gap-1">
                  <LogOut className="h-4 w-4" /> Logout
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setShowLogin(true)} className="gap-1">
                  <LogIn className="h-4 w-4" /> Admin Login
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl p-6 w-80">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Admin Login</h2>
            <Input
              type="password"
              placeholder="Admin password"
              value={loginPassword}
              onChange={e => setLoginPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              autoFocus
            />
            {loginError && <p className="text-xs text-red-600 mt-1">{loginError}</p>}
            <div className="flex gap-2 mt-4">
              <Button className="flex-1 bg-emerald-600 hover:bg-emerald-700" onClick={handleLogin}>
                Login
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => { setShowLogin(false); setLoginError(''); }}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Document Timeline panel */}
      <DocumentTimeline
        fileId={timelineDoc?.file_id ?? null}
        title={timelineDoc?.title ?? ''}
        onClose={() => setTimelineDoc(null)}
      />

      <main className="container mx-auto px-4 lg:px-8 py-6 space-y-6">
        {/* Summary Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Donut chart */}
          <div className="bg-white rounded-xl border p-4 col-span-1">
            <h2 className="text-sm font-semibold text-slate-600 mb-2">Lifecycle Distribution</h2>
            {summary ? (
              <LifecycleSummaryChart summary={summary} onStateClick={handleStateChartClick} />
            ) : (
              <div className="h-[260px] flex items-center justify-center text-slate-400 text-sm">
                Loading...
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3 content-start">
            {summary && (
              <>
                <StatCard label="Total Sources" value={summary.total_sources} />
                <StatCard label="Total Files" value={summary.total_files} />
                <StatCard label="In Search" value={summary.available_for_search} color="green" />
                <StatCard label="URL Dead" value={summary.url_dead} color="amber" />
                <StatCard label="Superseded" value={summary.mark_superseded} color="red" />
                <StatCard
                  label="Last Monitored"
                  value={
                    summary.last_monitoring_run
                      ? new Date(summary.last_monitoring_run).toLocaleDateString()
                      : '—'
                  }
                />
              </>
            )}
          </div>
        </div>

        {/* Filters + refresh */}
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <Select value={stateFilter} onValueChange={setStateFilter}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LIFECYCLE_STATES.map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            className="sm:w-64"
            placeholder="Search by title or topic..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />

          <Button
            variant="ghost"
            size="sm"
            className="gap-1 text-slate-500"
            onClick={() => fetchData(stateFilter)}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* LGA Document Table */}
        <div className="bg-white rounded-xl border p-4">
          <h2 className="text-sm font-semibold text-slate-600 mb-3">
            Documents by LGA
            {!isAdmin && (
              <span className="ml-2 text-xs font-normal text-slate-400">(read-only — login to manage)</span>
            )}
          </h2>
          {loading ? (
            <p className="text-sm text-slate-400 text-center py-8">Loading documents...</p>
          ) : (
            <LGADocumentTable
              groups={filteredGroups}
              isAdmin={isAdmin}
              onHistoryClick={doc => setTimelineDoc(doc)}
              onDocumentReplaced={() => fetchData(stateFilter)}
            />
          )}
        </div>

        {/* Register new document — admin only */}
        {isAdmin && (
          <div className="bg-white rounded-xl border p-4">
            <RegisterDocumentForm onRegistered={() => fetchData(stateFilter)} />
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color?: 'green' | 'amber' | 'red' }) {
  const colorClass = color === 'green'
    ? 'text-green-600'
    : color === 'amber'
    ? 'text-amber-600'
    : color === 'red'
    ? 'text-red-600'
    : 'text-slate-800';

  return (
    <div className="bg-slate-50 rounded-lg p-3 border">
      <p className="text-xs text-slate-500 font-medium">{label}</p>
      <p className={`text-2xl font-bold mt-0.5 ${colorClass}`}>{value}</p>
    </div>
  );
}
