# GreenGovRAG Frontend

React + TypeScript frontend for the GreenGovRAG AI assistant, providing an intuitive interface for querying Australian environmental regulations.

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API URL and MapBox token

# Start development server
npm run dev
# Visit: http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 6
- **Styling**: Tailwind CSS 4
- **UI Components**: shadcn/ui
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Maps**: MapBox GL JS
- **Linting**: ESLint
- **Type Checking**: TypeScript 5

## Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   └── ui/            # shadcn/ui components
│   ├── lib/               # Utilities and helpers
│   ├── types/             # TypeScript type definitions
│   ├── App.tsx            # Main application component
│   ├── main.tsx           # Application entry point
│   └── index.css          # Global styles + Tailwind
├── public/                # Static assets
├── index.html             # HTML template
├── vite.config.ts         # Vite configuration
├── tailwind.config.js     # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
└── package.json           # Dependencies
```

## Features

### Current Features

- **Query Interface**: Clean, intuitive search interface for environmental regulations
- **Location Filtering**: Optional LGA (Local Government Area) filtering for geospatial queries
- **Responsive Design**: Mobile-first, works on all screen sizes
- **Professional Theme**: Light mode with emerald/green gradient design matching documentation
- **Real-time Results**: Streaming responses with citation links
- **Error Handling**: Graceful error states and loading indicators

### Planned Features (WIP)

- MapBox integration for geospatial visualization
- Query history
- Document source filtering
- Advanced search options
- User authentication
- Dark mode toggle

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# MapBox token (optional, for future map features)
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

### Theme Customization

The frontend uses a professional emerald/green theme matching the documentation site. To customize:

**Colors** (`tailwind.config.js`):
```js
theme: {
  extend: {
    colors: {
      // Primary colors
      emerald: colors.emerald,
      green: colors.green,
      // Add custom colors
    }
  }
}
```

**Gradients** (`src/index.css`):
```css
/* Header gradient: emerald-50 → green-50 → emerald-50 */
.header-gradient {
  background: linear-gradient(to right, #ecfdf5, #f0fdf4, #ecfdf5);
}
```

## Available Scripts

```bash
# Development
npm run dev              # Start dev server (port 5173)

# Building
npm run build            # Build for production
npm run preview          # Preview production build

# Code Quality
npm run lint             # Run ESLint
npm run type-check       # Run TypeScript compiler

# Component Library
npx shadcn@latest add button   # Add shadcn/ui components
```

## Adding Components

### Using shadcn/ui

```bash
# Add a component
npx shadcn@latest add card

# Use in your code
import { Card } from '@/components/ui/card'
```

### Custom Components

```tsx
// src/components/MyComponent.tsx
import React from 'react'

interface MyComponentProps {
  title: string
  children?: React.ReactNode
}

export function MyComponent({ title, children }: MyComponentProps) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold">{title}</h2>
      {children}
    </div>
  )
}
```

## API Integration

### Query API

```typescript
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface QueryRequest {
  query: string
  lga_name?: string
  top_k?: number
}

interface QueryResponse {
  answer: string
  sources: Array<{
    title: string
    url: string
    jurisdiction: string
  }>
  confidence: number
}

export async function queryRAG(params: QueryRequest): Promise<QueryResponse> {
  const response = await axios.post(`${API_URL}/api/query`, params)
  return response.data
}
```

## Styling Guide

### Tailwind CSS

Follow Tailwind's utility-first approach:

```tsx
// Good: Utility classes
<button className="px-4 py-2 bg-emerald-500 text-white rounded-md hover:bg-emerald-600">
  Submit
</button>

// Avoid: Inline styles
<button style={{ padding: '8px 16px', backgroundColor: '#10b981' }}>
  Submit
</button>
```

### Component Variants

Use `className` composition:

```tsx
const buttonVariants = {
  primary: 'bg-emerald-500 hover:bg-emerald-600',
  secondary: 'bg-gray-200 hover:bg-gray-300',
}

<button className={`px-4 py-2 rounded-md ${buttonVariants.primary}`}>
  Primary
</button>
```

## Testing (Future)

```bash
# Unit tests (Vitest)
npm run test

# Component tests
npm run test:components

# E2E tests (Playwright)
npm run test:e2e
```

## Responsive Design

Breakpoints:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

```tsx
<div className="
  w-full           // Mobile: full width
  md:w-1/2         // Tablet: half width
  lg:w-1/3         // Desktop: one-third width
">
  Content
</div>
```

## Deployment

### AWS (via GitHub Actions)

Push to `main` branch triggers automatic deployment:

1. Build optimized production bundle
2. Upload to S3
3. Invalidate CloudFront cache
4. Deploy to: [CloudFront URL]

### Azure (via GitHub Actions)

Similar workflow for Azure Blob Storage + CDN.

### Manual Deployment

```bash
# Build
npm run build

# Output: dist/
# Upload dist/ to your hosting provider
```

## Troubleshooting

### Port 5173 Already in Use

```bash
# Use different port
npm run dev -- --port 5174
```

### Build Fails

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### TypeScript Errors

```bash
# Check types
npm run type-check

# Update TypeScript
npm install -D typescript@latest
```

### CORS Errors

Ensure backend is configured with correct CORS origins:

```python
# backend/green_gov_rag/config.py
CORS_ORIGINS = ["http://localhost:5173", "https://yourdomain.com"]
```

## Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [shadcn/ui](https://ui.shadcn.com)
- [TypeScript](https://www.typescriptlang.org)
- [Lucide Icons](https://lucide.dev)

## Contributing

See the main [Contributor Guide](../docs/docs_src/contributor-guide/overview.md) for:
- Code style guidelines
- Component patterns
- Pull request process
- Testing requirements

## License

Copyright © 2025-2026 Sundeep Anand. See [LICENSE](../LICENSE) for details.

---

**Status**: Work in Progress (WIP)
**Backend API**: See [backend/README.md](../backend/README.md)
**Documentation**: https://sdp5.github.io/green-gov-rag/
**Support**: [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
