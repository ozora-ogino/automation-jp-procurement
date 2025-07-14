import React from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { biddingAPI } from '../services/api';
import DocumentsSection from '../components/DocumentsSection';
import LLMExtractedDataSection from '../components/LLMExtractedDataSection';
import EligibilityDetailsSection from '../components/EligibilityDetailsSection';
import CaseChatbot from '../components/CaseChatbot';

const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  
  // Get the search params from the referring page (if any)
  const referrerSearch = location.state?.search || '';
  
  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => biddingAPI.getCase(id!),
    enabled: !!id,
  });

  const { data: similarCases } = useQuery({
    queryKey: ['similarCases', id],
    queryFn: () => biddingAPI.getSimilarCases(id!, 5),
    enabled: !!id,
  });

  const formatCurrency = (value?: number) => {
    if (!value) return '-';
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
    }).format(value);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    try {
      return format(new Date(dateString), 'yyyy年MM月dd日');
    } catch {
      return dateString;
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-4"></div>
        <div className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            {[...Array(10)].map((_, i) => (
              <div key={i}>
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">案件が見つかりませんでした。</p>
        <Link to="/" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
          ダッシュボードに戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{caseData.case_name}</h1>
        <Link
          to={`/${referrerSearch}`}
          className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          戻る
        </Link>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-semibold">基本情報</h2>
        </div>
        <div className="p-6">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">案件ID</dt>
              <dd className="mt-1 text-sm text-gray-900">{caseData.case_id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">機関</dt>
              <dd className="mt-1 text-sm text-gray-900">{caseData.organization}</dd>
            </div>
            {caseData.department && (
              <div>
                <dt className="text-sm font-medium text-gray-500">部署</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.department}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-gray-500">所在地</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {caseData.location || '-'}
                {caseData.prefecture && ` (${caseData.prefecture})`}
              </dd>
            </div>
            {caseData.delivery_location && (
              <div>
                <dt className="text-sm font-medium text-gray-500">履行/納品場所</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.delivery_location}</dd>
              </div>
            )}
            {caseData.search_condition && (
              <div>
                <dt className="text-sm font-medium text-gray-500">検索条件</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.search_condition}</dd>
              </div>
            )}
            {caseData.bidding_format && (
              <div>
                <dt className="text-sm font-medium text-gray-500">入札形式</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.bidding_format}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-gray-500">公告日</dt>
              <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.announcement_date)}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">入札日</dt>
              <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.bidding_date) || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">締切日</dt>
              <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.deadline)}</dd>
            </div>
            {caseData.briefing_date && (
              <div>
                <dt className="text-sm font-medium text-gray-500">説明会日</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.briefing_date)}</dd>
              </div>
            )}
            {caseData.award_announcement_date && (
              <div>
                <dt className="text-sm font-medium text-gray-500">落札結果公示日</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.award_announcement_date)}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-gray-500">業種</dt>
              <dd className="mt-1 text-sm text-gray-900">{caseData.industry_type || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">業務種別</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {caseData.business_type && caseData.business_type.length > 0 ? (
                  <div className="space-y-1">
                    {caseData.business_type.map((type, index) => (
                      <div key={index}>
                        {type}
                        {caseData.business_type_code && caseData.business_type_code[index] && 
                          ` (${caseData.business_type_code[index]})`}
                      </div>
                    ))}
                  </div>
                ) : '-'}
              </dd>
            </div>
            {caseData.case_url && (
              <div className="md:col-span-2">
                <dt className="text-sm font-medium text-gray-500">案件URL</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  <a href={caseData.case_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline">
                    {caseData.case_url}
                  </a>
                </dd>
              </div>
            )}
            {/* Eligibility status is shown in a separate section below */}
          </dl>
        </div>
      </div>

      {/* Eligibility Status Section */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-semibold">入札可否判定</h2>
        </div>
        <div className="p-6">
          <EligibilityDetailsSection
            isEligible={caseData.is_eligible_to_bid}
            reason={caseData.eligibility_reason}
            details={caseData.eligibility_details}
          />
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-semibold">入札情報</h2>
        </div>
        <div className="p-6">
          <dl className="space-y-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">入札資格</dt>
              <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
                {caseData.qualification_requirements || '-'}
              </dd>
            </div>
            {caseData.qualification_summary && (
              <div>
                <dt className="text-sm font-medium text-gray-500">資格要件サマリー</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {caseData.qualification_summary.rank && (
                    <div className="mb-2">
                      <span className="font-medium">必要ランク: </span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        {caseData.qualification_summary.rank}
                      </span>
                    </div>
                  )}
                  {/* Confidence score removed from display */}
                </dd>
              </div>
            )}
            {caseData.qualification_details && (
              <div>
                <dt className="text-sm font-medium text-gray-500">資格詳細</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {Array.isArray(caseData.qualification_details) && caseData.qualification_details.length > 0 && (
                    <div className="space-y-2">
                      {caseData.qualification_details.map((qual: any, index: number) => (
                        <div key={index} className="border-l-4 border-blue-400 pl-3 py-1">
                          <div className="font-medium">{qual.type || '資格要件'}</div>
                          {qual.level && <div>ランク: {qual.level}</div>}
                          {qual.category && <div>カテゴリ: {qual.category}</div>}
                          {qual.original_text && <div className="text-gray-600 text-xs mt-1">{qual.original_text}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </dd>
              </div>
            )}
            {/* Eligibility details moved to dedicated section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">予定価格</dt>
                <dd className="mt-1">
                  <div className="text-lg font-semibold text-gray-900">
                    {formatCurrency(caseData.planned_price)}
                  </div>
                  {caseData.planned_price_raw && caseData.planned_price_raw !== String(caseData.planned_price) && (
                    <div className="text-sm text-gray-500">元データ: {caseData.planned_price_raw}</div>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">落札価格</dt>
                <dd className="mt-1">
                  <div className="text-lg font-semibold text-green-600">
                    {formatCurrency(caseData.winning_price)}
                  </div>
                  {caseData.award_price_raw && caseData.award_price_raw !== String(caseData.winning_price) && (
                    <div className="text-sm text-gray-500">元データ: {caseData.award_price_raw}</div>
                  )}
                </dd>
              </div>
              {caseData.planned_unit_price && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">予定単価</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {formatCurrency(caseData.planned_unit_price)}
                  </dd>
                </div>
              )}
              {caseData.award_unit_price && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">落札単価</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {formatCurrency(caseData.award_unit_price)}
                  </dd>
                </div>
              )}
            </div>
            {caseData.winner_name && (
              <div>
                <dt className="text-sm font-medium text-gray-500">落札者</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {caseData.winner_name}
                  {caseData.winner_location && ` (${caseData.winner_location})`}
                </dd>
              </div>
            )}
            {caseData.winning_reason && (
              <div>
                <dt className="text-sm font-medium text-gray-500">落札理由</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.winning_reason}</dd>
              </div>
            )}
            {caseData.winning_score && (
              <div>
                <dt className="text-sm font-medium text-gray-500">落札評点</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.winning_score}</dd>
              </div>
            )}
            {caseData.award_remarks && (
              <div>
                <dt className="text-sm font-medium text-gray-500">落札結果備考</dt>
                <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{caseData.award_remarks}</dd>
              </div>
            )}
            {caseData.unsuccessful_bid && (
              <div>
                <dt className="text-sm font-medium text-gray-500">不調</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.unsuccessful_bid}</dd>
              </div>
            )}
            {caseData.contract_date && (
              <div>
                <dt className="text-sm font-medium text-gray-500">契約日</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(caseData.contract_date)}</dd>
              </div>
            )}
            {caseData.bid_result_details && (
              <div>
                <dt className="text-sm font-medium text-gray-500">入札結果詳細</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  <pre className="bg-gray-50 p-2 rounded text-xs">
                    {JSON.stringify(caseData.bid_result_details, null, 2)}
                  </pre>
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {(caseData.description || caseData.notes) && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-lg font-semibold">詳細情報</h2>
          </div>
          <div className="p-6 space-y-4">
            {caseData.description && (
              <div>
                <dt className="text-sm font-medium text-gray-500">説明</dt>
                <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
                  {caseData.description}
                </dd>
              </div>
            )}
            {caseData.notes && (
              <div>
                <dt className="text-sm font-medium text-gray-500">備考</dt>
                <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
                  {caseData.notes}
                </dd>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Processing and System Information */}
      {(caseData.processed_at || caseData.qualification_confidence) && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-lg font-semibold">処理情報</h2>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {caseData.processed_at && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">処理日時</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {formatDate(caseData.processed_at)} {new Date(caseData.processed_at).toLocaleTimeString('ja-JP')}
                  </dd>
                </div>
              )}
              {/* Qualification confidence removed from display */}
              <div>
                <dt className="text-sm font-medium text-gray-500">作成日時</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {formatDate(caseData.created_at)} {new Date(caseData.created_at).toLocaleTimeString('ja-JP')}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">更新日時</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {formatDate(caseData.updated_at)} {new Date(caseData.updated_at).toLocaleTimeString('ja-JP')}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {/* Documents Section */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-semibold">文書情報</h2>
        </div>
        <div className="px-6 py-4">
          <DocumentsSection
            documents={caseData.documents}
            documentCount={caseData.document_count}
            downloadedCount={caseData.downloaded_count}
            documentDirectory={caseData.document_directory}
          />
        </div>
      </div>

      {/* LLM Extracted Data Section */}
      {caseData.llm_extracted_data && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-lg font-semibold">AI抽出情報</h2>
            <p className="text-sm text-gray-600 mt-1">文書から自動抽出された詳細情報</p>
          </div>
          <div className="px-6 py-4">
            <LLMExtractedDataSection 
              data={caseData.llm_extracted_data} 
              timestamp={caseData.llm_extraction_timestamp}
            />
          </div>
        </div>
      )}

      {similarCases && similarCases.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-lg font-semibold">類似案件</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {similarCases.map((similarCase) => (
              <Link
                key={similarCase.id}
                to={`/case/${similarCase.id}`}
                className="block px-6 py-4 hover:bg-gray-50"
              >
                <h3 className="text-sm font-medium text-gray-900">{similarCase.case_name}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {similarCase.organization} • {formatCurrency(similarCase.planned_price)}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}
      
      {/* Chatbot Component */}
      {caseData && (
        <CaseChatbot caseId={String(caseData.case_id)} caseName={caseData.case_name} />
      )}
    </div>
  );
};

export default CaseDetail;