import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { biddingAPI } from '../services/api';
import BiddingCasesList from '../components/BiddingCasesList';
import StatsCards from '../components/StatsCards';
import Charts from '../components/Charts';
import SearchBar from '../components/SearchBar';
import Filters from '../components/Filters';
import QuickFilters from '../components/QuickFilters';
import { SearchParams } from '../types/bidding';

const Dashboard: React.FC = () => {
  const [searchParams, setSearchParams] = useState<SearchParams>({
    page: 1,
    limit: 20,
  });

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: biddingAPI.getStats,
  });

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          入札案件ダッシュボード
        </h1>
        <SearchBar onSearch={handleSearch} />
      </div>

      <StatsCards stats={statsData} loading={statsLoading} />

      <QuickFilters 
        onFilterApply={handleQuickFilterApply} 
        currentFilters={searchParams} 
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <Filters filters={searchParams} onFilterChange={handleFilterChange} />
        </div>
        
        <div className="lg:col-span-3">
          <BiddingCasesList 
            cases={casesData?.cases || []} 
            loading={casesLoading} 
          />
          
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

      {statsData && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            統計情報
          </h2>
          <Charts stats={statsData} />
        </div>
      )}
    </div>
  );
};

export default Dashboard;