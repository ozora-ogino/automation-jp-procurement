import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { BiddingStats } from '../types/bidding';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface ChartsProps {
  stats: BiddingStats | undefined;
}

const Charts: React.FC<ChartsProps> = ({ stats }) => {
  if (!stats) return null;

  const trendData = {
    labels: stats.recent_trends.map(t => t.date),
    datasets: [
      {
        label: '案件数',
        data: stats.recent_trends.map(t => t.count),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
      },
    ],
  };

  const prefectureData = {
    labels: Object.keys(stats.cases_by_prefecture).slice(0, 10),
    datasets: [
      {
        label: '案件数',
        data: Object.values(stats.cases_by_prefecture).slice(0, 10),
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
      },
    ],
  };

  const industryData = {
    labels: Object.keys(stats.cases_by_industry).slice(0, 5),
    datasets: [
      {
        data: Object.values(stats.cases_by_industry).slice(0, 5),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(251, 146, 60, 0.8)',
          'rgba(147, 51, 234, 0.8)',
          'rgba(239, 68, 68, 0.8)',
        ],
      },
    ],
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">案件数の推移</h3>
        <Line data={trendData} options={{ responsive: true }} />
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">都道府県別案件数</h3>
        <Bar data={prefectureData} options={{ responsive: true }} />
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">業種別案件分布</h3>
        <Doughnut data={industryData} options={{ responsive: true }} />
      </div>
    </div>
  );
};

export default Charts;