import { Leaf, Github } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import PlaygroundPage from './pages/PlaygroundPage';
import './index.css';
import { useEffect, useState } from 'react';
import apiClient from './api/client';

function App() {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await apiClient.get('/health');
        setVersion(response.data.version || '');
      } catch {
        // Silently fail if health endpoint is not available
      }
    };
    fetchVersion();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-green-50/20">
      {/* Header */}
      <header className="border-b bg-gradient-to-r from-emerald-50/50 via-green-50/30 to-emerald-50/50 backdrop-blur-sm shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex h-16 items-center gap-8 justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
                <Leaf className="h-6 w-6 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-700 to-green-700 bg-clip-text text-transparent">GreenGovRAG</h1>
                  <Badge className="text-xs bg-green-100 text-green-700 hover:bg-green-200 border-0 shadow-none">Beta</Badge>
                </div>
                <p className="text-xs text-slate-600 font-medium">Australian Environmental Regulations</p>
              </div>
            </div>

            <a
              href="https://github.com/sdp5/green-gov-rag"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-slate-700 hover:text-emerald-600 transition-all hover:scale-105"
              aria-label="View on GitHub"
            >
              <Github className="h-5 w-5" />
              <span className="hidden sm:inline text-sm font-medium">GitHub</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full">
        <PlaygroundPage />
      </main>

      {/* Footer */}
      <footer className="border-t mt-8 bg-gradient-to-r from-emerald-50/50 via-green-50/30 to-emerald-50/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-slate-600">
            <p className="text-center md:text-left">
              © 2025 GreenGovRAG. AI Assistant for Australian Environmental & Planning Regulations. {version && `v${version}`}
            </p>
            <div className="flex items-center gap-4">
              <a href="#" className="hover:text-emerald-600 transition-colors font-medium">About</a>
              <Separator orientation="vertical" className="h-4 bg-slate-300" />
              <a href="#" className="hover:text-emerald-600 transition-colors font-medium">Documentation</a>
              <Separator orientation="vertical" className="h-4 bg-slate-300" />
              <a href="#" className="hover:text-emerald-600 transition-colors font-medium">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
