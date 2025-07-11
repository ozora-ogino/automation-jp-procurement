import React from 'react';
import { SearchParams } from '../types/bidding';

interface QuickFiltersProps {
  onFilterApply: (filters: Partial<SearchParams>) => void;
  currentFilters: SearchParams;
}

interface PresetFilter {
  label: string;
  filters: Partial<SearchParams>;
  icon?: string;
}

const QuickFilters: React.FC<QuickFiltersProps> = ({ onFilterApply, currentFilters }) => {
  const presetFilters: PresetFilter[] = [
    {
      label: '入札可能のみ',
      filters: { eligibility_filter: 'eligible' },
      icon: '✅'
    },
    {
      label: '入札不可能のみ',
      filters: { eligibility_filter: 'ineligible' },
      icon: '❌'
    }
  ];

  const isFilterActive = (filter: Partial<SearchParams>): boolean => {
    return Object.entries(filter).every(([key, value]) => {
      return currentFilters[key as keyof SearchParams] === value;
    });
  };

  const handleFilterClick = (filter: Partial<SearchParams>) => {
    const newFilters = { ...currentFilters };
    
    if (isFilterActive(filter)) {
      // If filter is active, remove it
      Object.keys(filter).forEach(key => {
        delete newFilters[key as keyof SearchParams];
      });
      // Also remove legacy eligible_only parameter when toggling eligibility_filter
      if ('eligibility_filter' in filter) {
        delete newFilters.eligible_only;
      }
    } else {
      // Apply the filter
      Object.assign(newFilters, filter);
      // Remove legacy eligible_only parameter when setting eligibility_filter
      if ('eligibility_filter' in filter) {
        delete newFilters.eligible_only;
      }
    }
    
    // Pass the complete new filter state
    onFilterApply(newFilters);
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">クイックフィルター</h3>
      <div className="flex flex-wrap gap-2">
        {presetFilters.map((preset, index) => {
          const isActive = isFilterActive(preset.filters);
          return (
            <button
              key={index}
              onClick={() => handleFilterClick(preset.filters)}
              className={`
                inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-full
                transition-all duration-200 border
                ${isActive 
                  ? 'bg-blue-500 text-white border-blue-500 shadow-sm' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:border-gray-400'
                }
              `}
              title={`${preset.label}${isActive ? ' (クリックして解除)' : ''}`}
            >
              {preset.icon && <span className="text-base">{preset.icon}</span>}
              <span>{preset.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default QuickFilters;