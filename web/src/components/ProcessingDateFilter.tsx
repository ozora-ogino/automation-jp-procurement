import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarIcon } from '@heroicons/react/24/outline';
import { biddingAPI } from '../services/api';
import { format, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';

interface ProcessingDateFilterProps {
  selectedDate?: string;
  onDateChange: (date: string | undefined) => void;
}

const ProcessingDateFilter: React.FC<ProcessingDateFilterProps> = ({ selectedDate, onDateChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  const { data: processingDates, isLoading } = useQuery({
    queryKey: ['processing-dates'],
    queryFn: () => biddingAPI.getProcessingDates(),
  });

  const handleDateSelect = (date: string | undefined) => {
    onDateChange(date);
    setIsOpen(false);
  };

  const formatDate = (dateString: string) => {
    const date = parseISO(dateString);
    return format(date, 'yyyy年M月d日(E)', { locale: ja });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <CalendarIcon className="h-5 w-5 text-gray-500" />
        <span className="text-sm">
          {selectedDate ? formatDate(selectedDate) : '処理日で絞り込み'}
        </span>
        <svg
          className={`ml-2 h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 20 20"
        >
          <path
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.5"
            d="M6 8l4 4 4-4"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-y-auto">
          <div className="p-2">
            {selectedDate && (
              <button
                onClick={() => handleDateSelect(undefined)}
                className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
              >
                すべての日付を表示
              </button>
            )}
            
            {isLoading ? (
              <div className="px-3 py-2 text-sm text-gray-500">読み込み中...</div>
            ) : processingDates && processingDates.length > 0 ? (
              <div className="space-y-1">
                {processingDates.map((date) => (
                  <button
                    key={date.processing_date}
                    onClick={() => handleDateSelect(date.processing_date)}
                    className={`w-full text-left px-3 py-2 rounded transition-colors ${
                      selectedDate === date.processing_date
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">
                        {formatDate(date.processing_date)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {date.case_count}件
                      </span>
                    </div>
                    <div className="flex gap-4 mt-1 text-xs text-gray-500">
                      <span>入札可: {date.eligible_count}件</span>
                      <span>入札不可: {date.ineligible_count}件</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="px-3 py-2 text-sm text-gray-500">
                処理日データがありません
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessingDateFilter;