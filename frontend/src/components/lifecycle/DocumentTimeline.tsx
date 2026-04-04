import { type ReactNode, useEffect, useState } from 'react';
import { X, ArrowRight, Monitor, User, Cpu, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { lifecycleAPI } from '@/api/lifecycle';
import type { LifecycleEventEntry, LifecycleState } from '@/types/lifecycle';

const STATE_COLORS: Record<LifecycleState, string> = {
  detect: 'bg-blue-100 text-blue-700',
  fetch: 'bg-blue-100 text-blue-700',
  chunk: 'bg-blue-100 text-blue-700',
  embed: 'bg-blue-100 text-blue-700',
  available_for_search: 'bg-green-100 text-green-700',
  url_dead: 'bg-amber-100 text-amber-700',
  mark_superseded: 'bg-red-100 text-red-700',
  removed_from_search: 'bg-red-200 text-red-800',
};

const TRIGGER_ICONS: Record<string, ReactNode> = {
  monitor_run: <Monitor className="h-3.5 w-3.5" />,
  etl_pipeline: <Cpu className="h-3.5 w-3.5" />,
  api: <User className="h-3.5 w-3.5" />,
  bootstrap: <Database className="h-3.5 w-3.5" />,
};

function stateBadge(state: LifecycleState) {
  const cls = STATE_COLORS[state] ?? 'bg-slate-100 text-slate-700';
  return (
    <span className={`inline-block text-xs font-medium px-1.5 py-0.5 rounded ${cls}`}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

function EventRow({ event }: { event: LifecycleEventEntry }) {
  const icon = TRIGGER_ICONS[event.triggered_by] as ReactNode;
  const reason = event.details?.reason as string | undefined;
  return (
    <li className="ml-4">
      <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border-2 border-white bg-slate-400" />
      <div className="flex items-center gap-1 flex-wrap">
        {stateBadge(event.from_state)}
        <ArrowRight className="h-3 w-3 text-slate-400 shrink-0" />
        {stateBadge(event.to_state)}
      </div>
      <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
        {icon ?? null}
        <span>{event.triggered_by.replace(/_/g, ' ')}</span>
        {event.http_status ? (
          <span className="ml-1 text-amber-600">HTTP {event.http_status}</span>
        ) : null}
      </div>
      <p className="text-xs text-slate-400 mt-0.5">
        {new Date(event.created_at).toLocaleString()}
      </p>
      {reason ? (
        <p className="text-xs text-slate-500 italic mt-0.5">{reason}</p>
      ) : null}
    </li>
  );
}

interface Props {
  fileId: string | null;
  title: string;
  onClose: () => void;
}

export function DocumentTimeline({ fileId, title, onClose }: Props) {
  const [events, setEvents] = useState<LifecycleEventEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    lifecycleAPI.getHistory(fileId)
      .then(data => setEvents(data.events))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [fileId]);

  const isOpen = fileId !== null;

  return (
    <div
      className={`fixed top-0 right-0 h-full w-80 bg-white shadow-2xl border-l z-50 flex flex-col
        transition-transform duration-300 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-slate-50">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">History</p>
          <p className="text-sm font-semibold text-slate-800 truncate max-w-[220px]">{title}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <p className="text-sm text-slate-500 text-center mt-8">Loading...</p>
        )}
        {!loading && events.length === 0 && (
          <p className="text-sm text-slate-500 text-center mt-8">No history yet.</p>
        )}
        {!loading && events.length > 0 && (
          <ol className="relative border-l border-slate-200 ml-3 space-y-6">
            {events.map(event => (
              <EventRow key={event.id} event={event} />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
