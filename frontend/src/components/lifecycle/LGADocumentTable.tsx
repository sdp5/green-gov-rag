import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, History, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { lifecycleAPI } from '@/api/lifecycle';
import type { LGADocumentGroup, LifecycleDocumentEntry, LifecycleState } from '@/types/lifecycle';

const STATE_BADGE: Record<LifecycleState, string> = {
  detect: 'bg-blue-100 text-blue-700 border-blue-200',
  fetch: 'bg-blue-100 text-blue-700 border-blue-200',
  chunk: 'bg-blue-100 text-blue-700 border-blue-200',
  embed: 'bg-blue-100 text-blue-700 border-blue-200',
  available_for_search: 'bg-green-100 text-green-700 border-green-200',
  url_dead: 'bg-amber-100 text-amber-700 border-amber-200',
  mark_superseded: 'bg-red-100 text-red-700 border-red-200',
  removed_from_search: 'bg-red-200 text-red-800 border-red-300',
};

const JURISDICTION_BADGE: Record<string, string> = {
  federal: 'bg-purple-100 text-purple-700',
  state: 'bg-indigo-100 text-indigo-700',
  local: 'bg-teal-100 text-teal-700',
};

interface DocumentRowProps {
  doc: LifecycleDocumentEntry;
  isAdmin: boolean;
  onHistoryClick: (doc: LifecycleDocumentEntry) => void;
  onReplaced: (fileId: string, newUrl: string) => void;
}

function DocumentRow({ doc, isAdmin, onHistoryClick, onReplaced }: DocumentRowProps) {
  const [replacementUrl, setReplacementUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleReplace = async () => {
    if (!replacementUrl.startsWith('http')) {
      setError('Must be a valid http/https URL');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await lifecycleAPI.replace(doc.file_id, replacementUrl);
      onReplaced(doc.file_id, replacementUrl);
    } catch {
      setError('Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="py-3 px-4 border-b last:border-0 hover:bg-slate-50/60 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800 truncate">{doc.title}</span>
            <Badge
              className={`text-xs px-1.5 py-0 border ${JURISDICTION_BADGE[doc.jurisdiction] ?? 'bg-slate-100 text-slate-700'}`}
              variant="outline"
            >
              {doc.jurisdiction}
            </Badge>
            <Badge
              className={`text-xs px-1.5 py-0 border ${STATE_BADGE[doc.lifecycle_state]}`}
              variant="outline"
            >
              {doc.lifecycle_state === 'url_dead' && (
                <AlertTriangle className="h-3 w-3 mr-1 inline" />
              )}
              {doc.lifecycle_state.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
            {doc.lifecycle_transitioned_at && (
              <span>{new Date(doc.lifecycle_transitioned_at).toLocaleDateString()}</span>
            )}
            {doc.http_status_code && (
              <span className={doc.http_status_code >= 400 ? 'text-red-500' : ''}>
                HTTP {doc.http_status_code}
              </span>
            )}
            <a
              href={doc.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-0.5 hover:text-emerald-600"
            >
              <ExternalLink className="h-3 w-3" /> URL
            </a>
          </div>

          {/* Admin: replacement URL input for url_dead docs */}
          {isAdmin && doc.lifecycle_state === 'url_dead' && (
            <div className="mt-2">
              <p className="text-xs text-amber-700 font-medium mb-1">
                ⚠ URL returned 404 — provide a replacement URL to supersede this document:
              </p>
              <div className="flex gap-2">
                <Input
                  className="h-7 text-xs"
                  placeholder="https://..."
                  value={replacementUrl}
                  onChange={e => setReplacementUrl(e.target.value)}
                />
                <Button
                  size="sm"
                  className="h-7 text-xs bg-amber-600 hover:bg-amber-700"
                  onClick={handleReplace}
                  disabled={submitting}
                >
                  {submitting ? '...' : 'Replace'}
                </Button>
              </div>
              {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
            </div>
          )}

          {/* Read-only url_dead notice for non-admins */}
          {!isAdmin && doc.lifecycle_state === 'url_dead' && (
            <p className="mt-1 text-xs text-amber-600">
              URL returned 404. Admin login required to provide a replacement.
            </p>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 text-slate-400 hover:text-slate-700"
          title="View history"
          onClick={() => onHistoryClick(doc)}
        >
          <History className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

interface LGAGroupProps {
  group: LGADocumentGroup;
  isAdmin: boolean;
  defaultOpen?: boolean;
  onHistoryClick: (doc: LifecycleDocumentEntry) => void;
  onReplaced: (fileId: string, newUrl: string) => void;
}

function LGAGroup({ group, isAdmin, defaultOpen = false, onHistoryClick, onReplaced }: LGAGroupProps) {
  const [open, setOpen] = useState(defaultOpen);
  const deadCount = group.documents.filter(d => d.lifecycle_state === 'url_dead').length;

  return (
    <div className="border rounded-lg mb-2 overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
        onClick={() => setOpen(v => !v)}
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
          <span className="font-medium text-slate-700">{group.lga_name}</span>
          <span className="text-xs text-slate-400">({group.documents.length} docs)</span>
          {deadCount > 0 && (
            <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-medium">
              {deadCount} dead URL{deadCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </button>

      {open && (
        <div>
          {group.documents.map(doc => (
            <DocumentRow
              key={doc.file_id}
              doc={doc}
              isAdmin={isAdmin}
              onHistoryClick={onHistoryClick}
              onReplaced={onReplaced}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  groups: LGADocumentGroup[];
  isAdmin: boolean;
  onHistoryClick: (doc: LifecycleDocumentEntry) => void;
  onDocumentReplaced: () => void;
}

export function LGADocumentTable({ groups, isAdmin, onHistoryClick, onDocumentReplaced }: Props) {
  const handleReplaced = (_fileId: string, _newUrl: string) => {
    onDocumentReplaced();
  };

  return (
    <div>
      {groups.map(group => (
        <LGAGroup
          key={group.lga_name}
          group={group}
          isAdmin={isAdmin}
          defaultOpen={group.lga_name === 'All LGAs'}
          onHistoryClick={onHistoryClick}
          onReplaced={handleReplaced}
        />
      ))}
      {groups.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-8">No documents found.</p>
      )}
    </div>
  );
}
