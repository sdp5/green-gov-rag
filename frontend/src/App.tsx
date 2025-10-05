import { Leaf } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
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
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-green-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex h-16 items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
                <Leaf className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">GreenGovRAG</h1>
                <p className="text-xs text-gray-600">Australian Environmental Regulations</p>
              </div>
            </div>

          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full">
        <PlaygroundPage />
      </main>

      {/* Footer */}
      <footer className="border-t mt-12 bg-green-50">
        <div className="container mx-auto px-4 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-600">
            <p>© 2025 GreenGovRAG. AI Assistant for Australian Environmental & Planning Regulations. {version && `v${version}`}</p>
            <div className="flex items-center gap-4">
              <a href="#" className="hover:text-gray-900 transition-colors">About</a>
              <Separator orientation="vertical" className="h-4 bg-gray-300" />
              <a href="#" className="hover:text-gray-900 transition-colors">Documentation</a>
              <Separator orientation="vertical" className="h-4 bg-gray-300" />
              <a href="#" className="hover:text-gray-900 transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
