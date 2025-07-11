import React from 'react';
import { BiddingCase } from '../types/bidding';
import { 
  ChartBarIcon, 
  CheckCircleIcon, 
  XCircleIcon
} from '@heroicons/react/24/outline';

interface DashboardSummaryProps {
  cases: BiddingCase[];
  loading?: boolean;
}

const DashboardSummary: React.FC<DashboardSummaryProps> = ({ cases, loading }) => {
  const calculateStats = () => {
    const total = cases.length;
    const eligible = cases.filter(c => c.is_eligible_to_bid === true).length;
    const ineligible = cases.filter(c => c.is_eligible_to_bid === false).length;
    const pending = cases.filter(c => c.is_eligible_to_bid === undefined).length;
    
    const totalValue = cases.reduce((sum, c) => sum + (c.planned_price || 0), 0);
    const avgValue = total > 0 ? totalValue / total : 0;

    return { total, eligible, ineligible, pending, totalValue, avgValue };
  };

  const stats = calculateStats();

  const summaryCards = [
    {
      title: '全案件数',
      value: stats.total,
      icon: ChartBarIcon,
      color: 'bg-blue-500',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700'
    },
    {
      title: '入札可能',
      value: stats.eligible,
      icon: CheckCircleIcon,
      color: 'bg-green-500',
      bgColor: 'bg-green-50',
      textColor: 'text-green-700'
    },
    {
      title: '入札不可',
      value: stats.ineligible,
      icon: XCircleIcon,
      color: 'bg-red-500',
      bgColor: 'bg-red-50',
      textColor: 'text-red-700'
    }
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {summaryCards.map((card, index) => (
        <div key={index} className={`${card.bgColor} rounded-lg p-4 border border-gray-100`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className={`text-sm font-medium ${card.textColor}`}>{card.title}</h3>
            <card.icon className={`h-5 w-5 ${card.textColor}`} />
          </div>
          <p className={`text-2xl font-bold ${card.textColor}`}>
            {card.value.toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
};

export default DashboardSummary;