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
import { MapPin, ChevronLeft, ChevronRight, BarChart3, FileText } from 'lucide-react';
import { REGIONS, JURISDICTIONS, TOPICS } from '@/commons/constants';
import Map, { Source, Layer, type MapMouseEvent, type ViewStateChangeEvent } from 'react-map-gl/mapbox';
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
        <aside className="w-[600px] border-r bg-card overflow-y-auto flex-shrink-0">
          <div className="px-6 py-4 border-b bg-green-50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-green-600" />
                <h3 className="font-semibold text-gray-900">Geographic Filter</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setLeftSidebarOpen(false)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-600">Select LGAs to filter queries</p>
          </div>

          <div className="px-6 py-4 space-y-4">
            {/* Selected LGAs */}
            <div>
              <p className="text-sm font-medium mb-2">Selected ({selectedLGAs.length})</p>
              {selectedLGAs.length === 0 ? (
                <p className="text-xs text-muted-foreground">No LGAs selected</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedLGAs.map((lga) => (
                    <Badge
                      key={lga}
                      variant="secondary"
                      className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
                      onClick={() => removeLGA(lga)}
                    >
                      {lga}
                      <span className="ml-1">×</span>
                    </Badge>
                  ))}
                </div>
              )}
              {selectedLGAs.length > 0 && (
                <Button variant="outline" size="sm" onClick={clearLGAs} className="mt-2 w-full">
                  Clear All
                </Button>
              )}
            </div>

            {/* Map */}
            {MAPBOX_TOKEN ? (
              <div className="border rounded-lg overflow-hidden">
                {mapLoading ? (
                  <div className="h-[600px] flex items-center justify-center">
                    <Skeleton className="h-8 w-32" />
                  </div>
                ) : (
                  <div className="h-[600px]">
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
                  </div>
                )}
              </div>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <p className="text-xs text-muted-foreground text-center">Map requires VITE_MAPBOX_TOKEN</p>
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
            <div className="text-center space-y-4 py-6 px-4">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
                AI Assistant for Australian Environmental Regulations
              </h2>
              <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                Navigate Australian environmental and planning regulations with AI-powered search.
              </p>
            </div>

            {/* LGA Indicator */}
            {selectedLGAs.length > 0 && (
              <Card className="border-green-200 bg-green-50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <MapPin className="h-4 w-4 text-green-600" />
                        <p className="text-sm font-medium">
                          Filtering by {selectedLGAs.length} LGA{selectedLGAs.length > 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedLGAs.map((lga) => (
                          <Badge key={lga} variant="secondary" className="text-xs">
                            {lga}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={clearLGAs}>
                      Clear
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Query Form */}
            <Card>
              <CardHeader>
                <CardTitle>Ask About Regulations</CardTitle>
                <CardDescription>
                  Enter your question about environmental or planning regulations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6 p-6">
                <div className="space-y-2">
                  <Textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        handleQuerySubmit();
                      }
                    }}
                    placeholder="e.g., Do I need an environmental impact assessment to build a solar farm in regional NSW?"
                    className="min-h-[140px] resize-none"
                  />
                  <p className="text-xs text-muted-foreground">Press Cmd/Ctrl + Enter to submit</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Region</label>
                    <Select
                      value={filters.region || 'all'}
                      onValueChange={(value) => setFilters({ region: value === 'all' ? undefined : value })}
                    >
                      <SelectTrigger>
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
                    <label className="text-sm font-medium">Jurisdiction</label>
                    <Select
                      value={filters.jurisdiction || 'all'}
                      onValueChange={(value) => setFilters({ jurisdiction: value === 'all' ? undefined : value })}
                    >
                      <SelectTrigger>
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
                    <label className="text-sm font-medium">Topics</label>
                    <Select
                      value={filters.topics?.[0] || 'all'}
                      onValueChange={(value) => setFilters({ topics: value === 'all' ? undefined : [value] })}
                    >
                      <SelectTrigger>
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

                <div className="flex gap-3 pt-2">
                  <Button onClick={handleQuerySubmit} disabled={isLoading} className="flex-1 h-11">
                    {isLoading ? 'Searching...' : 'Search'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setQuery('');
                      setFilters({});
                      setResults(null);
                      setQueryError(null);
                    }}
                    className="h-11"
                  >
                    Clear
                  </Button>
                </div>

                {queryError && (
                  <div className="text-sm text-destructive bg-destructive/10 p-4 rounded-md">
                    {queryError}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Loading */}
            {isLoading && (
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
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
                <Card>
                  <CardHeader>
                    <CardTitle>Answer</CardTitle>
                    {results.response_time_ms && (
                      <CardDescription>Response time: {results.response_time_ms.toFixed(0)}ms</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="p-6">
                    <p className="text-base leading-relaxed whitespace-pre-wrap">{results.answer}</p>
                  </CardContent>
                </Card>

                {results.sources && results.sources.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Sources ({results.sources.length})</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {results.sources.map((source: { title?: string; jurisdiction?: string; topic?: string; excerpt?: string; source_url?: string }, idx: number) => (
                          <div key={idx} className="border rounded-lg p-4 hover:bg-accent/50 transition-colors">
                            <h4 className="font-semibold text-base mb-2">{source.title}</h4>
                            <div className="flex flex-wrap gap-2 mb-3">
                              {source.jurisdiction && <Badge variant="secondary">{source.jurisdiction}</Badge>}
                              {source.topic && <Badge variant="secondary">{source.topic}</Badge>}
                            </div>
                            {source.excerpt && (
                              <p className="text-sm text-muted-foreground mb-3 line-clamp-3">{source.excerpt}</p>
                            )}
                            {source.source_url && (
                              <a
                                href={source.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-primary hover:underline"
                              >
                                View Source →
                              </a>
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
        <aside className="w-60 border-l bg-card overflow-y-auto flex-shrink-0">
          <div className="px-6 py-4 border-b bg-green-50">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-900">Information</h3>
              <Button variant="ghost" size="sm" onClick={() => setRightSidebarOpen(false)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <Tabs value={rightTab} onValueChange={setRightTab} className="w-full">
            <TabsList className="w-full grid grid-cols-2 rounded-none border-b mx-0">
              <TabsTrigger value="sources" className="rounded-none">
                <FileText className="h-4 w-4 mr-2" />
                Sources
              </TabsTrigger>
              <TabsTrigger value="analytics" className="rounded-none">
                <BarChart3 className="h-4 w-4 mr-2" />
                Analytics
              </TabsTrigger>
            </TabsList>

            <TabsContent value="analytics" className="px-6 py-4 space-y-4 mt-0">
              {analyticsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i}>
                      <CardHeader>
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
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs">Total Documents</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{stats.total_documents.toLocaleString()}</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs">Total Queries</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{stats.total_queries.toLocaleString()}</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs">Avg Response Time</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">
                        {stats.avg_response_time_ms ? `${stats.avg_response_time_ms.toFixed(0)}ms` : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>

                  {stats.documents_by_jurisdiction && stats.documents_by_jurisdiction.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">By Jurisdiction</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {(stats as { documents_by_jurisdiction?: Array<{ name: string; count: number }> })?.documents_by_jurisdiction?.map((item) => (
                            <div key={item.name} className="flex justify-between text-xs">
                              <span className="text-muted-foreground">{item.name}</span>
                              <span className="font-medium">{item.count}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ) : null}
            </TabsContent>

            <TabsContent value="sources" className="px-6 py-4 space-y-4 mt-0">
              <div className="space-y-2">
                <Select
                  value={(sourcesFilters.jurisdiction as string) || 'all'}
                  onValueChange={(value) =>
                    setSourcesFilters({ ...sourcesFilters, jurisdiction: value === 'all' ? undefined : value })
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
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
                  <SelectTrigger className="h-8 text-xs">
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
                    <Card key={i}>
                      <CardHeader className="pb-2">
                        <Skeleton className="h-4 w-full" />
                      </CardHeader>
                    </Card>
                  ))}
                </div>
              ) : documents ? (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    {(documents as { total: number })?.total} {(documents as { total: number })?.total === 1 ? 'document' : 'documents'}
                  </p>
                  {(documents as { documents: Array<{ id: string; title?: string; jurisdiction?: string; topic?: string; source_url?: string }> })?.documents?.slice(0, 10).map((doc) => (
                    <Card key={doc.id} className="hover:shadow-sm transition-shadow">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm leading-tight">{doc.title}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-1 mb-2">
                          {doc.jurisdiction && (
                            <Badge variant="secondary" className="text-xs">
                              {doc.jurisdiction}
                            </Badge>
                          )}
                          {doc.topic && (
                            <Badge variant="secondary" className="text-xs">
                              {doc.topic}
                            </Badge>
                          )}
                        </div>
                        {doc.source_url && (
                          <a
                            href={doc.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline"
                          >
                            View →
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
