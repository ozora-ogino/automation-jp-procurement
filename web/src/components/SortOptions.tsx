import React, { useState } from 'react';
import { ArrowsUpDownIcon } from '@heroicons/react/24/outline';

export type SortOption = 'deadline' | 'price' | 'created' | 'organization';
export type SortDirection = 'asc' | 'desc';

interface SortOptionsProps {
  onSortChange: (sort: SortOption, direction: SortDirection) => void;
  currentSort?: SortOption;
  currentDirection?: SortDirection;
}

const SortOptions: React.FC<SortOptionsProps> = ({ 
  onSortChange, 
  currentSort = 'created',
  currentDirection = 'desc' 
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const sortOptions = [
    { value: 'deadline' as SortOption, label: '締切日' },
    { value: 'price' as SortOption, label: '予定価格' },
    { value: 'created' as SortOption, label: '登録日' },
    { value: 'organization' as SortOption, label: '機関名' },
  ];

  const handleSortChange = (option: SortOption) => {
    if (currentSort === option) {
      onSortChange(option, currentDirection === 'asc' ? 'desc' : 'asc');
    } else {
      onSortChange(option, 'desc');
    }
    setIsOpen(false);
  };

  const currentOption = sortOptions.find(opt => opt.value === currentSort);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <ArrowsUpDownIcon className="h-5 w-5 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">
          {currentOption?.label || '並び替え'}
        </span>
        <span className="text-xs text-gray-500">
          {currentDirection === 'asc' ? '↑' : '↓'}
        </span>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-30"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-40 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5">
            <div className="py-1">
              {sortOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleSortChange(option.value)}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${
                    currentSort === option.value ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  <span>{option.label}</span>
                  {currentSort === option.value && (
                    <span className="text-xs">
                      {currentDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SortOptions;