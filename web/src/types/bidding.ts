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
  // status field removed - no longer needed
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
  
  // LLM extracted data
  llm_extracted_data?: LLMExtractedData;
  llm_extraction_timestamp?: string;
}

export interface LLMExtractedData {
  important_dates?: {
    announcement_date?: string;
    briefing_session?: {
      date?: string;
      is_mandatory?: boolean;
      location?: string;
    };
    question_deadline?: string;
    submission_deadline?: string;
    opening_date?: string;
    contract_date?: string;
    performance_period?: {
      start?: string;
      end?: string;
      description?: string;
    };
  };
  
  qualification_requirements?: {
    unified_qualification?: {
      required?: boolean;
      category?: string;
      rank?: string;
      valid_regions?: string[];
    };
    specific_qualifications?: Array<{
      name?: string;
      details?: string;
      is_mandatory?: boolean;
    }>;
    experience_requirements?: Array<{
      type?: string;
      details?: string;
      period?: string;
      scale?: string;
    }>;
    financial_requirements?: {
      capital?: string;
      annual_revenue?: string;
      financial_soundness?: string;
    };
    personnel_requirements?: Array<{
      role?: string;
      qualification?: string;
      experience?: string;
      number?: string;
    }>;
    other_requirements?: string[];
  };
  
  business_content?: {
    overview?: string;
    detailed_content?: string;
    scope_of_work?: string[];
    deliverables?: Array<{
      item?: string;
      deadline?: string;
      format?: string;
      quantity?: string;
    }>;
    technical_requirements?: Array<{
      category?: string;
      requirement?: string;
      priority?: string;
    }>;
    performance_location?: string;
    work_conditions?: string;
  };
  
  financial_info?: {
    budget_amount?: string;
    budget_disclosure?: string;
    minimum_price?: {
      exists?: boolean;
      calculation_method?: string;
    };
    payment_terms?: {
      method?: string;
      timing?: string;
      conditions?: string;
    };
    advance_payment?: {
      available?: boolean;
      percentage?: string;
      conditions?: string;
    };
    bid_bond?: {
      required?: boolean;
      amount?: string;
      exemption_conditions?: string;
    };
    performance_bond?: {
      required?: boolean;
      amount?: string;
      exemption_conditions?: string;
    };
  };
  
  submission_requirements?: {
    bid_documents?: Array<{
      document_name?: string;
      format?: string;
      copies?: string;
      notes?: string;
    }>;
    technical_proposal?: {
      required?: boolean;
      page_limit?: string;
      evaluation_items?: string[];
    };
    submission_method?: {
      options?: string[];
      electronic_system?: string;
      notes?: string;
    };
    submission_location?: {
      address?: string;
      department?: string;
      reception_hours?: string;
    };
  };
  
  evaluation_criteria?: {
    evaluation_method?: string;
    price_weight?: string;
    technical_weight?: string;
    evaluation_items?: Array<{
      category?: string;
      item?: string;
      points?: string;
      criteria?: string;
    }>;
    minimum_technical_score?: string;
  };
  
  contact_info?: {
    contract_department?: {
      name?: string;
      person?: string;
      phone?: string;
      fax?: string;
      email?: string;
      hours?: string;
    };
    technical_department?: {
      name?: string;
      person?: string;
      phone?: string;
      email?: string;
    };
  };
  
  special_conditions?: {
    joint_venture?: {
      allowed?: boolean;
      conditions?: string;
    };
    subcontracting?: {
      allowed?: boolean;
      restrictions?: string;
    };
    confidentiality?: string;
    intellectual_property?: string;
    penalty_clauses?: string;
  };
  
  risk_analysis?: {
    key_points?: Array<{
      point?: string;
      importance?: string;
      reason?: string;
    }>;
    red_flags?: Array<{
      issue?: string;
      severity?: string;
      description?: string;
      mitigation?: string;
    }>;
    unclear_points?: Array<{
      item?: string;
      impact?: string;
      action_required?: string;
    }>;
  };
  
  bid_feasibility?: {
    strengths?: string[];
    weaknesses?: string[];
    preparation_time?: string;
    resource_requirements?: string;
    competition_level?: string;
    recommendation?: {
      participate?: string;
      reasoning?: string;
      conditions?: string[];
    };
  };
  
  _metadata?: {
    extraction_timestamp?: string;
    model_used?: string;
    case_id?: string;
    token_usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

export interface BiddingStats {
  total_cases: number;
  total_value: number;
  // active_cases field removed - no longer needed
  // completed_cases field removed - no longer needed
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
  // status field removed - no longer needed
  eligible_only?: boolean;
  eligibility_filter?: 'all' | 'eligible' | 'ineligible';
  date_from?: string;
  date_to?: string;
  price_min?: number;
  price_max?: number;
  page?: number;
  limit?: number;
}