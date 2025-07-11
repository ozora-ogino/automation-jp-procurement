import React, { useState } from 'react';
import { SearchParams } from '../types/bidding';
import { 
  FunnelIcon, 
  XMarkIcon,
  CalendarIcon,
  CurrencyYenIcon,
  BuildingOfficeIcon,
  MapPinIcon,
  TagIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

interface AdvancedFiltersProps {
  filters: SearchParams;
  onFilterChange: (filters: SearchParams) => void;
}

const AdvancedFilters: React.FC<AdvancedFiltersProps> = ({ filters, onFilterChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleChange = (field: keyof SearchParams, value: any) => {
    if (filters[field] === value && value !== '' && value !== undefined) {
      const newFilters = { ...filters };
      delete newFilters[field];
      onFilterChange(newFilters);
    } else {
      onFilterChange({ ...filters, [field]: value });
    }
  };

  const activeFilterCount = Object.keys(filters).filter(
    key => key !== 'page' && key !== 'limit' && filters[key as keyof SearchParams] !== undefined
  ).length;

  const clearAllFilters = () => {
    onFilterChange({ page: filters.page, limit: filters.limit });
  };

  const prefectures = [
    '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
    '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
    '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
    '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
    '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
          activeFilterCount > 0
            ? 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
        }`}
      >
        <FunnelIcon className="h-5 w-5" />
        <span className="font-medium">詳細フィルター</span>
        {activeFilterCount > 0 && (
          <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-blue-600 rounded-full">
            {activeFilterCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 bg-black bg-opacity-25 z-40 lg:hidden"
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute top-12 left-0 z-50 w-full max-w-md bg-white rounded-lg shadow-xl border border-gray-200 p-6 
                          lg:w-96">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-gray-900">詳細フィルター</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="space-y-6 max-h-[60vh] overflow-y-auto">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <BuildingOfficeIcon className="h-4 w-4" />
                  機関名
                </label>
                <input
                  type="text"
                  value={filters.organization || ''}
                  onChange={(e) => handleChange('organization', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="例: 東京都"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <MapPinIcon className="h-4 w-4" />
                  都道府県
                </label>
                <select
                  value={filters.prefecture || ''}
                  onChange={(e) => handleChange('prefecture', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">すべて</option>
                  {prefectures.map(pref => (
                    <option key={pref} value={pref}>{pref}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <TagIcon className="h-4 w-4" />
                  業種
                </label>
                <select
                  value={filters.industry_type || ''}
                  onChange={(e) => handleChange('industry_type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">すべて</option>
                  <option value="物品">物品</option>
                  <option value="役務">役務</option>
                  <option value="工事">工事</option>
                  <option value="その他">その他</option>
                </select>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <CheckCircleIcon className="h-4 w-4" />
                  入札可否
                </label>
                <select
                  value={filters.eligibility_filter || 'all'}
                  onChange={(e) => {
                    const value = e.target.value as 'all' | 'eligible' | 'ineligible';
                    if (value === 'all') {
                      const newFilters = { ...filters };
                      delete newFilters.eligibility_filter;
                      onFilterChange(newFilters);
                    } else {
                      onFilterChange({ ...filters, eligibility_filter: value });
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">すべて</option>
                  <option value="eligible">入札可能のみ</option>
                  <option value="ineligible">入札不可能のみ</option>
                </select>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <CurrencyYenIcon className="h-4 w-4" />
                  予定価格範囲
                </label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={filters.price_min || ''}
                    onChange={(e) => handleChange('price_min', e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="最小"
                  />
                  <span className="text-gray-500">〜</span>
                  <input
                    type="number"
                    value={filters.price_max || ''}
                    onChange={(e) => handleChange('price_max', e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="最大"
                  />
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <CalendarIcon className="h-4 w-4" />
                  公告日範囲
                </label>
                <div className="flex gap-2 items-center">
                  <input
                    type="date"
                    value={filters.date_from || ''}
                    onChange={(e) => handleChange('date_from', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-gray-500">〜</span>
                  <input
                    type="date"
                    value={filters.date_to || ''}
                    onChange={(e) => handleChange('date_to', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={clearAllFilters}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                すべてクリア
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                適用
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AdvancedFilters;