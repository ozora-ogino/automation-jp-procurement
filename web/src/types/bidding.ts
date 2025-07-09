export interface BiddingCase {
  id: string;
  case_id: string;
  case_name: string;
  organization: string;
  department?: string;
  location?: string;
  prefecture?: string;
  announcement_date?: string;
  deadline?: string;
  industry_type?: string;
  business_type?: string[];
  business_type_code?: string[];
  qualification_requirements?: string;
  qualification_details?: any;
  qualification_summary?: any;
  planned_price?: number;
  winning_price?: number;
  winner_name?: string;
  winner_location?: string;
  contract_date?: string;
  description?: string;
  notes?: string;
  status?: string;
  is_eligible_to_bid?: boolean;
  eligibility_reason?: string;
  eligibility_details?: any;
  created_at: string;
  updated_at: string;
  
  // Additional fields
  search_condition?: string;
  bidding_format?: string;
  case_url?: string;
  delivery_location?: string;
  bidding_date?: string;
  briefing_date?: string;
  award_announcement_date?: string;
  business_types_normalized?: string[];
  planned_price_raw?: string;
  planned_unit_price?: number;
  award_price_raw?: string;
  award_unit_price?: number;
  main_price?: number;
  winning_reason?: string;
  winning_score?: number;
  award_remarks?: string;
  bid_result_details?: any;
  unsuccessful_bid?: string;
  processed_at?: string;
  qualification_confidence?: number;
  
  // Document fields
  document_directory?: string;
  document_count?: number;
  downloaded_count?: number;
  documents?: Array<{
    name: string;
    type: string;
    url: string;
    index: number;
    anken_id: string;
  }>;
}

export interface BiddingStats {
  total_cases: number;
  total_value: number;
  active_cases: number;
  completed_cases: number;
  average_winning_price: number;
  eligible_cases: number;
  ineligible_cases: number;
  eligibility_percentage: number;
  cases_by_prefecture: Record<string, number>;
  cases_by_industry: Record<string, number>;
  recent_trends: {
    date: string;
    count: number;
    value: number;
  }[];
}

export interface SearchParams {
  query?: string;
  organization?: string;
  prefecture?: string;
  industry_type?: string;
  status?: string;
  eligible_only?: boolean;
  eligibility_filter?: 'all' | 'eligible' | 'ineligible';
  date_from?: string;
  date_to?: string;
  price_min?: number;
  price_max?: number;
  page?: number;
  limit?: number;
}