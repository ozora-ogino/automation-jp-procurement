import React from 'react';
import { SearchParams } from '../types/bidding';

interface FiltersProps {
  filters: SearchParams;
  onFilterChange: (filters: SearchParams) => void;
}

const Filters: React.FC<FiltersProps> = ({ filters, onFilterChange }) => {
  const handleChange = (field: keyof SearchParams, value: any) => {
    // Toggle off if the same value is selected (for select elements)
    if (filters[field] === value && value !== '' && value !== undefined) {
      const newFilters = { ...filters };
      delete newFilters[field];
      onFilterChange(newFilters);
    } else {
      onFilterChange({ ...filters, [field]: value });
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">絞り込み</h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            機関
          </label>
          <input
            type="text"
            value={filters.organization || ''}
            onChange={(e) => handleChange('organization', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="機関名を入力"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            都道府県
          </label>
          <select
            value={filters.prefecture || ''}
            onChange={(e) => handleChange('prefecture', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">すべて</option>
            <option value="東京都">東京都</option>
            <option value="大阪府">大阪府</option>
            <option value="愛知県">愛知県</option>
            <option value="福岡県">福岡県</option>
            <option value="北海道">北海道</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            業種
          </label>
          <select
            value={filters.industry_type || ''}
            onChange={(e) => handleChange('industry_type', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">すべて</option>
            <option value="物品">物品</option>
            <option value="役務">役務</option>
            <option value="工事">工事</option>
            <option value="その他">その他</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            入札可否
          </label>
          <select
            value={filters.eligibility_filter || 'all'}
            onChange={(e) => {
              const value = e.target.value as 'all' | 'eligible' | 'ineligible';
              if (value === 'all') {
                const newFilters = { ...filters };
                delete newFilters.eligibility_filter;
                delete newFilters.eligible_only; // Remove legacy parameter
                onFilterChange(newFilters);
              } else {
                // Toggle off if same value is selected
                if (filters.eligibility_filter === value) {
                  const newFilters = { ...filters };
                  delete newFilters.eligibility_filter;
                  delete newFilters.eligible_only;
                  onFilterChange(newFilters);
                } else {
                  const newFilters = { ...filters };
                  delete newFilters.eligible_only; // Remove legacy parameter
                  newFilters.eligibility_filter = value;
                  onFilterChange(newFilters);
                }
              }
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">すべて</option>
            <option value="eligible">入札可能のみ</option>
            <option value="ineligible">入札不可能のみ</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            価格範囲
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={filters.price_min || ''}
              onChange={(e) => handleChange('price_min', e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="最小"
            />
            <span className="self-center">〜</span>
            <input
              type="number"
              value={filters.price_max || ''}
              onChange={(e) => handleChange('price_max', e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="最大"
            />
          </div>
        </div>

        <button
          onClick={() => onFilterChange({})}
          className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
        >
          フィルターをクリア
        </button>
      </div>
    </div>
  );
};

export default Filters;