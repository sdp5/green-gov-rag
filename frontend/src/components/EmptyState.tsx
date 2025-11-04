import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from './ui/button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  children?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  children,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-6 text-center ${className}`}>
      <div className="relative mb-6">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-200 to-green-200 rounded-full blur-2xl opacity-30 animate-pulse"></div>
        <div className="relative bg-gradient-to-br from-emerald-50 to-green-50 p-6 rounded-2xl border-2 border-emerald-200 shadow-lg">
          <Icon className="h-12 w-12 text-emerald-600" strokeWidth={1.5} />
        </div>
      </div>

      <h3 className="text-xl md:text-2xl font-bold text-slate-900 mb-3 tracking-tight">
        {title}
      </h3>

      <p className="text-sm md:text-base text-slate-600 max-w-md mb-6 leading-relaxed">
        {description}
      </p>

      {action && (
        <Button
          onClick={action.onClick}
          className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 shadow-md hover:shadow-lg transition-all"
        >
          {action.label}
        </Button>
      )}

      {children}
    </div>
  );
}