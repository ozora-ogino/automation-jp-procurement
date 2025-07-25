import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { biddingAPI } from '../services/api';
import BiddingCaseCard from '../components/BiddingCaseCard';
import SearchBar from '../components/SearchBar';
import AdvancedFilters from '../components/AdvancedFilters';
import DashboardSummary from '../components/DashboardSummary';
import QuickFilters from '../components/QuickFilters';
import ProcessingDateFilter from '../components/ProcessingDateFilter';
import SortOptions from '../components/SortOptions';
import { SearchParams } from '../types/bidding';
import { Squares2X2Icon, ListBulletIcon } from '@heroicons/react/24/outline';
import { useURLSearchParams } from '../hooks/useURLSearchParams';
import { useURLSortParams } from '../hooks/useURLSortParams';
import { useURLViewMode } from '../hooks/useURLViewMode';
import { format, parseISO, isToday, isYesterday, differenceInDays } from 'date-fns';
import { ja } from 'date-fns/locale';

const Dashboard: React.FC = () => {
  // Use URL-based state management
  const { searchParams, setSearchParams } = useURLSearchParams({
    page: 1,
    limit: 20,
  });
  
  const { viewMode, setViewMode } = useURLViewMode('grid');
  const { sortOption, sortDirection, setSortParams } = useURLSortParams('created', 'desc');


  const { data: casesData, isLoading: casesLoading } = useQuery({
    queryKey: ['cases', searchParams],
    queryFn: () => biddingAPI.getCases(searchParams),
  });

  const handleSearch = (query: string) => {
    setSearchParams(prev => ({ ...prev, query, page: 1 }));
  };

  const handleFilterChange = (filters: SearchParams) => {
    setSearchParams(prev => ({ ...prev, ...filters, page: 1 }));
  };

  const handleQuickFilterApply = (filters: SearchParams) => {
    // For QuickFilters, we replace the entire filter state to handle deletions
    setSearchParams({ ...filters, page: 1 });
  };

  const handlePageChange = (page: number) => {
    setSearchParams(prev => ({ ...prev, page }));
  };

  const handleProcessingDateChange = (date: string | undefined) => {
    setSearchParams(prev => ({ ...prev, processed_date: date, page: 1 }));
  };

  const sortCases = (cases: any[]) => {
    const sorted = [...cases].sort((a, b) => {
      let compareValue = 0;
      
      switch (sortOption) {
        case 'deadline':
          if (!a.deadline && !b.deadline) return 0;
          if (!a.deadline) return 1;
          if (!b.deadline) return -1;
          compareValue = new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
          break;
        case 'price':
          compareValue = (a.planned_price || 0) - (b.planned_price || 0);
          break;
        case 'created':
          compareValue = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case 'organization':
          compareValue = (a.organization || '').localeCompare(b.organization || '');
          break;
      }
      
      return sortDirection === 'asc' ? compareValue : -compareValue;
    });
    
    return sorted;
  };

  const displayCases = casesData?.cases ? sortCases(casesData.cases) : [];

  // Group cases by date
  const groupCasesByDate = (cases: any[]) => {
    const groups: { [key: string]: any[] } = {};
    
    cases.forEach(caseItem => {
      const date = parseISO(caseItem.created_at);
      const dateKey = format(date, 'yyyy-MM-dd');
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(caseItem);
    });
    
    return groups;
  };

  const getDateLabel = (dateString: string) => {
    const date = parseISO(dateString);
    const today = new Date();
    const daysDiff = differenceInDays(today, date);
    
    if (isToday(date)) {
      return '今日';
    } else if (isYesterday(date)) {
      return '昨日';
    } else if (daysDiff < 7) {
      return format(date, 'M月d日(E)', { locale: ja });
    } else {
      return format(date, 'M月d日', { locale: ja });
    }
  };

  const groupedCases = groupCasesByDate(displayCases);
  const sortedDates = Object.keys(groupedCases).sort((a, b) => b.localeCompare(a)); // 新しい日付順

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          入札案件ダッシュボード
        </h1>
        <p className="text-gray-600 mb-6">政府調達案件の検索と入札可否判定</p>
      </div>

      <DashboardSummary cases={displayCases} loading={casesLoading} processingDate={searchParams.processed_date} />

      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
          <div className="flex-1 w-full lg:max-w-2xl">
            <SearchBar onSearch={handleSearch} />
          </div>
          <div className="flex gap-3 items-center">
            <ProcessingDateFilter
              selectedDate={searchParams.processed_date}
              onDateChange={handleProcessingDateChange}
            />
            <SortOptions 
              onSortChange={(sort, direction) => {
                setSortParams(sort, direction);
              }}
              currentSort={sortOption}
              currentDirection={sortDirection}
            />
            <AdvancedFilters filters={searchParams} onFilterChange={handleFilterChange} />
            <div className="flex rounded-lg border border-gray-300 bg-white">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 rounded-l-lg transition-colors ${
                  viewMode === 'grid' 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                title="グリッド表示"
              >
                <Squares2X2Icon className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 rounded-r-lg transition-colors ${
                  viewMode === 'list' 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                title="リスト表示"
              >
                <ListBulletIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <QuickFilters 
        onFilterApply={handleQuickFilterApply} 
        currentFilters={searchParams} 
      />

      <div>
        {casesLoading ? (
          <div className="space-y-8">
            {[...Array(3)].map((_, i) => (
              <div key={i}>
                <div className="h-6 bg-gray-200 rounded w-24 mb-4 animate-pulse"></div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
                      <div className="h-6 bg-gray-200 rounded w-3/4 mb-3"></div>
                      <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                      <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-8">
            {sortedDates.map((dateKey) => (
              <div key={dateKey}>
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">{getDateLabel(dateKey)}</span>
                  <span className="text-sm text-gray-500 font-normal">
                    ({groupedCases[dateKey].length}件)
                  </span>
                </h2>
                {viewMode === 'grid' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {groupedCases[dateKey].map((biddingCase) => (
                      <BiddingCaseCard key={biddingCase.id} biddingCase={biddingCase} />
                    ))}
                  </div>
                ) : (
                  <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              案件名
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              機関
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              締切
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              予定価格
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              状態
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {groupedCases[dateKey].map((biddingCase) => (
                            <tr key={biddingCase.id} className="hover:bg-gray-50">
                              <td className="px-6 py-4">
                                <Link 
                                  to={`/case/${biddingCase.id}`} 
                                  state={{ search: window.location.search }}
                                  className="text-blue-600 hover:text-blue-800 font-medium"
                                >
                                  {biddingCase.case_name}
                                </Link>
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-900">
                                {biddingCase.organization}
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-900">
                                {biddingCase.deadline ? new Date(biddingCase.deadline).toLocaleDateString('ja-JP') : '-'}
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-900">
                                {biddingCase.planned_price ? 
                                  new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(biddingCase.planned_price) : 
                                  '-'
                                }
                              </td>
                              <td className="px-6 py-4">
                                {biddingCase.is_eligible_to_bid !== undefined ? (
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    biddingCase.is_eligible_to_bid 
                                      ? 'bg-green-100 text-green-800' 
                                      : 'bg-red-100 text-red-800'
                                  }`}>
                                    {biddingCase.is_eligible_to_bid ? '入札可能' : '入札不可'}
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                    判定待ち
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        
        {casesData && casesData.pages > 1 && (
          <div className="mt-4 flex justify-center">
            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
              <button
                onClick={() => handlePageChange(casesData.page - 1)}
                disabled={casesData.page === 1}
                className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                前へ
              </button>
              
              {[...Array(Math.min(5, casesData.pages))].map((_, i) => {
                const pageNum = i + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                      pageNum === casesData.page
                        ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                        : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              
              <button
                onClick={() => handlePageChange(casesData.page + 1)}
                disabled={casesData.page === casesData.pages}
                className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                次へ
              </button>
            </nav>
          </div>
        )}
      </div>

    </div>
  );
};

export default Dashboard;