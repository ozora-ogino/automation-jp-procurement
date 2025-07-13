import { useSearchParams } from 'react-router-dom';
import { useCallback, useMemo } from 'react';
import { SortOption, SortDirection } from '../components/SortOptions';

interface SortParams {
  sortOption: SortOption;
  sortDirection: SortDirection;
}

/**
 * Custom hook to manage sort parameters in URL
 */
export const useURLSortParams = (defaultSort: SortOption = 'created', defaultDirection: SortDirection = 'desc') => {
  const [urlSearchParams, setURLSearchParams] = useSearchParams();
  
  // Parse current sort params from URL
  const sortParams = useMemo((): SortParams => {
    const sort = urlSearchParams.get('sort') as SortOption | null;
    const direction = urlSearchParams.get('direction') as SortDirection | null;
    
    return {
      sortOption: sort || defaultSort,
      sortDirection: direction || defaultDirection,
    };
  }, [urlSearchParams, defaultSort, defaultDirection]);
  
  // Update sort params in URL
  const setSortParams = useCallback((
    option: SortOption,
    direction: SortDirection
  ) => {
    setURLSearchParams(prevParams => {
      const newParams = new URLSearchParams(prevParams);
      newParams.set('sort', option);
      newParams.set('direction', direction);
      return newParams;
    });
  }, [setURLSearchParams]);
  
  return {
    sortOption: sortParams.sortOption,
    sortDirection: sortParams.sortDirection,
    setSortParams,
  };
};