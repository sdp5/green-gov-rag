import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { lifecycleAPI } from '@/api/lifecycle';
import type { RegisterDocumentRequest } from '@/types/lifecycle';

interface Props {
  onRegistered: () => void;
}

const EMPTY_FORM: RegisterDocumentRequest = {
  title: '',
  source_url: '',
  download_urls: [],
  jurisdiction: '',
  category: '',
  topic: '',
  region: '',
  spatial_metadata: {
    lga_names: [],
    applies_to_all_lgas: false,
  },
};

export function RegisterDocumentForm({ onRegistered }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<RegisterDocumentRequest>(EMPTY_FORM);
  const [downloadUrlsText, setDownloadUrlsText] = useState('');
  const [lgaNamesText, setLgaNamesText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async () => {
    setError('');
    setSuccess('');

    const urls = downloadUrlsText.split('\n').map(u => u.trim()).filter(Boolean);
    if (!form.title || !form.source_url || !urls.length || !form.jurisdiction || !form.category || !form.topic) {
      setError('Please fill in all required fields.');
      return;
    }

    const lgas = lgaNamesText.split(',').map(l => l.trim()).filter(Boolean);
    const payload: RegisterDocumentRequest = {
      ...form,
      download_urls: urls,
      spatial_metadata: {
        lga_names: lgas,
        applies_to_all_lgas: lgas.length === 0,
        spatial_scope: form.jurisdiction,
      },
    };

    setSubmitting(true);
    try {
      const result = await lifecycleAPI.register(payload);
      setSuccess(`Registered: ${result.source_id}. Will be ingested on next monitoring run.`);
      setForm(EMPTY_FORM);
      setDownloadUrlsText('');
      setLgaNamesText('');
      onRegistered();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to register document.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border rounded-lg overflow-hidden mt-4">
      <button
        className="w-full flex items-center gap-2 px-4 py-3 bg-emerald-50 hover:bg-emerald-100 transition-colors text-left"
        onClick={() => setOpen(v => !v)}
      >
        {open ? <ChevronDown className="h-4 w-4 text-emerald-600" /> : <ChevronRight className="h-4 w-4 text-emerald-600" />}
        <Plus className="h-4 w-4 text-emerald-600" />
        <span className="font-medium text-emerald-700">Register New Document</span>
      </button>

      {open && (
        <div className="p-4 space-y-3 bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Title *</label>
              <Input
                placeholder="e.g. EPBC Act 2025"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Source URL *</label>
              <Input
                placeholder="https://legislation.gov.au/..."
                value={form.source_url}
                onChange={e => setForm(f => ({ ...f, source_url: e.target.value }))}
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Jurisdiction *</label>
              <Select value={form.jurisdiction} onValueChange={v => setForm(f => ({ ...f, jurisdiction: v }))}>
                <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="federal">Federal</SelectItem>
                  <SelectItem value="state">State</SelectItem>
                  <SelectItem value="local">Local</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Category *</label>
              <Input
                placeholder="e.g. legislation, policy, building"
                value={form.category}
                onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Topic *</label>
              <Input
                placeholder="e.g. biodiversity, emissions, planning"
                value={form.topic}
                onChange={e => setForm(f => ({ ...f, topic: e.target.value }))}
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Region</label>
              <Input
                placeholder="e.g. Australia, New South Wales"
                value={form.region ?? ''}
                onChange={e => setForm(f => ({ ...f, region: e.target.value }))}
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">
              Download URLs * <span className="font-normal text-slate-400">(one per line)</span>
            </label>
            <Textarea
              rows={3}
              placeholder="https://example.gov.au/doc1.pdf&#10;https://example.gov.au/doc2.pdf"
              value={downloadUrlsText}
              onChange={e => setDownloadUrlsText(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">
              LGA Names <span className="font-normal text-slate-400">(comma-separated; leave blank for federal/state)</span>
            </label>
            <Input
              placeholder="Adelaide City Council, Burnside, Campbelltown"
              value={lgaNamesText}
              onChange={e => setLgaNamesText(e.target.value)}
            />
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
          {success && <p className="text-xs text-green-700 bg-green-50 px-3 py-2 rounded">{success}</p>}

          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Registering...' : 'Register Document'}
          </Button>
        </div>
      )}
    </div>
  );
}
