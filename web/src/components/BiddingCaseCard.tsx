import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { format } from 'date-fns';
import { BiddingCase } from '../types/bidding';
import { 
  DocumentIcon, 
  ChevronDownIcon, 
  ChevronUpIcon,
  MapPinIcon,
  CalendarIcon,
  BuildingOfficeIcon,
  CurrencyYenIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

interface BiddingCaseCardProps {
  biddingCase: BiddingCase;
}

const BiddingCaseCard: React.FC<BiddingCaseCardProps> = ({ biddingCase }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const location = useLocation();

  const formatCurrency = (value?: number) => {
    if (!value) return '-';
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      notation: 'compact',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    try {
      return format(new Date(dateString), 'MM/dd');
    } catch {
      return dateString;
    }
  };

  const getEligibilityStatus = () => {
    if (biddingCase.is_eligible_to_bid === true) {
      return {
        icon: CheckCircleIcon,
        text: '入札可能',
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200'
      };
    } else if (biddingCase.is_eligible_to_bid === false) {
      return {
        icon: XCircleIcon,
        text: '入札不可',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200'
      };
    } else {
      return {
        icon: ClockIcon,
        text: '判定待ち',
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200'
      };
    }
  };

  const eligibilityStatus = getEligibilityStatus();

  const getDaysUntilDeadline = () => {
    if (!biddingCase.deadline) return null;
    const deadline = new Date(biddingCase.deadline);
    const today = new Date();
    const diffTime = deadline.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const daysUntilDeadline = getDaysUntilDeadline();

  return (
    <div className={`bg-white rounded-lg shadow-sm border ${eligibilityStatus.borderColor} hover:shadow-md transition-shadow`}>
      <Link 
        to={`/case/${biddingCase.id}`} 
        state={{ search: location.search }}
        className="block p-6"
      >
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1 pr-4">
            <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 mb-2">
              {biddingCase.case_name}
            </h3>
            
            <div className="flex flex-wrap gap-2 text-sm text-gray-600 mb-3">
              <div className="flex items-center gap-1">
                <BuildingOfficeIcon className="h-4 w-4" />
                <span className="truncate max-w-[200px]">{biddingCase.organization}</span>
              </div>
              {biddingCase.prefecture && (
                <div className="flex items-center gap-1">
                  <MapPinIcon className="h-4 w-4" />
                  <span>{biddingCase.prefecture}</span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-sm">
              <div className="flex items-center gap-1">
                <CalendarIcon className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600">締切: {formatDate(biddingCase.deadline)}</span>
                {daysUntilDeadline !== null && daysUntilDeadline >= 0 && (
                  <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    daysUntilDeadline <= 3 ? 'bg-red-100 text-red-700' :
                    daysUntilDeadline <= 7 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {daysUntilDeadline === 0 ? '本日' : `${daysUntilDeadline}日後`}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <CurrencyYenIcon className="h-4 w-4 text-gray-400" />
                <span className="font-medium text-gray-900">{formatCurrency(biddingCase.planned_price)}</span>
              </div>
            </div>
          </div>

          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${eligibilityStatus.bgColor} ${eligibilityStatus.color} font-medium text-sm`}>
            <eligibilityStatus.icon className="h-5 w-5" />
            <span>{eligibilityStatus.text}</span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex flex-wrap gap-2">
            {biddingCase.industry_type && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {biddingCase.industry_type}
              </span>
            )}
            {biddingCase.document_count && biddingCase.document_count > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                <DocumentIcon className="h-3 w-3" />
                {biddingCase.downloaded_count || 0}/{biddingCase.document_count}
              </span>
            )}
          </div>

          <button
            onClick={(e) => {
              e.preventDefault();
              setIsExpanded(!isExpanded);
            }}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            {isExpanded ? (
              <ChevronUpIcon className="h-5 w-5" />
            ) : (
              <ChevronDownIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </Link>

      {isExpanded && (
        <div className="px-6 pb-6 pt-0 border-t border-gray-100">
          <div className="mt-4 space-y-2 text-sm">
            {biddingCase.department && (
              <div className="flex">
                <span className="text-gray-500 w-20">部署:</span>
                <span className="text-gray-700">{biddingCase.department}</span>
              </div>
            )}
            {biddingCase.bidding_format && (
              <div className="flex">
                <span className="text-gray-500 w-20">入札形式:</span>
                <span className="text-gray-700">{biddingCase.bidding_format}</span>
              </div>
            )}
            {biddingCase.eligibility_reason && (
              <div className="flex">
                <span className="text-gray-500 w-20">判定理由:</span>
                <span className={`${eligibilityStatus.color} font-medium`}>
                  {biddingCase.eligibility_reason}
                </span>
              </div>
            )}
            <div className="flex gap-4 text-xs text-gray-500 mt-3">
              <span>公告日: {formatDate(biddingCase.announcement_date)}</span>
              {biddingCase.bidding_date && (
                <span>入札日: {formatDate(biddingCase.bidding_date)}</span>
              )}
            </div>
          </div>
          <Link
            to={`/case/${biddingCase.id}`}
            state={{ search: location.search }}
            className="inline-flex items-center mt-4 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            詳細を見る →
          </Link>
        </div>
      )}
    </div>
  );
};

export default BiddingCaseCard;