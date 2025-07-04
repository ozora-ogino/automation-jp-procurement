import React from 'react';
import { BiddingStats } from '../types/bidding';

interface StatsCardsProps {
  stats: BiddingStats | undefined;
  loading?: boolean;
}

const StatsCards: React.FC<StatsCardsProps> = ({ stats, loading }) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('ja-JP').format(value);
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const cards = [
    {
      title: '総案件数',
      value: formatNumber(stats.total_cases),
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: '入札可能案件',
      value: formatNumber(stats.eligible_cases),
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: '入札可能率',
      value: `${stats.eligibility_percentage.toFixed(1)}%`,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cards.map((card, index) => (
        <div key={index} className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">{card.title}</p>
          <p className={`text-2xl font-bold mt-2 ${card.color}`}>
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;