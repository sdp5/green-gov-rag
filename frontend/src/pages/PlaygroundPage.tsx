import { useState, useEffect, useMemo } from 'react';
import { useQueryStore } from '@/store/queryStore';
import { useMapStore } from '@/store/mapStore';
import { queryAPI, documentsAPI, analyticsAPI, mapAPI } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, ChevronLeft, ChevronRight, BarChart3, FileText, ChevronUp, ChevronDown } from 'lucide-react';
import { REGIONS, JURISDICTIONS, TOPICS } from '@/commons/constants';
import Map, { Source, Layer, NavigationControl, type MapMouseEvent, type ViewStateChangeEvent } from 'react-map-gl/mapbox';
import type { FillLayer, LineLayer } from 'mapbox-gl';
import type { AnalyticsStats, DocumentListResponse } from '@/types/api';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

export default function PlaygroundPage() {
  // Sidebar state
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [rightTab, setRightTab] = useState('sources');

  // Query state
  const { query, setQuery, filters, setFilters, results, isLoading, setResults, setLoading } = useQueryStore();
  const [queryError, setQueryError] = useState<string | null>(null);

  // Map state
  const { viewport, setViewport, selectedLGAs, addLGA, removeLGA, clearLGAs } = useMapStore();
  const [geojson, setGeojson] = useState<unknown>(null);
  const [mapLoading, setMapLoading] = useState(true);
  const [hoveredLGA, setHoveredLGA] = useState<string | null>(null);

  // Analytics state
  const [stats, setStats] = useState<AnalyticsStats | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  // Sources state
  const [documents, setDocuments] = useState<DocumentListResponse | null>(null);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesFilters, setSourcesFilters] = useState<Record<string, unknown>>({});

  // Load map data (only once)
  useEffect(() => {
    const fetchLGAs = async () => {
      setMapLoading(true);
      try {
        const data = await mapAPI.getLGAs();
        setGeojson(data);
      } catch (err) {
        console.error('Failed to load map:', err);
      } finally {
        setMapLoading(false);
      }
    };
    // Only fetch if we don't have the data yet
    if (leftSidebarOpen && !geojson) {
      fetchLGAs();
    }
  }, [leftSidebarOpen, geojson]);

  // Load analytics data
  useEffect(() => {
    const fetchStats = async () => {
      setAnalyticsLoading(true);
      try {
        const result = await analyticsAPI.getStats();
        setStats(result);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      } finally {
        setAnalyticsLoading(false);
      }
    };
    if (rightSidebarOpen && rightTab === 'analytics') {
      fetchStats();
    }
  }, [rightSidebarOpen, rightTab]);

  // Load documents
  useEffect(() => {
    const fetchDocuments = async () => {
      setSourcesLoading(true);
      try {
        const result = await documentsAPI.list(sourcesFilters);
        setDocuments(result);
      } catch (err) {
        console.error('Failed to fetch documents:', err);
      } finally {
        setSourcesLoading(false);
      }
    };
    if (rightSidebarOpen && rightTab === 'sources') {
      fetchDocuments();
    }
  }, [rightSidebarOpen, rightTab, sourcesFilters]);

  // Query handlers
  const handleQuerySubmit = async () => {
    if (!query.trim()) {
      setQueryError('Please enter a query');
      return;
    }
    setQueryError(null);
    setLoading(true);
    try {
      const result = await queryAPI.execute(query, filters);
      setResults(result);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : 'Failed to execute query');
      setLoading(false);
    }
  };

  // Map handlers
  const enhancedGeojson = useMemo(() => {
    if (!geojson || typeof geojson !== 'object' || !('features' in geojson)) return null;
    const geoData = geojson as { features: Array<{ properties?: Record<string, unknown>; [key: string]: unknown }> };
    return {
      ...geoData,
      features: geoData.features.map((feature) => {
        const lgaNameArray = feature.properties?.lga_name || feature.properties?.name || feature.properties?.LGA_NAME;
        const lgaName = Array.isArray(lgaNameArray) ? lgaNameArray[0] : lgaNameArray;
        return {
          ...feature,
          properties: {
            ...feature.properties,
            lga_name_str: lgaName,
            selected: selectedLGAs.includes(lgaName as string),
          },
        };
      }),
    };
  }, [geojson, selectedLGAs]);

  const handleMapClick = (event: MapMouseEvent & { features?: Array<{ properties?: Record<string, unknown> }> }) => {
    const feature = event.features?.[0];
    if (feature && feature.properties) {
      let lgaNameArray = feature.properties.lga_name || feature.properties.name || feature.properties.LGA_NAME;
      if (typeof lgaNameArray === 'string' && lgaNameArray.startsWith('[')) {
        try {
          lgaNameArray = JSON.parse(lgaNameArray);
        } catch {
          // Failed to parse, use as-is
        }
      }
      const lgaName = Array.isArray(lgaNameArray) ? lgaNameArray[0] : lgaNameArray;
      if (lgaName) {
        if (selectedLGAs.includes(lgaName as string)) {
          removeLGA(lgaName as string);
        } else {
          addLGA(lgaName as string);
        }
      }
    }
  };

  const handleMouseMove = (event: MapMouseEvent & { features?: Array<{ properties?: Record<string, unknown> }> }) => {
    const feature = event.features?.[0];
    if (feature && feature.properties) {
      let lgaNameArray = feature.properties.lga_name || feature.properties.name || feature.properties.LGA_NAME;
      if (typeof lgaNameArray === 'string' && lgaNameArray.startsWith('[')) {
        try {
          lgaNameArray = JSON.parse(lgaNameArray);
        } catch {
          // Failed to parse, use as-is
        }
      }
      const lgaName = Array.isArray(lgaNameArray) ? lgaNameArray[0] : lgaNameArray;
      setHoveredLGA(lgaName as string);
    }
  };

  const handleMouseLeave = () => {
    setHoveredLGA(null);
  };

  const panMap = (direction: 'up' | 'down' | 'left' | 'right') => {
    const panAmount = 0.5; // Adjust pan distance
    const newViewport = { ...viewport };

    switch (direction) {
      case 'up':
        newViewport.latitude += panAmount;
        break;
      case 'down':
        newViewport.latitude -= panAmount;
        break;
      case 'left':
        newViewport.longitude -= panAmount;
        break;
      case 'right':
        newViewport.longitude += panAmount;
        break;
    }

    setViewport(newViewport);
  };

  const layerStyle: FillLayer = {
    id: 'lga-fills',
    type: 'fill',
    paint: {
      'fill-color': ['case', ['==', ['get', 'selected'], true], '#16a34a', '#e2e8f0'],
      'fill-opacity': ['case', ['==', ['get', 'selected'], true], 0.7, 0.2],
    },
  };

  const lineLayerStyle: LineLayer = {
    id: 'lga-lines',
    type: 'line',
    paint: { 'line-color': '#cbd5e1', 'line-width': 1 },
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left Sidebar - Map */}
      {leftSidebarOpen && (
        <aside className="w-[600px] border-r bg-gradient-to-b from-green-50/30 to-background overflow-y-auto flex-shrink-0">
          <div className="px-6 py-5 border-b bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <MapPin className="h-5 w-5 text-green-700" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 text-lg">Geographic Filter</h3>
                  <p className="text-xs text-gray-600">Click LGAs on map to filter</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setLeftSidebarOpen(false)}
                className="hover:bg-white/50"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="px-6 py-5 space-y-5">
            {/* Selected LGAs */}
            <div className="bg-white rounded-lg border p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold text-foreground">
                  Selected Regions <span className="text-muted-foreground">({selectedLGAs.length})</span>
                </p>
                {selectedLGAs.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={clearLGAs} className="h-7 text-xs">
                    Clear All
                  </Button>
                )}
              </div>
              {selectedLGAs.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-3">
                  No regions selected
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedLGAs.map((lga) => (
                    <Badge
                      key={lga}
                      variant="secondary"
                      className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground transition-colors px-3 py-1"
                      onClick={() => removeLGA(lga)}
                    >
                      {lga}
                      <span className="ml-1.5 font-bold">×</span>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Map */}
            {MAPBOX_TOKEN ? (
              <div className="border-2 rounded-xl overflow-hidden shadow-md bg-white">
                {mapLoading ? (
                  <div className="h-[600px] flex items-center justify-center bg-muted/20">
                    <div className="text-center space-y-3">
                      <Skeleton className="h-8 w-32 mx-auto" />
                      <p className="text-sm text-muted-foreground">Loading map data...</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-[600px] relative">
                    <Map
                      {...viewport}
                      onMove={(evt: ViewStateChangeEvent) => setViewport(evt.viewState)}
                      mapboxAccessToken={MAPBOX_TOKEN}
                      mapStyle="mapbox://styles/mapbox/light-v11"
                      interactiveLayerIds={enhancedGeojson ? ['lga-fills'] : undefined}
                      onClick={handleMapClick}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={handleMouseLeave}
                      cursor={hoveredLGA ? 'pointer' : 'grab'}
                    >
                      <NavigationControl position="top-right" showCompass={false} />
                      {enhancedGeojson && (
                        <Source
                          key={`lgas-${selectedLGAs.join('-')}`}
                          id="lgas"
                          type="geojson"
                          data={enhancedGeojson}
                        >
                          <Layer {...layerStyle} />
                          <Layer {...lineLayerStyle} />
                        </Source>
                      )}
                    </Map>
                    {/* Hover tooltip */}
                    {hoveredLGA && (
                      <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-sm px-3 py-2 rounded-lg shadow-lg border text-sm font-medium">
                        {hoveredLGA}
                      </div>
                    )}
                    {/* Custom Navigation Controls */}
                    <div className="absolute bottom-4 left-4 flex flex-col gap-1.5 bg-white/90 backdrop-blur-sm p-2 rounded-lg shadow-lg">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-9 w-9 p-0 hover:bg-green-100"
                        onClick={() => panMap('up')}
                        title="Pan North"
                      >
                        <ChevronUp className="h-5 w-5" />
                      </Button>
                      <div className="flex gap-1.5">
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-9 w-9 p-0 hover:bg-green-100"
                          onClick={() => panMap('left')}
                          title="Pan West"
                        >
                          <ChevronLeft className="h-5 w-5" />
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-9 w-9 p-0 hover:bg-green-100"
                          onClick={() => panMap('right')}
                          title="Pan East"
                        >
                          <ChevronRight className="h-5 w-5" />
                        </Button>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-9 w-9 p-0 hover:bg-green-100"
                        onClick={() => panMap('down')}
                        title="Pan South"
                      >
                        <ChevronDown className="h-5 w-5" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Card className="border-2">
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground text-center">Map requires VITE_MAPBOX_TOKEN environment variable</p>
                </CardContent>
              </Card>
            )}
          </div>
        </aside>
      )}

      {/* Main Content - Query */}
      <main className="flex-1 overflow-y-auto px-6">
        {/* Toggle Left Sidebar */}
        {!leftSidebarOpen && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setLeftSidebarOpen(true)}
            className="fixed left-4 top-20 z-10 bg-background shadow-md"
          >
            <MapPin className="h-4 w-4 mr-1" />
            Map
          </Button>
        )}

        {/* Toggle Right Sidebar */}
        {!rightSidebarOpen && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRightSidebarOpen(true)}
            className="fixed right-4 top-20 z-10 bg-background shadow-md"
          >
            <BarChart3 className="h-4 w-4 mr-1" />
            Info
          </Button>
        )}

        <div className="mx-auto py-12 max-w-4xl">
          <div className="space-y-6">
            {/* Hero */}
            <div className="text-center space-y-6 py-8 px-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-50 border border-green-200">
                <span className="text-green-600 text-sm font-medium">🌿 Environmental Intelligence</span>
              </div>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">
                Australian Environmental Regulations
              </h1>
              <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                Navigate Australian environmental and planning regulations with AI-powered insights. Ask questions, explore documents, and discover what applies to your location.
              </p>
            </div>

            {/* LGA Indicator */}
            {selectedLGAs.length > 0 && (
              <Card className="border-2 border-green-300 bg-gradient-to-r from-green-50 to-emerald-50 shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="p-1.5 bg-green-100 rounded-lg">
                          <MapPin className="h-4 w-4 text-green-700" />
                        </div>
                        <p className="text-sm font-semibold text-green-900">
                          Filtering by {selectedLGAs.length} Region{selectedLGAs.length > 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedLGAs.map((lga) => (
                          <Badge key={lga} variant="secondary" className="text-xs font-medium bg-white">
                            {lga}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearLGAs}
                      className="hover:bg-white/50 font-medium"
                    >
                      Clear
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Query Form */}
            <Card className="border-2 shadow-sm">
              <CardHeader className="pb-4">
                <CardTitle className="text-xl">Ask About Regulations</CardTitle>
                <CardDescription className="text-base">
                  Enter your question about environmental or planning regulations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        handleQuerySubmit();
                      }
                    }}
                    placeholder="e.g., Do I need an environmental impact assessment to build a solar farm in regional NSW?"
                    className="min-h-[140px] resize-none text-base"
                  />
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <kbd className="px-2 py-0.5 rounded bg-muted text-xs">⌘</kbd> +
                    <kbd className="px-2 py-0.5 rounded bg-muted text-xs">Enter</kbd> to submit
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Region</label>
                    <Select
                      value={filters.region || 'all'}
                      onValueChange={(value) => setFilters({ region: value === 'all' ? undefined : value })}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="All regions" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All regions</SelectItem>
                        {REGIONS.map((region) => (
                          <SelectItem key={region} value={region}>
                            {region}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Jurisdiction</label>
                    <Select
                      value={filters.jurisdiction || 'all'}
                      onValueChange={(value) => setFilters({ jurisdiction: value === 'all' ? undefined : value })}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="All jurisdictions" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All jurisdictions</SelectItem>
                        {JURISDICTIONS.map((jurisdiction) => (
                          <SelectItem key={jurisdiction} value={jurisdiction}>
                            {jurisdiction}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Topics</label>
                    <Select
                      value={filters.topics?.[0] || 'all'}
                      onValueChange={(value) => setFilters({ topics: value === 'all' ? undefined : [value] })}
                    >
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="All topics" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All topics</SelectItem>
                        {TOPICS.map((topic) => (
                          <SelectItem key={topic} value={topic}>
                            {topic}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={handleQuerySubmit}
                    disabled={isLoading}
                    className="flex-1 h-12 text-base font-medium bg-green-600 hover:bg-green-700"
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Searching...
                      </span>
                    ) : (
                      'Search Regulations'
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setQuery('');
                      setFilters({});
                      setResults(null);
                      setQueryError(null);
                    }}
                    className="h-12 px-6"
                  >
                    Clear
                  </Button>
                </div>

                {queryError && (
                  <div className="text-sm text-destructive bg-destructive/10 p-4 rounded-lg border border-destructive/20">
                    <strong>Error:</strong> {queryError}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Loading */}
            {isLoading && (
              <Card className="border-2 shadow-md">
                <CardHeader className="pb-4">
                  <div className="flex items-center gap-3">
                    <div className="animate-pulse">
                      <div className="h-6 w-6 bg-green-500 rounded-full"></div>
                    </div>
                    <Skeleton className="h-6 w-40" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </CardContent>
              </Card>
            )}

            {/* Results */}
            {!isLoading && results && (
              <div className="space-y-6">
                <Card className="border-2 shadow-md bg-gradient-to-br from-green-50/30 to-white">
                  <CardHeader className="pb-4 border-b bg-gradient-to-r from-green-50/50 to-transparent">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xl flex items-center gap-2">
                        <span className="text-2xl">💡</span>
                        Answer
                      </CardTitle>
                      {results.response_time_ms && (
                        <Badge variant="secondary" className="text-xs font-mono">
                          {results.response_time_ms.toFixed(0)}ms
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-6">
                    <p className="text-base leading-relaxed whitespace-pre-wrap text-foreground">{results.answer}</p>
                  </CardContent>
                </Card>

                {results.sources && results.sources.length > 0 && (
                  <Card className="border-2 shadow-md">
                    <CardHeader className="pb-4 border-b">
                      <CardTitle className="text-xl flex items-center gap-2">
                        <span className="text-2xl">📚</span>
                        Sources
                        <Badge variant="outline" className="ml-2">{results.sources.length}</Badge>
                      </CardTitle>
                      <CardDescription className="text-sm">
                        Referenced documents from Australian regulations
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                      <div className="space-y-4">
                        {results.sources.map((source: { title?: string; jurisdiction?: string; topic?: string; excerpt?: string; source_url?: string }, idx: number) => (
                          <div key={idx} className="border-2 rounded-xl p-5 hover:shadow-lg hover:border-green-200 transition-all bg-white">
                            <div className="flex items-start gap-3 mb-3">
                              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-bold text-sm">
                                {idx + 1}
                              </div>
                              <div className="flex-1">
                                <h4 className="font-semibold text-base mb-2 leading-tight">{source.title}</h4>
                                <div className="flex flex-wrap gap-2">
                                  {source.jurisdiction && (
                                    <Badge variant="secondary" className="font-medium">
                                      📍 {source.jurisdiction}
                                    </Badge>
                                  )}
                                  {source.topic && (
                                    <Badge variant="outline" className="font-medium">
                                      🏷️ {source.topic}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </div>
                            {source.excerpt && (
                              <p className="text-sm text-muted-foreground mb-3 pl-11 line-clamp-3 italic border-l-2 border-green-200 pl-4">
                                "{source.excerpt}"
                              </p>
                            )}
                            {source.source_url && (
                              <div className="pl-11">
                                <a
                                  href={source.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-primary hover:underline font-medium inline-flex items-center gap-1"
                                >
                                  View Full Document →
                                </a>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Right Sidebar - Analytics & Sources */}
      {rightSidebarOpen && (
        <aside className="w-80 border-l bg-gradient-to-b from-green-50/30 to-background overflow-y-auto flex-shrink-0">
          <div className="px-6 py-5 border-b bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-green-700" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg">Data Explorer</h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRightSidebarOpen(false)}
                className="hover:bg-white/50"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <Tabs value={rightTab} onValueChange={setRightTab} className="w-full">
            <TabsList className="w-full grid grid-cols-2 rounded-none border-b mx-0 bg-background h-12">
              <TabsTrigger value="sources" className="rounded-none data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <FileText className="h-4 w-4 mr-2" />
                <span className="font-medium">Sources</span>
              </TabsTrigger>
              <TabsTrigger value="analytics" className="rounded-none data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <BarChart3 className="h-4 w-4 mr-2" />
                <span className="font-medium">Analytics</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="analytics" className="px-6 py-5 space-y-4 mt-0">
              {analyticsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="shadow-sm">
                      <CardHeader className="pb-3">
                        <Skeleton className="h-6 w-24" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-8 w-16" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : stats ? (
                <div className="space-y-4">
                  <Card className="shadow-sm border-2 bg-gradient-to-br from-green-50/50 to-white">
                    <CardHeader className="pb-3">
                      <CardDescription className="text-xs font-medium uppercase text-green-700">Total Documents</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-green-900">{stats.total_documents.toLocaleString()}</p>
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm border-2 bg-gradient-to-br from-emerald-50/50 to-white">
                    <CardHeader className="pb-3">
                      <CardDescription className="text-xs font-medium uppercase text-emerald-700">Total Queries</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-emerald-900">{stats.total_queries.toLocaleString()}</p>
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm border-2 bg-gradient-to-br from-teal-50/50 to-white">
                    <CardHeader className="pb-3">
                      <CardDescription className="text-xs font-medium uppercase text-teal-700">Avg Response Time</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-teal-900">
                        {stats.avg_response_time_ms ? `${stats.avg_response_time_ms.toFixed(0)}ms` : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>

                  {stats.documents_by_jurisdiction && stats.documents_by_jurisdiction.length > 0 && (
                    <Card className="shadow-sm border-2">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-semibold">Documents by Jurisdiction</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2.5">
                          {(stats as { documents_by_jurisdiction?: Array<{ name: string; count: number }> })?.documents_by_jurisdiction?.map((item) => (
                            <div key={item.name} className="flex justify-between items-center text-sm p-2 rounded bg-muted/30 hover:bg-muted/50 transition-colors">
                              <span className="font-medium">{item.name}</span>
                              <Badge variant="secondary" className="font-semibold">{item.count}</Badge>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ) : null}
            </TabsContent>

            <TabsContent value="sources" className="px-6 py-5 space-y-4 mt-0">
              <div className="space-y-3 bg-white rounded-lg border-2 p-3 shadow-sm">
                <label className="text-xs font-semibold uppercase text-muted-foreground">Filter Sources</label>
                <Select
                  value={(sourcesFilters.jurisdiction as string) || 'all'}
                  onValueChange={(value) =>
                    setSourcesFilters({ ...sourcesFilters, jurisdiction: value === 'all' ? undefined : value })
                  }
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Jurisdiction" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All jurisdictions</SelectItem>
                    {JURISDICTIONS.map((j) => (
                      <SelectItem key={j} value={j}>
                        {j}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={(sourcesFilters.topic as string) || 'all'}
                  onValueChange={(value) =>
                    setSourcesFilters({ ...sourcesFilters, topic: value === 'all' ? undefined : value })
                  }
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Topic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All topics</SelectItem>
                    {TOPICS.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {sourcesLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="shadow-sm">
                      <CardHeader className="pb-2">
                        <Skeleton className="h-4 w-full" />
                      </CardHeader>
                    </Card>
                  ))}
                </div>
              ) : documents ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between px-1">
                    <p className="text-xs font-semibold text-muted-foreground uppercase">
                      {(documents as { total: number })?.total} {(documents as { total: number })?.total === 1 ? 'Document' : 'Documents'}
                    </p>
                  </div>
                  {(documents as { documents: Array<{ id: string; title?: string; jurisdiction?: string; topic?: string; source_url?: string }> })?.documents?.slice(0, 10).map((doc) => (
                    <Card key={doc.id} className="hover:shadow-md transition-all border-2 hover:border-primary/20">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm leading-tight font-semibold">{doc.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="flex flex-wrap gap-1.5">
                          {doc.jurisdiction && (
                            <Badge variant="secondary" className="text-xs font-medium">
                              {doc.jurisdiction}
                            </Badge>
                          )}
                          {doc.topic && (
                            <Badge variant="outline" className="text-xs font-medium">
                              {doc.topic}
                            </Badge>
                          )}
                        </div>
                        {doc.source_url && (
                          <a
                            href={doc.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-1"
                          >
                            View Source →
                          </a>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : null}
            </TabsContent>
          </Tabs>
        </aside>
      )}
    </div>
  );
}
