import React from 'react';
import { CheckCircleIcon, XCircleIcon, ExclamationCircleIcon, LightBulbIcon } from '@heroicons/react/24/outline';

interface EligibilityDetailsSectionProps {
  isEligible?: boolean;
  reason?: string;
  details?: any;
}

const EligibilityDetailsSection: React.FC<EligibilityDetailsSectionProps> = ({
  isEligible,
  reason,
  details
}) => {
  if (isEligible === undefined) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <ExclamationCircleIcon className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-lg font-semibold text-yellow-900">LLM判定待ち</h3>
            <p className="mt-1 text-sm text-yellow-700">
              入札可否の判定は現在処理中です。しばらくお待ちください。
            </p>
          </div>
        </div>
      </div>
    );
  }

  const bgColor = isEligible ? 'bg-green-50' : 'bg-red-50';
  const borderColor = isEligible ? 'border-green-200' : 'border-red-200';
  const iconColor = isEligible ? 'text-green-600' : 'text-red-600';
  const titleColor = isEligible ? 'text-green-900' : 'text-red-900';
  const textColor = isEligible ? 'text-green-700' : 'text-red-700';
  const Icon = isEligible ? CheckCircleIcon : XCircleIcon;

  // Parse eligibility details
  let parsedDetails: any = {};
  try {
    if (typeof details === 'string') {
      parsedDetails = JSON.parse(details);
    } else if (typeof details === 'object') {
      parsedDetails = details;
    }
  } catch (e) {
    console.error('Failed to parse eligibility details:', e);
  }

  const reasonArray = parsedDetails.reason || [];
  const recommendations = parsedDetails.recommendations || [];

  return (
    <div className={`${bgColor} border ${borderColor} rounded-lg p-6`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-6 h-6 ${iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <h3 className={`text-lg font-semibold ${titleColor}`}>
            {isEligible ? '入札可能' : '入札不可'}
          </h3>
          
          {/* Main reason */}
          {reason && (
            <p className={`mt-2 text-base ${textColor}`}>
              {reason}
            </p>
          )}
          
          {/* Detailed reasons */}
          {reasonArray.length > 0 && (
            <div className="mt-4">
              <h4 className={`text-sm font-semibold ${titleColor} mb-2`}>判定理由</h4>
              <ul className={`space-y-1 ${textColor}`}>
                {reasonArray.map((item: string, index: number) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-sm mt-0.5">•</span>
                    <span className="text-sm">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="mt-4 bg-white bg-opacity-50 rounded-md p-4">
              <div className="flex items-center gap-2 mb-2">
                <LightBulbIcon className="w-5 h-5 text-amber-600" />
                <h4 className="text-sm font-semibold text-gray-900">推奨事項</h4>
              </div>
              <ul className="space-y-1">
                {recommendations.map((item: string, index: number) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-amber-600 text-sm mt-0.5">→</span>
                    <span className="text-sm text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Confidence score if available */}
          {parsedDetails.confidence !== undefined && (
            <div className="mt-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600">判定信頼度</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-xs">
                  <div
                    className={`h-2 rounded-full ${isEligible ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${parsedDetails.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-600">
                  {(parsedDetails.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EligibilityDetailsSection;