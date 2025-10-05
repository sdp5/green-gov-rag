# Frontend Implementation Guide

## ✅ Completed Setup

### Infrastructure
- ✅ React + Vite + TypeScript initialized
- ✅ Dependencies installed (React Router, Axios, Zustand, Mapbox, Plotly)
- ✅ Tailwind CSS configured
- ✅ Project structure created
- ✅ API client created (`src/api/client.ts`)
- ✅ TypeScript types defined (`src/types/api.ts`)
- ✅ Zustand stores created (`src/store/queryStore.ts`, `src/store/mapStore.ts`)
- ✅ Basic routing setup in `App.tsx`
- ✅ Environment variables (`.env`, `.env.example`)

### File Structure
```
frontend/src/
├── api/
│   └── client.ts           ✅ API client with endpoints
├── components/             📝 To be built
│   ├── layout/
│   ├── query/
│   ├── map/
│   └── analytics/
├── pages/                  📝 To be built (placeholders exist)
├── store/
│   ├── queryStore.ts       ✅ Query state management
│   └── mapStore.ts         ✅ Map state management
├── types/
│   └── api.ts              ✅ TypeScript interfaces
├── lib/
│   └── utils.ts            ✅ Utility functions
├── App.tsx                 ✅ Basic routing
└── index.css               ✅ Tailwind setup
```

---

## 📋 Next Steps: Component Implementation

### 1. Install shadcn/ui Components

```bash
cd frontend

# Install clsx and tailwind-merge (already done)
# Add shadcn components:
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add select
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add skeleton
```

### 2. Build Query Page

Create `src/pages/QueryPage.tsx`:
```typescript
import { useState } from 'react';
import { useQueryStore } from '../store/queryStore';
import { queryAPI } from '../api/client';

export default function QueryPage() {
  const { query, setQuery, filters, setFilters, setResults, setLoading } = useQueryStore();

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const result = await queryAPI.execute(query, filters);
      setResults(result);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="space-y-4">
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a question..."
        className="w-full p-4 border rounded"
      />

      {/* Add filter selects here */}

      <button onClick={handleSubmit}>
        Search
      </button>

      {/* Display results */}
    </div>
  );
}
```

### 3. Build Map Page with Mapbox

Create `src/pages/MapPage.tsx`:
```typescript
import Map, { Source, Layer } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useMapStore } from '../store/mapStore';
import { useEffect, useState } from 'react';
import { mapAPI } from '../api/client';

export default function MapPage() {
  const { viewport, setViewport, selectedLGAs, addLGA } = useMapStore();
  const [geojson, setGeojson] = useState(null);

  useEffect(() => {
    mapAPI.getLGAs().then(setGeojson);
  }, []);

  return (
    <div className="h-[600px]">
      <Map
        {...viewport}
        onMove={evt => setViewport(evt.viewState)}
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        mapStyle="mapbox://styles/mapbox/light-v11"
      >
        {geojson && (
          <Source id="lgas" type="geojson" data={geojson}>
            <Layer
              id="lga-fills"
              type="fill"
              paint={{
                'fill-color': '#088',
                'fill-opacity': 0.4
              }}
            />
          </Source>
        )}
      </Map>
    </div>
  );
}
```

### 4. Build Analytics Page with Plotly

Create `src/pages/AnalyticsPage.tsx`:
```typescript
import Plot from 'react-plotly.js';
import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api/client';
import type { AnalyticsStats } from '../types/api';

export default function AnalyticsPage() {
  const [stats, setStats] = useState<AnalyticsStats | null>(null);

  useEffect(() => {
    analyticsAPI.getStats().then(setStats);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold mb-4">Documents by Jurisdiction</h3>
        <Plot
          data={[{
            x: stats.documents_by_jurisdiction.map(d => d.name),
            y: stats.documents_by_jurisdiction.map(d => d.count),
            type: 'bar',
          }]}
          layout={{ autosize: true }}
        />
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Documents by Topic</h3>
        <Plot
          data={[{
            labels: stats.documents_by_topic.map(d => d.name),
            values: stats.documents_by_topic.map(d => d.count),
            type: 'pie',
          }]}
          layout={{ autosize: true }}
        />
      </div>
    </div>
  );
}
```

### 5. Build Sources Page

Create `src/pages/SourcesPage.tsx`:
```typescript
import { useEffect, useState } from 'react';
import { documentsAPI } from '../api/client';
import type { DocumentListResponse } from '../types/api';

export default function SourcesPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [filters, setFilters] = useState({});

  useEffect(() => {
    documentsAPI.list(filters).then(setData);
  }, [filters]);

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Documents ({data.total})</h2>

      {/* Add filters here */}

      <div className="space-y-4">
        {data.documents.map(doc => (
          <div key={doc.id} className="border p-4 rounded">
            <h3 className="font-semibold">{doc.title}</h3>
            <p className="text-sm text-muted-foreground">
              {doc.jurisdiction} | {doc.topic} | {doc.region}
            </p>
            <a href={doc.source_url} className="text-primary text-sm">
              View Source
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 6. Update App.tsx to use new pages

Replace placeholder functions with actual imports:
```typescript
import QueryPage from './pages/QueryPage';
import MapPage from './pages/MapPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SourcesPage from './pages/SourcesPage';
```

---

## 🚀 Running the Frontend

```bash
cd frontend

# Development
npm run dev

# Build
npm run build

# Preview production build
npm run preview
```

Access at: http://localhost:5173

---

## 🔧 Configuration

### Environment Variables
Edit `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000/api
VITE_MAPBOX_TOKEN=your_actual_token
```

Get Mapbox token: https://account.mapbox.com/access-tokens/

---

## 📚 Resources

- **shadcn/ui**: https://ui.shadcn.com/docs
- **Mapbox GL**: https://docs.mapbox.com/mapbox-gl-js/
- **Plotly React**: https://plotly.com/javascript/react/
- **Zustand**: https://docs.pmnd.rs/zustand/
- **React Router**: https://reactrouter.com/

---

## 🎯 Priority Order

1. **Query Page** - Core functionality
2. **Sources Page** - Document browsing
3. **Analytics Page** - Data visualization
4. **Map Page** - Geographic features

---

## ⚡ Quick Wins

- Use shadcn/ui components for consistent UI
- API client is ready - just call the functions
- Stores are set up - use hooks in components
- Types are defined - TypeScript will help

---

## 🐛 Troubleshooting

**Mapbox not loading:**
- Check VITE_MAPBOX_TOKEN in .env
- Ensure mapbox-gl CSS is imported

**API calls failing:**
- Verify backend is running on port 8000
- Check CORS settings in backend

**Build errors:**
- Run `npm install` to ensure all deps are installed
- Check TypeScript errors with `npx tsc --noEmit`
