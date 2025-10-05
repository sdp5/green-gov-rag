/**
 * Shared constants for the GreenGovRAG application
 */

export const REGIONS = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'] as const;

export const JURISDICTIONS = ['Local', 'State', 'Federal'] as const;

export const TOPICS = [
  'Climate Action',
  'Energy',
  'Transport',
  'Waste',
  'Buildings',
  'Land Use',
  'Water',
  'Biodiversity',
] as const;

export const STATUS_OPTIONS = ['pending', 'processed', 'failed'] as const;

export type Region = typeof REGIONS[number];
export type Jurisdiction = typeof JURISDICTIONS[number];
export type Topic = typeof TOPICS[number];
export type DocumentStatus = typeof STATUS_OPTIONS[number];