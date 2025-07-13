import { SearchParams } from '../types/bidding';

/**
 * Convert SearchParams object to URLSearchParams
 */
export const searchParamsToURL = (params: SearchParams): URLSearchParams => {
  const urlParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (typeof value === 'number') {
        urlParams.set(key, value.toString());
      } else if (typeof value === 'string') {
        urlParams.set(key, value);
      }
    }
  });
  
  return urlParams;
};

/**
 * Convert URLSearchParams to SearchParams object
 */
export const urlToSearchParams = (urlParams: URLSearchParams): SearchParams => {
  const params: SearchParams = {};
  
  // String fields
  const stringFields = ['query', 'organization', 'prefecture', 'industry_type', 
                       'eligibility_filter', 'date_from', 'date_to', 'processed_date'];
  
  stringFields.forEach(field => {
    const value = urlParams.get(field);
    if (value) {
      params[field as keyof SearchParams] = value as any;
    }
  });
  
  // Number fields
  const numberFields = ['price_min', 'price_max', 'page', 'limit'];
  
  numberFields.forEach(field => {
    const value = urlParams.get(field);
    if (value) {
      const numValue = parseInt(value, 10);
      if (!isNaN(numValue)) {
        params[field as keyof SearchParams] = numValue as any;
      }
    }
  });
  
  return params;
};

/**
 * Merge default params with URL params
 */
export const mergeWithDefaults = (urlParams: SearchParams, defaults: SearchParams): SearchParams => {
  return { ...defaults, ...urlParams };
};