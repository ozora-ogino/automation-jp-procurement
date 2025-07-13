import { useSearchParams } from 'react-router-dom';
import { useCallback, useMemo } from 'react';

type ViewMode = 'grid' | 'list';

/**
 * Custom hook to manage view mode in URL
 */
export const useURLViewMode = (defaultMode: ViewMode = 'grid') => {
  const [urlSearchParams, setURLSearchParams] = useSearchParams();
  
  // Parse current view mode from URL
  const viewMode = useMemo((): ViewMode => {
    const mode = urlSearchParams.get('view') as ViewMode | null;
    return mode || defaultMode;
  }, [urlSearchParams, defaultMode]);
  
  // Update view mode in URL
  const setViewMode = useCallback((mode: ViewMode) => {
    setURLSearchParams(prevParams => {
      const newParams = new URLSearchParams(prevParams);
      newParams.set('view', mode);
      return newParams;
    });
  }, [setURLSearchParams]);
  
  return {
    viewMode,
    setViewMode,
  };
};