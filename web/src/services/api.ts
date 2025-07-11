import axios from 'axios';
import { BiddingCase, SearchParams } from '../types/bidding';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const biddingAPI = {
  getCases: async (params: SearchParams = {}) => {
    const response = await api.get<{
      cases: BiddingCase[];
      total: number;
      page: number;
      pages: number;
    }>('/bidding/cases', { params });
    return response.data;
  },

  getCase: async (id: string) => {
    const response = await api.get<BiddingCase>(`/bidding/cases/${id}`);
    return response.data;
  },

  getProcessingDates: async () => {
    const response = await api.get<{
      processing_date: string;
      case_count: number;
      eligible_count: number;
      ineligible_count: number;
      first_processed: string;
      last_processed: string;
    }[]>('/bidding/processing-dates');
    return response.data;
  },

  searchCases: async (query: string) => {
    const response = await api.get<BiddingCase[]>('/bidding/search', {
      params: { q: query },
    });
    return response.data;
  },

  getSimilarCases: async (id: string, limit: number = 5) => {
    const response = await api.get<BiddingCase[]>(`/bidding/cases/${id}/similar`, {
      params: { limit },
    });
    return response.data;
  },
};