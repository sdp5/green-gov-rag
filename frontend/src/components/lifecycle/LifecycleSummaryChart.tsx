import Plot from 'react-plotly.js';
import type { LifecycleSummary, LifecycleState } from '@/types/lifecycle';

const STATE_COLORS: Record<LifecycleState, string> = {
  detect: '#3b82f6',
  fetch: '#60a5fa',
  chunk: '#93c5fd',
  embed: '#bfdbfe',
  available_for_search: '#22c55e',
  url_dead: '#f59e0b',
  mark_superseded: '#ef4444',
  removed_from_search: '#991b1b',
};

const STATE_LABELS: Record<LifecycleState, string> = {
  detect: 'Detected',
  fetch: 'Fetching',
  chunk: 'Chunking',
  embed: 'Embedding',
  available_for_search: 'In Search',
  url_dead: 'URL Dead',
  mark_superseded: 'Superseded',
  removed_from_search: 'Removed',
};

const STATES: LifecycleState[] = [
  'detect', 'fetch', 'chunk', 'embed',
  'available_for_search', 'url_dead', 'mark_superseded', 'removed_from_search',
];

interface Props {
  summary: LifecycleSummary;
  onStateClick?: (state: LifecycleState | 'all') => void;
}

export function LifecycleSummaryChart({ summary, onStateClick }: Props) {
  const values = STATES.map(s => summary[s]);
  const labels = STATES.map(s => STATE_LABELS[s]);
  const colors = STATES.map(s => STATE_COLORS[s]);

  return (
    <Plot
      data={[
        {
          type: 'pie',
          hole: 0.55,
          values,
          labels,
          marker: { colors },
          textinfo: 'label+value',
          hovertemplate: '<b>%{label}</b><br>%{value} files (%{percent})<extra></extra>',
          sort: false,
        },
      ]}
      layout={{
        margin: { t: 10, b: 10, l: 10, r: 10 },
        showlegend: false,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        height: 260,
        annotations: [
          {
            text: `${summary.total_files}<br><span style="font-size:11px">files</span>`,
            x: 0.5,
            y: 0.5,
            font: { size: 20, color: '#1e293b' },
            showarrow: false,
          },
        ],
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
      onClick={(event) => {
        if (onStateClick && event.points[0]) {
          const clickedLabel = String(((event.points[0] as unknown) as Record<string, unknown>).label ?? '');
          const state = STATES.find(s => STATE_LABELS[s] === clickedLabel);
          onStateClick(state ?? 'all');
        }
      }}
    />
  );
}
