import { useSearchParams } from 'react-router-dom';
import { useCallback, useMemo } from 'react';
import { SearchParams } from '../types/bidding';
import { searchParamsToURL, urlToSearchParams, mergeWithDefaults } from '../utils/urlParams';

/**
 * Custom hook to manage search parameters in URL
 */
export const useURLSearchParams = (defaultParams: SearchParams) => {
  const [urlSearchParams, setURLSearchParams] = useSearchParams();
  
  // Parse current URL params and merge with defaults
  const searchParams = useMemo(() => {
    const parsed = urlToSearchParams(urlSearchParams);
    return mergeWithDefaults(parsed, defaultParams);
  }, [urlSearchParams, defaultParams]);
  
  // Update URL params
  const setSearchParams = useCallback((
    updater: SearchParams | ((prev: SearchParams) => SearchParams)
  ) => {
    setURLSearchParams(prevParams => {
      const currentParams = urlToSearchParams(prevParams);
      const mergedParams = mergeWithDefaults(currentParams, defaultParams);
      
      const newParams = typeof updater === 'function' 
        ? updater(mergedParams)
        : updater;
      
      return searchParamsToURL(newParams);
    });
  }, [setURLSearchParams, defaultParams]);
  
  // Clear all params and reset to defaults
  const resetSearchParams = useCallback(() => {
    setURLSearchParams(searchParamsToURL(defaultParams));
  }, [setURLSearchParams, defaultParams]);
  
  return {
    searchParams,
    setSearchParams,
    resetSearchParams,
  };
};