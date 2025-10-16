import { useState, useEffect, useMemo } from 'react';
import { useQueryStore } from '@/store/queryStore';
import { useMapStore } from '@/store/mapStore';
import { queryAPI, documentsAPI, analyticsAPI, mapAPI } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  MapPin, ChevronLeft, ChevronRight, BarChart3, FileText, ChevronUp, ChevronDown,
  Shield, AlertTriangle, Scale, Building2, ExternalLink, BookOpen, Info, CheckCircle2,
  XCircle, AlertCircle, Sparkles, Clock, TrendingUp, Eye, EyeOff, Maximize2, Minimize2, Star
} from 'lucide-react';
import { REGIONS, JURISDICTIONS, TOPICS } from '@/commons/constants';
import Map, { Source, Layer, NavigationControl, type MapMouseEvent, type ViewStateChangeEvent } from 'react-map-gl/mapbox';
import type { FillLayer, LineLayer } from 'mapbox-gl';
import type { AnalyticsStats, DocumentListResponse } from '@/types/api';
import { MAPBOX_TOKEN } from '@/config/env';
import 'mapbox-gl/dist/mapbox-gl.css';

export default function PlaygroundPage() {
  // Sidebar state
  const [analyticsFooterOpen, setAnalyticsFooterOpen] = useState(false);
  const [rightTab, setRightTab] = useState('analytics');

  // Query state
  const { query, setQuery, filters, setFilters, results, isLoading, setResults, setLoading } = useQueryStore();
  const [queryError, setQueryError] = useState<string | null>(null);

  // Feedback state
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [feedbackLoading, setFeedbackLoading] = useState<boolean>(false);

  // UI state
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    trustScore: true,
    conflicts: true,
    hierarchy: true,
    warnings: true,
    sources: true,
  });
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

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

  // Toggle section expansion
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Load map data
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
    if (!geojson) {
      fetchLGAs();
    }
  }, [geojson]);

  // Load analytics data on initial page load
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
    // Always fetch on mount (page load/refresh)
    fetchStats();
  }, []); // Empty dependency array = runs only on mount

  // Refresh analytics when footer opens
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
    if (analyticsFooterOpen && rightTab === 'analytics') {
      fetchStats();
    }
  }, [analyticsFooterOpen, rightTab]);

  // Load documents
  useEffect(() => {
    const fetchDocuments = async () => {
      setSourcesLoading(true);
      try {
        const result = await documentsAPI.list({});
        setDocuments(result);
      } catch (err) {
        console.error('Failed to fetch documents:', err);
      } finally {
        setSourcesLoading(false);
      }
    };
    if (analyticsFooterOpen && rightTab === 'sources') {
      fetchDocuments();
    }
  }, [analyticsFooterOpen, rightTab]);

  // Query handlers
  const handleQuerySubmit = async () => {
    if (!query.trim()) {
      setQueryError('Please enter a query');
      return;
    }
    setQueryError(null);
    setLoading(true);
    // Reset feedback state on new query
    setFeedbackRating(0);
    setFeedbackSubmitted(false);
    try {
      const result = await queryAPI.execute(query, filters);
      setResults(result);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : 'Failed to execute query');
      setLoading(false);
    }
  };

  // Feedback handler - simplified for direct star click
  const handleFeedbackSubmit = async (rating: number) => {
    if (!results?.query_id || rating === 0) return;

    setFeedbackRating(rating);
    setFeedbackLoading(true);
    try {
      await queryAPI.submitFeedback(results.query_id, { rating });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setFeedbackLoading(false);
    }
  };

  // Load sample data for testing (toggle on/off)
  const loadSampleData = () => {
    // If demo data is already loaded, clear it
    if (query === 'What are my Scope 2 emissions reporting obligations for electricity consumption, and are there any conflicts between federal and state requirements?' && results) {
      setQuery('');
      setResults(null);
      setLoading(false);
      return;
    }

    // Otherwise, load demo data
    setQuery('What are my Scope 2 emissions reporting obligations for electricity consumption, and are there any conflicts between federal and state requirements?');
    setResults({
      answer: 'Under the National Greenhouse and Energy Reporting (NGER) Act, Scope 2 emissions relate to indirect emissions from the consumption of purchased electricity, steam, heat or cooling. Facilities must report Scope 2 emissions if they meet the threshold of 50 kilotonnes CO2-e per year or more.\n\nKey requirements include:\n• Accurate measurement and reporting of all purchased electricity\n• Use of approved emission factors from the National Greenhouse Accounts\n• Quarterly data collection and annual reporting by 31 October\n• Independent audit requirements for facilities over 125 kt CO2-e\n\nRegarding jurisdictional conflicts: The NGER Act (Federal) provides the primary framework. However, Victorian facilities must also comply with the Climate Change Act 2017 (Vic), which may impose additional requirements. Where both apply, the more stringent requirement takes precedence.',
      query: 'What are my Scope 2 emissions reporting obligations for electricity consumption, and are there any conflicts between federal and state requirements?',
      query_id: 999,  // Demo query ID for feedback
      sources: [
        {
          title: 'National Greenhouse and Energy Reporting Act 2007',
          source_url: 'https://www.legislation.gov.au/Details/C2023C00145',
          deep_link: 'https://www.legislation.gov.au/Details/C2023C00145#section-10',
          excerpt: 'A person has operational control over a facility if the person has the authority to introduce and implement operating, health and safety or environmental policies for the facility.',
          relevance_score: 0.94,
          jurisdiction: 'Federal',
          topic: 'Climate Change',
          region: 'National',
          page_number: 15,
          page_range: [15, 17],
          section_title: 'Scope 2 Emissions',
          section_hierarchy: ['Part 2', 'Division 2', 'Section 10', 'Subsection 10.2'],
          clause_reference: 's.10.2',
          citation: 'National Greenhouse and Energy Reporting Act 2007 (Cth) s.10.2, pp.15-17',
          esg_metadata: {
            frameworks: ['NGER', 'GHG Protocol'],
            emission_scopes: ['Scope 2'],
            greenhouse_gases: ['CO2', 'CH4', 'N2O'],
            regulator: 'Clean Energy Regulator',
            reportable_under_nger: true
          }
        },
        {
          title: 'National Greenhouse and Energy Reporting Regulations 2008',
          source_url: 'https://www.legislation.gov.au/Details/F2023C00456',
          excerpt: 'For the purposes of calculating Scope 2 emissions, the entity must use the emission factors published in the National Greenhouse Accounts (NGA) Factors.',
          relevance_score: 0.89,
          jurisdiction: 'Federal',
          topic: 'Climate Change',
          page_number: 42,
          page_range: [42, 42],
          section_title: 'Emission Factors',
          section_hierarchy: ['Part 3', 'Regulation 15'],
          clause_reference: 'reg.15',
          citation: 'National Greenhouse and Energy Reporting Regulations 2008 (Cth) reg.15, p.42',
          esg_metadata: {
            frameworks: ['NGER'],
            emission_scopes: ['Scope 2'],
            regulator: 'Clean Energy Regulator'
          }
        },
        {
          title: 'NGER Measurement Determination 2008',
          source_url: 'https://www.legislation.gov.au/Details/F2023C00789',
          excerpt: 'Electricity consumption must be measured at the point of delivery to the facility using appropriate metering equipment that complies with National Measurement Institute standards.',
          relevance_score: 0.87,
          jurisdiction: 'Federal',
          topic: 'Climate Change',
          page_number: 28,
          section_hierarchy: ['Part 2', 'Section 2.3'],
          clause_reference: 's.2.3',
          esg_metadata: {
            frameworks: ['NGER'],
            emission_scopes: ['Scope 2']
          }
        }
      ],
      filters_applied: { jurisdiction: 'Federal', topics: ['Climate Change'] },
      response_time_ms: 1847,
      trust_score: 0.87,
      trust_confidence: 'high',
      trust_breakdown: {
        citation_score: 0.92,
        authority_score: 0.95,
        conflict_score: 0.88,
        accuracy_score: 0.85,
        warnings: [
          'Some emission factor values may be updated annually',
          'State-based schemes may have additional requirements'
        ]
      },
      conflicts_detected: [
        {
          type: 'Jurisdictional Overlap',
          severity: 'warning',
          details: 'Victorian Climate Change Act 2017 may impose additional reporting requirements beyond NGER for facilities in Victoria.',
          resolution: 'Facilities in Victoria must comply with both NGER (Federal) and Victorian Climate Change Act requirements. The more stringent requirement applies.'
        }
      ],
      hierarchy_explanation: 'Federal legislation (NGER Act) takes precedence as the primary framework, with State/Territory laws providing complementary requirements. Where conflicts exist, the more stringent obligation typically applies.',
      citation_warnings: [
        'Page ranges are approximate based on document structure',
        'Always verify with the latest consolidated version of legislation'
      ]
    });
    setLoading(false);
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
          // ignore
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
          // ignore
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
    const panAmount = 0.5;
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
      'fill-color': ['case', ['==', ['get', 'selected'], true], '#10b981', '#e5e7eb'],
      'fill-opacity': ['case', ['==', ['get', 'selected'], true], 0.4, 0.15],
    },
  };

  const lineLayerStyle: LineLayer = {
    id: 'lga-lines',
    type: 'line',
    paint: { 'line-color': '#9ca3af', 'line-width': 1 },
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gradient-to-br from-slate-50 via-green-50/30 to-emerald-50/20">
      {/* Analytics Strip */}
      <div className="bg-white border-b-2 border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
            <div className="flex flex-wrap items-center gap-3 sm:gap-6 text-slate-700 w-full sm:w-auto">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAnalyticsFooterOpen(!analyticsFooterOpen)}
                className="hover:bg-slate-100 gap-2 font-semibold"
              >
                <BarChart3 className="h-4 w-4 text-emerald-600" />
                <span>Data Explorer</span>
                {analyticsFooterOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              {stats && !analyticsFooterOpen && (
                <>
                  <div className="hidden sm:block h-6 w-px bg-slate-300"></div>
                  <div className="flex items-center gap-2 text-sm sm:text-base">
                    <FileText className="h-3 w-3 sm:h-4 sm:w-4 text-emerald-600" />
                    <span className="font-bold text-slate-900">{stats.total_documents.toLocaleString()}</span>
                    <span className="text-xs text-slate-500 hidden sm:inline">documents</span>
                    <span className="text-xs text-slate-500 sm:hidden">docs</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm sm:text-base">
                    <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4 text-purple-600" />
                    <span className="font-bold text-slate-900">{stats.total_queries.toLocaleString()}</span>
                    <span className="text-xs text-slate-500 hidden sm:inline">queries</span>
                    <span className="text-xs text-slate-500 sm:hidden">qry</span>
                  </div>
                  {stats.avg_response_time_ms !== undefined && stats.avg_response_time_ms !== null && (
                    <div className="flex items-center gap-2 text-sm sm:text-base">
                      <Clock className="h-3 w-3 sm:h-4 sm:w-4 text-amber-600" />
                      <span className="font-bold text-slate-900">{stats.avg_response_time_ms.toFixed(0)}</span>
                      <span className="text-xs text-slate-500">ms</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Expanded Analytics */}
          {analyticsFooterOpen && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <Tabs value={rightTab} onValueChange={setRightTab} className="w-full">
                <TabsList className="bg-slate-100 mb-4">
                  <TabsTrigger value="analytics" className="data-[state=active]:bg-white data-[state=active]:text-emerald-700 data-[state=active]:shadow-sm">
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Analytics
                  </TabsTrigger>
                  <TabsTrigger value="sources" className="data-[state=active]:bg-white data-[state=active]:text-emerald-700 data-[state=active]:shadow-sm">
                    <FileText className="h-4 w-4 mr-2" />
                    Browse Sources
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="analytics" className="mt-0">
                  {analyticsLoading ? (
                    <div className="grid grid-cols-4 gap-4">
                      {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="bg-slate-100 rounded-lg p-4 animate-pulse">
                          <div className="h-4 bg-slate-200 rounded mb-2"></div>
                          <div className="h-8 bg-slate-200 rounded"></div>
                        </div>
                      ))}
                    </div>
                  ) : stats ? (
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                      <div className="bg-gradient-to-br from-emerald-50 to-green-50 border-2 border-emerald-200 rounded-lg p-4">
                        <p className="text-xs font-bold uppercase mb-1 text-emerald-700">Total Documents</p>
                        <p className="text-3xl font-extrabold text-emerald-900">{stats.total_documents.toLocaleString()}</p>
                      </div>
                      <div className="bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-200 rounded-lg p-4">
                        <p className="text-xs font-bold uppercase mb-1 text-purple-700">Total Queries</p>
                        <p className="text-3xl font-extrabold text-purple-900">{stats.total_queries.toLocaleString()}</p>
                      </div>
                      <div className="bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-200 rounded-lg p-4">
                        <p className="text-xs font-bold uppercase mb-1 text-amber-700">Avg Response</p>
                        <p className="text-3xl font-extrabold text-amber-900">
                          {stats.avg_response_time_ms !== undefined && stats.avg_response_time_ms !== null
                            ? `${stats.avg_response_time_ms.toFixed(0)}ms`
                            : 'N/A'}
                        </p>
                      </div>
                      <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-lg p-4">
                        <p className="text-xs font-bold uppercase mb-1 text-blue-700">Jurisdictions</p>
                        <p className="text-3xl font-extrabold text-blue-900">{stats.documents_by_jurisdiction?.length || 0}</p>
                      </div>
                    </div>
                  ) : null}
                </TabsContent>

                <TabsContent value="sources" className="mt-0">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 max-h-60 overflow-y-auto">
                    {sourcesLoading ? (
                      <p className="text-center text-slate-600">Loading sources...</p>
                    ) : documents && documents.documents && documents.documents.length > 0 ? (
                      <div className="space-y-2">
                        {documents.documents.slice(0, 5).map((doc) => (
                          <div key={doc.id} className="bg-white border border-slate-200 rounded-lg p-3 hover:border-emerald-300 hover:shadow-sm transition-all">
                            <p className="font-semibold text-sm text-slate-900">{doc.title}</p>
                            <div className="flex gap-2 mt-2">
                              {doc.jurisdiction && (
                                <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800 border-blue-200">{doc.jurisdiction}</Badge>
                              )}
                              {doc.topic && (
                                <Badge variant="outline" className="text-xs">{doc.topic}</Badge>
                              )}
                            </div>
                          </div>
                        ))}
                        <p className="text-xs text-slate-500 text-center pt-2">
                          Showing {Math.min(5, documents.documents.length)} of {documents.total} documents
                        </p>
                      </div>
                    ) : (
                      <p className="text-center text-slate-500 py-4">No documents available</p>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </div>

      {/* Main Content: Dual Pane */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Panel - Map (hidden on mobile, visible on lg+) */}
        <aside className="hidden lg:block lg:w-[40%] lg:max-w-[650px] lg:min-w-[450px] border-b lg:border-b-0 lg:border-r-2 border-slate-200 bg-slate-50 overflow-y-auto flex-shrink-0">
          <div className="sticky top-0 z-10 px-5 py-4 border-b-2 border-slate-200 bg-white shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <MapPin className="h-5 w-5 text-emerald-700" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-slate-900">Geographic Scope</h3>
                <p className="text-xs text-slate-600">Select regions to filter regulations</p>
              </div>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {/* Selected LGAs */}
            <Card className="border-2 border-emerald-200 bg-gradient-to-br from-emerald-50 to-white shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    Selected Regions
                    <Badge variant="secondary" className="ml-1">{selectedLGAs.length}</Badge>
                  </CardTitle>
                  {selectedLGAs.length > 0 && (
                    <Button variant="ghost" size="sm" onClick={clearLGAs} className="h-7 text-xs hover:bg-red-100 hover:text-red-700">
                      Clear All
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {selectedLGAs.length === 0 ? (
                  <div className="text-center py-4 text-sm text-muted-foreground">
                    <MapPin className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    Click regions on map to filter
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {selectedLGAs.map((lga) => (
                      <Badge
                        key={lga}
                        variant="secondary"
                        className="cursor-pointer hover:bg-red-100 hover:text-red-700 transition-colors px-3 py-1.5 bg-emerald-100 text-emerald-800 border border-emerald-200"
                        onClick={() => removeLGA(lga)}
                      >
                        {lga}
                        <XCircle className="ml-1.5 h-3 w-3" />
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Map */}
            {MAPBOX_TOKEN ? (
              <div className="border-2 border-slate-200 rounded-xl overflow-hidden shadow-lg bg-white">
                {mapLoading ? (
                  <div className="h-[500px] flex items-center justify-center bg-slate-50">
                    <div className="text-center space-y-3">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto"></div>
                      <p className="text-sm text-muted-foreground">Loading map data...</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-[500px] relative">
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
                    {hoveredLGA && (
                      <div className="absolute top-3 left-3 bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg shadow-xl border border-slate-200 text-sm font-semibold text-slate-900">
                        {hoveredLGA}
                      </div>
                    )}
                    {/* Navigation Controls */}
                    <div className="absolute bottom-3 left-3 flex flex-col gap-1 bg-white/95 backdrop-blur-sm p-1.5 rounded-lg shadow-lg border border-slate-200">
                      <Button size="sm" variant="secondary" className="h-8 w-8 p-0" onClick={() => panMap('up')}>
                        <ChevronUp className="h-4 w-4" />
                      </Button>
                      <div className="flex gap-1">
                        <Button size="sm" variant="secondary" className="h-8 w-8 p-0" onClick={() => panMap('left')}>
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="secondary" className="h-8 w-8 p-0" onClick={() => panMap('right')}>
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                      <Button size="sm" variant="secondary" className="h-8 w-8 p-0" onClick={() => panMap('down')}>
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Card className="border-2">
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground text-center">Map requires VITE_MAPBOX_TOKEN</p>
                </CardContent>
              </Card>
            )}
          </div>
        </aside>

        {/* Right Panel - Search & Results */}
        <main className="flex-1 overflow-y-auto bg-white">
          <div className="max-w-6xl mx-auto py-4 sm:py-6 lg:py-8 px-4 sm:px-6 space-y-4 sm:space-y-6">
            {/* LGA Filter Indicator */}
            {selectedLGAs.length > 0 && (
            <Card className="border-2 border-emerald-300 bg-gradient-to-r from-emerald-50 via-green-50 to-emerald-50 shadow-md">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 bg-emerald-100 rounded-lg">
                        <MapPin className="h-5 w-5 text-emerald-700" />
                      </div>
                      <p className="text-base font-bold text-emerald-900">
                        Filtering by {selectedLGAs.length} Region{selectedLGAs.length > 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 ml-14">
                      {selectedLGAs.map((lga) => (
                        <Badge key={lga} variant="secondary" className="text-xs font-semibold bg-white/80 border border-emerald-200">
                          {lga}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={clearLGAs} className="hover:bg-white/60 font-semibold">
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Query Form */}
          <Card className="border-2 border-slate-200 shadow-xl bg-white/90 backdrop-blur-sm">
            <CardHeader className="pb-3 sm:pb-4 bg-gradient-to-r from-slate-50 to-white border-b">
              <CardTitle className="text-base sm:text-lg lg:text-xl flex items-center gap-2">
                <BookOpen className="h-4 w-4 sm:h-5 sm:w-5 text-slate-700" />
                <span className="leading-tight">Ask questions, explore documents, and discover what applies to your location.</span>
              </CardTitle>
              <CardDescription className="text-sm sm:text-base">
                Navigate Australian environmental and planning regulations with AI-powered insights.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 sm:pt-6 space-y-4 sm:space-y-5">
              <div className="space-y-3">
                <Textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      handleQuerySubmit();
                    }
                  }}
                  placeholder="e.g., What are the Scope 2 reporting requirements under NGER for electricity consumption?"
                  className="min-h-[100px] sm:min-h-[120px] resize-none text-sm sm:text-base border-2 focus:border-emerald-400"
                />
                <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
                  <Info className="h-3 w-3" />
                  <span>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border">⌘</kbd> + <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border">Enter</kbd> to submit</span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    Region
                  </label>
                  <Select
                    value={filters.region || 'all'}
                    onValueChange={(value) => setFilters({ region: value === 'all' ? undefined : value })}
                  >
                    <SelectTrigger className="h-10 border-2 focus:border-emerald-400">
                      <SelectValue placeholder="All regions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All regions</SelectItem>
                      {REGIONS.map((region) => (
                        <SelectItem key={region} value={region}>{region}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                    <Building2 className="h-3.5 w-3.5" />
                    Jurisdiction
                  </label>
                  <Select
                    value={filters.jurisdiction || 'all'}
                    onValueChange={(value) => setFilters({ jurisdiction: value === 'all' ? undefined : value })}
                  >
                    <SelectTrigger className="h-10 border-2 focus:border-emerald-400">
                      <SelectValue placeholder="All jurisdictions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All jurisdictions</SelectItem>
                      {JURISDICTIONS.map((jurisdiction) => (
                        <SelectItem key={jurisdiction} value={jurisdiction}>{jurisdiction}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5" />
                    Topics
                  </label>
                  <Select
                    value={filters.topics?.[0] || 'all'}
                    onValueChange={(value) => setFilters({ topics: value === 'all' ? undefined : [value] })}
                  >
                    <SelectTrigger className="h-10 border-2 focus:border-emerald-400">
                      <SelectValue placeholder="All topics" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All topics</SelectItem>
                      {TOPICS.map((topic) => (
                        <SelectItem key={topic} value={topic}>{topic}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2">
                <Button
                  onClick={handleQuerySubmit}
                  disabled={isLoading}
                  className="flex-1 h-11 sm:h-12 text-sm sm:text-base font-bold bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 shadow-lg"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span className="hidden sm:inline">Analyzing...</span>
                      <span className="sm:hidden">Analyzing...</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      <span className="hidden sm:inline">Search Regulations</span>
                      <span className="sm:hidden">Search</span>
                    </span>
                  )}
                </Button>
                <div className="flex gap-2 sm:gap-3">
                  <Button
                    variant="secondary"
                    onClick={loadSampleData}
                    className="flex-1 sm:flex-none h-11 sm:h-12 px-4 sm:px-6 border-2 text-sm sm:text-base"
                    title="Load sample data to preview UI"
                  >
                    Demo
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setQuery('');
                      setFilters({});
                      setResults(null);
                      setQueryError(null);
                      setLoading(false);
                    }}
                    className="flex-1 sm:flex-none h-11 sm:h-12 px-4 sm:px-6 border-2 text-sm sm:text-base"
                    disabled={isLoading}
                  >
                    Clear
                  </Button>
                </div>
              </div>

              {queryError && (
                <div className="flex items-start gap-3 text-sm text-red-700 bg-red-50 p-4 rounded-lg border-2 border-red-200">
                  <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold">Error:</strong> {queryError}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Loading State */}
          {isLoading && (
            <Card className="border-2 border-slate-200 shadow-lg">
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <div className="relative">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-emerald-600"></div>
                    <Sparkles className="h-6 w-6 text-emerald-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-lg font-semibold text-slate-700">Analyzing regulations...</p>
                    <p className="text-sm text-muted-foreground">Searching databases, verifying citations, detecting conflicts</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Section */}
          {!isLoading && results && (
            <div className="space-y-5">
              {/* 1. Answer - Most Important */}
              <Card className="border-2 border-sky-200 bg-gradient-to-br from-sky-50 via-blue-50 to-white shadow-xl">
                <CardHeader className="pb-4 bg-gradient-to-r from-sky-50/50 to-transparent border-b-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-2xl flex items-center gap-3">
                      <div className="p-2 bg-sky-100 rounded-lg">
                        <Sparkles className="h-6 w-6 text-sky-600" />
                      </div>
                      Answer
                    </CardTitle>
                    {results.response_time_ms && (
                      <Badge variant="outline" className="flex items-center gap-1 font-mono">
                        <Clock className="h-3 w-3" />
                        {results.response_time_ms.toFixed(0)}ms
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
                  <div className="prose prose-slate max-w-none">
                    <p className="text-base leading-relaxed whitespace-pre-wrap text-slate-800">{results.answer}</p>
                  </div>

                  {/* Integrated Feedback */}
                  {results.query_id && (
                    <div className="pt-4 border-t border-sky-200">
                      {!feedbackSubmitted ? (
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-slate-600">Rate this answer:</span>
                          <div className="flex gap-1">
                            {[1, 2, 3, 4, 5].map((rating) => (
                              <button
                                key={rating}
                                onClick={() => handleFeedbackSubmit(rating)}
                                disabled={feedbackLoading}
                                className={`transition-all hover:scale-110 ${
                                  rating <= feedbackRating
                                    ? 'text-yellow-500'
                                    : 'text-slate-300 hover:text-yellow-400'
                                } ${feedbackLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                              >
                                <Star className={`h-6 w-6 ${rating <= feedbackRating ? 'fill-current' : ''}`} />
                              </button>
                            ))}
                          </div>
                          {feedbackLoading && (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-sky-600"></div>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-sky-700">
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                          <span className="text-sm font-medium">Thanks!</span>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 2. Trust Score - Credibility Check */}
              {results.trust_score !== undefined && (
                <Card className="border-2 border-emerald-300 bg-gradient-to-br from-emerald-50 via-green-50 to-white shadow-lg transition-all hover:shadow-xl">
                  <CardHeader className="pb-3 cursor-pointer" onClick={() => toggleSection('trustScore')}>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xl flex items-center gap-3">
                        <div className="p-2 bg-emerald-100 rounded-lg">
                          <Shield className="h-6 w-6 text-emerald-600" />
                        </div>
                        <span>Trust Score</span>
                        <Badge className={`${
                          results.trust_confidence === 'high' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                          results.trust_confidence === 'medium' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                          'bg-red-100 text-red-800 border-red-300'
                        } text-xs font-bold px-3 py-1 border`}>
                          {results.trust_confidence?.toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="ml-auto font-mono font-bold text-lg border-emerald-300">
                          {(results.trust_score * 100).toFixed(0)}%
                        </Badge>
                      </CardTitle>
                      <Button variant="ghost" size="sm" className="p-1">
                        {expandedSections.trustScore ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                      </Button>
                    </div>
                  </CardHeader>
                  {expandedSections.trustScore && (
                    <CardContent className="space-y-4">
                      <div className="relative">
                        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner">
                          <div
                            className={`h-4 rounded-full transition-all duration-700 ${
                              results.trust_confidence === 'high' ? 'bg-gradient-to-r from-emerald-500 to-green-500' :
                              results.trust_confidence === 'medium' ? 'bg-gradient-to-r from-amber-400 to-yellow-500' :
                              'bg-gradient-to-r from-red-400 to-rose-500'
                            }`}
                            style={{ width: `${results.trust_score * 100}%` }}
                          />
                        </div>
                      </div>
                      {results.trust_breakdown && (
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t">
                          <div className="text-center p-4 bg-white/60 rounded-lg border-2 border-blue-100">
                            <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Citation</p>
                            <p className="text-2xl font-bold text-blue-900">{(results.trust_breakdown.citation_score * 100).toFixed(0)}%</p>
                          </div>
                          <div className="text-center p-4 bg-white/60 rounded-lg border-2 border-purple-100">
                            <p className="text-xs font-semibold text-purple-600 uppercase mb-1">Authority</p>
                            <p className="text-2xl font-bold text-purple-900">{(results.trust_breakdown.authority_score * 100).toFixed(0)}%</p>
                          </div>
                          <div className="text-center p-4 bg-white/60 rounded-lg border-2 border-orange-100">
                            <p className="text-xs font-semibold text-orange-600 uppercase mb-1">Conflicts</p>
                            <p className="text-2xl font-bold text-orange-900">{(results.trust_breakdown.conflict_score * 100).toFixed(0)}%</p>
                          </div>
                          <div className="text-center p-4 bg-white/60 rounded-lg border-2 border-green-100">
                            <p className="text-xs font-semibold text-green-600 uppercase mb-1">Accuracy</p>
                            <p className="text-2xl font-bold text-green-900">{(results.trust_breakdown.accuracy_score * 100).toFixed(0)}%</p>
                          </div>
                        </div>
                      )}
                      {results.trust_breakdown?.warnings && results.trust_breakdown.warnings.length > 0 && (
                        <div className="space-y-2 pt-2">
                          <p className="text-sm font-semibold text-slate-700">Considerations:</p>
                          {results.trust_breakdown.warnings.map((warning, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm text-slate-600 bg-white/60 p-3 rounded-lg border">
                              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-600" />
                              <span>{warning}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              )}

              {/* 3. Citation Warnings - Important Caveats */}
              {results.citation_warnings && results.citation_warnings.length > 0 && (
                <Card className="border-2 border-amber-300 bg-gradient-to-br from-amber-50 to-yellow-50 shadow-lg">
                  <CardHeader className="pb-3 cursor-pointer" onClick={() => toggleSection('warnings')}>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-3">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                        Citation Warnings
                        <Badge variant="outline" className="bg-amber-100 border-amber-300">{results.citation_warnings.length}</Badge>
                      </CardTitle>
                      <Button variant="ghost" size="sm" className="p-1">
                        {expandedSections.warnings ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </CardHeader>
                  {expandedSections.warnings && (
                    <CardContent>
                      <ul className="space-y-2">
                        {results.citation_warnings.map((warning, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-sm bg-white/60 p-3 rounded-lg border border-amber-200">
                            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-700" />
                            <span className="text-amber-900">{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  )}
                </Card>
              )}

              {/* 4. Regulatory Conflicts */}
              {results.conflicts_detected && results.conflicts_detected.length > 0 && (
                <Card className="border-2 border-orange-300 bg-gradient-to-br from-orange-50 to-red-50 shadow-lg">
                  <CardHeader className="pb-3 cursor-pointer" onClick={() => toggleSection('conflicts')}>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-3">
                        <Scale className="h-5 w-5 text-orange-600" />
                        Regulatory Conflicts
                        <Badge variant="outline" className="bg-orange-100 border-orange-300">{results.conflicts_detected.length}</Badge>
                      </CardTitle>
                      <Button variant="ghost" size="sm" className="p-1">
                        {expandedSections.conflicts ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </CardHeader>
                  {expandedSections.conflicts && (
                    <CardContent>
                      <div className="space-y-3">
                        {results.conflicts_detected.map((conflict, idx) => (
                          <div key={idx} className="bg-white/80 rounded-lg p-4 border-l-4 border-orange-500">
                            <div className="flex items-start gap-3 mb-2">
                              <Badge
                                variant={conflict.severity === 'critical' ? 'destructive' : conflict.severity === 'warning' ? 'secondary' : 'outline'}
                                className="text-xs font-bold"
                              >
                                {conflict.severity.toUpperCase()}
                              </Badge>
                              <span className="font-bold text-orange-900">{conflict.type}</span>
                            </div>
                            <p className="text-sm text-slate-600 mb-3">{conflict.details}</p>
                            <div className="bg-orange-100/50 p-3 rounded border border-orange-200">
                              <p className="text-xs font-semibold text-orange-900 mb-1">RESOLUTION:</p>
                              <p className="text-sm text-orange-800">{conflict.resolution}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  )}
                </Card>
              )}

              {/* 5. Source Documents - Evidence/References */}
              {results.sources && results.sources.length > 0 && (
                <Card className="border-2 border-slate-300 shadow-xl bg-white">
                  <CardHeader className="pb-4 border-b-2 bg-gradient-to-r from-slate-50 to-white cursor-pointer" onClick={() => toggleSection('sources')}>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xl flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="h-5 w-5 text-blue-600" />
                        </div>
                        Source Documents
                        <Badge variant="outline" className="bg-blue-50 border-blue-200">{results.sources.length}</Badge>
                      </CardTitle>
                      <Button variant="ghost" size="sm" className="p-1">
                        {expandedSections.sources ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                    <CardDescription className="text-base">
                      Referenced regulations and guidelines
                    </CardDescription>
                  </CardHeader>
                  {expandedSections.sources && (
                    <CardContent className="pt-6">
                      <div className="space-y-4">
                        {results.sources.map((source, idx) => (
                          <Card
                            key={idx}
                            className={`border-2 transition-all ${
                              expandedSource === idx ? 'border-emerald-400 shadow-lg' : 'border-slate-200 hover:border-emerald-300 hover:shadow-md'
                            }`}
                          >
                            <CardHeader
                              className="pb-3 cursor-pointer bg-gradient-to-r from-slate-50 to-white"
                              onClick={() => setExpandedSource(expandedSource === idx ? null : idx)}
                            >
                              <div className="flex items-start gap-4">
                                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center text-white font-bold text-lg shadow-md">
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-bold text-base mb-2 leading-tight text-slate-900">{source.title}</h4>

                                  {/* Citation */}
                                  {source.citation && (
                                    <div className="mb-3 bg-slate-100 px-3 py-2 rounded-md border border-slate-200">
                                      <p className="text-xs font-mono text-slate-700">{source.citation}</p>
                                    </div>
                                  )}

                                  {/* Badges */}
                                  <div className="flex flex-wrap gap-2">
                                    {source.jurisdiction && (
                                      <Badge variant="secondary" className="text-xs font-semibold bg-blue-100 text-blue-800 border-blue-200">
                                        <Building2 className="h-3 w-3 mr-1" />
                                        {source.jurisdiction}
                                      </Badge>
                                    )}
                                    {source.topic && (
                                      <Badge variant="outline" className="text-xs font-semibold">
                                        {source.topic}
                                      </Badge>
                                    )}
                                    {source.page_number && (
                                      <Badge variant="outline" className="text-xs font-semibold">
                                        Page {source.page_number}
                                      </Badge>
                                    )}
                                    {source.relevance_score && (
                                      <Badge variant="outline" className="text-xs font-mono font-bold text-emerald-700">
                                        {(source.relevance_score * 100).toFixed(0)}% match
                                      </Badge>
                                    )}
                                    <Button variant="ghost" size="sm" className="ml-auto p-1">
                                      {expandedSource === idx ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </CardHeader>

                            {expandedSource === idx && (
                              <CardContent className="pt-4 space-y-4 border-t-2">
                                {/* Section Hierarchy */}
                                {source.section_hierarchy && source.section_hierarchy.length > 0 && (
                                  <div>
                                    <p className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                                      <TrendingUp className="h-3 w-3" />
                                      Document Structure:
                                    </p>
                                    <div className="flex items-center gap-2 text-sm text-slate-700 bg-slate-50 p-3 rounded-lg border">
                                      {source.section_hierarchy.map((section, i) => (
                                        <span key={i} className="flex items-center gap-2">
                                          {i > 0 && <ChevronRight className="h-3 w-3 text-slate-400" />}
                                          <span className="font-medium">{section}</span>
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* ESG Metadata */}
                                {source.esg_metadata && (
                                  <div>
                                    <p className="text-xs font-semibold text-slate-600 mb-2">ESG Classifications:</p>
                                    <div className="flex flex-wrap gap-2">
                                      {source.esg_metadata.frameworks?.map((fw) => (
                                        <Badge key={fw} variant="secondary" className="text-xs bg-emerald-100 text-emerald-800 border-emerald-200">
                                          {fw}
                                        </Badge>
                                      ))}
                                      {source.esg_metadata.emission_scopes?.map((scope) => (
                                        <Badge key={scope} variant="outline" className="text-xs">
                                          {scope}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Excerpt */}
                                {source.excerpt && (
                                  <div className="bg-slate-50 border-l-4 border-emerald-500 p-4 rounded-r-lg">
                                    <p className="text-sm text-slate-700 italic leading-relaxed">"{source.excerpt}"</p>
                                  </div>
                                )}

                                {/* Links */}
                                <div className="flex gap-3 pt-2">
                                  {source.deep_link && (
                                    <Button variant="default" size="sm" className="flex-1 bg-emerald-600 hover:bg-emerald-700" asChild>
                                      <a href={source.deep_link} target="_blank" rel="noopener noreferrer">
                                        <ExternalLink className="h-4 w-4 mr-2" />
                                        View Section
                                      </a>
                                    </Button>
                                  )}
                                  {source.source_url && !source.deep_link && (
                                    <Button variant="outline" size="sm" className="flex-1" asChild>
                                      <a href={source.source_url} target="_blank" rel="noopener noreferrer">
                                        <ExternalLink className="h-4 w-4 mr-2" />
                                        View Document
                                      </a>
                                    </Button>
                                  )}
                                </div>
                              </CardContent>
                            )}
                          </Card>
                        ))}
                      </div>
                    </CardContent>
                  )}
                </Card>
              )}

              {/* 6. Regulatory Hierarchy - Context */}
              {results.hierarchy_explanation && (
                <Card className="border-2 border-purple-300 bg-gradient-to-br from-purple-50 to-indigo-50 shadow-lg">
                  <CardHeader className="pb-3 cursor-pointer" onClick={() => toggleSection('hierarchy')}>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-3">
                        <TrendingUp className="h-5 w-5 text-purple-600" />
                        Regulatory Hierarchy
                      </CardTitle>
                      <Button variant="ghost" size="sm" className="p-1">
                        {expandedSections.hierarchy ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                    <CardDescription className="flex items-center gap-2 text-purple-700">
                      <span className="font-semibold">Federal</span>
                      <ChevronRight className="h-3 w-3" />
                      <span className="font-semibold">State</span>
                      <ChevronRight className="h-3 w-3" />
                      <span className="font-semibold">Local</span>
                    </CardDescription>
                  </CardHeader>
                  {expandedSections.hierarchy && (
                    <CardContent>
                      <div className="bg-white/70 p-4 rounded-lg border-2 border-purple-200 font-mono text-sm whitespace-pre-line text-purple-900 leading-relaxed">
                        {results.hierarchy_explanation}
                      </div>
                    </CardContent>
                  )}
                </Card>
              )}
            </div>
          )}
        </div>
      </main>
      </div>
    </div>
  );
}
