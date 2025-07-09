import React from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { BiddingCase } from '../types/bidding';
import { DocumentIcon } from '@heroicons/react/24/outline';

interface BiddingCasesListProps {
  cases: BiddingCase[];
  loading?: boolean;
}

const BiddingCasesList: React.FC<BiddingCasesListProps> = ({ cases, loading }) => {
  const formatCurrency = (value?: number) => {
    if (!value) return '-';
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
    }).format(value);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    try {
      return format(new Date(dateString), 'yyyy年MM月dd日');
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="mb-4">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">入札案件一覧</h2>
      </div>
      <div className="divide-y divide-gray-200">
        {cases.map((biddingCase) => (
          <Link
            key={biddingCase.id}
            to={`/case/${biddingCase.id}`}
            className="block px-6 py-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-base font-medium text-gray-900 mb-1">
                  {biddingCase.case_name}
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>機関: {biddingCase.organization}</p>
                  {biddingCase.department && (
                    <p>部署: {biddingCase.department}</p>
                  )}
                  <div className="flex gap-4">
                    <span>公告日: {formatDate(biddingCase.announcement_date)}</span>
                    <span>締切: {formatDate(biddingCase.deadline)}</span>
                  </div>
                </div>
              </div>
              <div className="text-right ml-4">
                <div className="text-sm text-gray-600">
                  <p>予定価格</p>
                  <p className="font-medium text-gray-900">
                    {formatCurrency(biddingCase.planned_price)}
                  </p>
                </div>
                {biddingCase.winning_price && (
                  <div className="text-sm text-gray-600 mt-2">
                    <p>落札価格</p>
                    <p className="font-medium text-green-600">
                      {formatCurrency(biddingCase.winning_price)}
                    </p>
                  </div>
                )}
              </div>
            </div>
            <div className="mt-2 flex gap-2">
              {biddingCase.prefecture && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {biddingCase.prefecture}
                </span>
              )}
              {biddingCase.industry_type && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {biddingCase.industry_type}
                </span>
              )}
              {biddingCase.status && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  {biddingCase.status}
                </span>
              )}
              {biddingCase.is_eligible_to_bid !== undefined && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  biddingCase.is_eligible_to_bid 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {biddingCase.is_eligible_to_bid ? '入札可能' : '入札不可'}
                </span>
              )}
              {biddingCase.document_count && biddingCase.document_count > 0 && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  <DocumentIcon className="h-3 w-3 mr-1" />
                  {biddingCase.downloaded_count || 0}/{biddingCase.document_count} 文書
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default BiddingCasesList;