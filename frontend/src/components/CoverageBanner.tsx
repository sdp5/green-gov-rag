import { AlertCircle, AlertTriangle, FileWarning, Info } from 'lucide-react';
import type { CoverageInfo } from '../types/api';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { Button } from './ui/button';

interface CoverageBannerProps {
  coverageInfo: CoverageInfo;
}

export function CoverageBanner({ coverageInfo }: CoverageBannerProps) {
  const {
    selected_lga,
    local_doc_count,
    coverage_level,
    contribution_url,
  } = coverageInfo;

  // Don't show banner for federal-only queries or high coverage
  if (coverage_level === 'federal_only' || coverage_level === 'high') {
    return null;
  }

  // Determine banner variant and icon based on coverage level
  const getBannerConfig = () => {
    switch (coverage_level) {
      case 'none':
        return {
          variant: 'destructive' as const,
          icon: AlertCircle,
          title: `No Local Documents for ${selected_lga || 'Selected LGA'}`,
          description: `We don't have local-specific documents for this LGA yet. Results will include federal and state regulations. Help us improve coverage by contributing!`,
          buttonText: 'Be the First to Contribute',
        };
      case 'low':
        return {
          variant: 'default' as const,
          icon: AlertTriangle,
          title: `Limited Coverage for ${selected_lga || 'Selected LGA'}`,
          description: `Only ${local_doc_count} local document${local_doc_count === 1 ? '' : 's'} available. Results may be incomplete. Help expand our coverage!`,
          buttonText: 'Contribute Documents',
        };
      case 'medium':
        return {
          variant: 'default' as const,
          icon: Info,
          title: `Partial Coverage for ${selected_lga || 'Selected LGA'}`,
          description: `${local_doc_count} local documents available. More documents would improve accuracy. Consider contributing!`,
          buttonText: 'Add More Documents',
        };
      default:
        return null;
    }
  };

  const config = getBannerConfig();
  if (!config) return null;

  const Icon = config.icon;

  return (
    <Alert variant={config.variant} className="mb-4">
      <Icon className="h-4 w-4" />
      <AlertTitle>{config.title}</AlertTitle>
      <AlertDescription className="mt-2">
        <p className="mb-3">{config.description}</p>
        <Button
          variant={coverage_level === 'none' ? 'default' : 'outline'}
          size="sm"
          asChild
        >
          <a
            href={contribution_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2"
          >
            <FileWarning className="h-4 w-4" />
            {config.buttonText}
          </a>
        </Button>
      </AlertDescription>
    </Alert>
  );
}
