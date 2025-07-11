import React, { useState } from 'react';
import { LLMExtractedData } from '../types/bidding';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface LLMExtractedDataSectionProps {
  data?: LLMExtractedData;
  timestamp?: string;
}

const LLMExtractedDataSection: React.FC<LLMExtractedDataSectionProps> = ({ data, timestamp }) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    dates: true,
    qualification: true,
    business: false,
    financial: false,
    submission: false,
    evaluation: false,
    contact: false,
    special: false,
    risk: true,
    feasibility: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (!data) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>LLM抽出データがありません</p>
      </div>
    );
  }

  const formatCurrency = (value?: string) => {
    if (!value) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
    }).format(num);
  };

  const SectionHeader = ({ title, section }: { title: string; section: string }) => (
    <button
      onClick={() => toggleSection(section)}
      className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
    >
      <h3 className="text-md font-semibold text-gray-800">{title}</h3>
      {expandedSections[section] ? (
        <ChevronUpIcon className="h-5 w-5 text-gray-500" />
      ) : (
        <ChevronDownIcon className="h-5 w-5 text-gray-500" />
      )}
    </button>
  );

  return (
    <div className="space-y-4">
      {/* Metadata */}
      {timestamp && (
        <div className="text-sm text-gray-500 text-right">
          抽出日時: {new Date(timestamp).toLocaleString('ja-JP')}
          {data._metadata?.model_used && ` | Model: ${data._metadata.model_used}`}
          {data._metadata?.token_usage?.total_tokens && ` | Tokens: ${data._metadata.token_usage.total_tokens.toLocaleString()}`}
        </div>
      )}

      {/* Important Dates */}
      {data.important_dates && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="重要日程" section="dates" />
          {expandedSections.dates && (
            <div className="p-4">
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.important_dates.announcement_date && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">公告日</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.important_dates.announcement_date}</dd>
                  </div>
                )}
                {data.important_dates.submission_deadline && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">提出締切</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.important_dates.submission_deadline}</dd>
                  </div>
                )}
                {data.important_dates.opening_date && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">開札日時</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.important_dates.opening_date}</dd>
                  </div>
                )}
                {data.important_dates.briefing_session?.date && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">説明会</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {data.important_dates.briefing_session.date}
                      {data.important_dates.briefing_session.is_mandatory && (
                        <span className="ml-2 text-red-600 font-semibold">(参加必須)</span>
                      )}
                      {data.important_dates.briefing_session.location && (
                        <div className="text-xs text-gray-500">場所: {data.important_dates.briefing_session.location}</div>
                      )}
                    </dd>
                  </div>
                )}
                {data.important_dates.performance_period && (
                  <div className="md:col-span-2">
                    <dt className="text-sm font-medium text-gray-500">履行期間</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {data.important_dates.performance_period.start} ～ {data.important_dates.performance_period.end}
                      {data.important_dates.performance_period.description && (
                        <div className="text-xs text-gray-500 mt-1">{data.important_dates.performance_period.description}</div>
                      )}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      )}

      {/* Qualification Requirements */}
      {data.qualification_requirements && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="資格要件" section="qualification" />
          {expandedSections.qualification && (
            <div className="p-4 space-y-4">
              {data.qualification_requirements.unified_qualification && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">全省庁統一資格</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    <p>必要: {data.qualification_requirements.unified_qualification.required ? 'はい' : 'いいえ'}</p>
                    {data.qualification_requirements.unified_qualification.category && (
                      <p>カテゴリ: {data.qualification_requirements.unified_qualification.category}</p>
                    )}
                    {data.qualification_requirements.unified_qualification.rank && (
                      <p>ランク: <span className="font-semibold">{data.qualification_requirements.unified_qualification.rank}</span></p>
                    )}
                    {data.qualification_requirements.unified_qualification.valid_regions && data.qualification_requirements.unified_qualification.valid_regions.length > 0 && (
                      <p>有効地域: {data.qualification_requirements.unified_qualification.valid_regions.join(', ')}</p>
                    )}
                  </div>
                </div>
              )}
              
              {data.qualification_requirements.experience_requirements && data.qualification_requirements.experience_requirements.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">実績要件</h4>
                  <ul className="space-y-2">
                    {data.qualification_requirements.experience_requirements.map((req, idx) => (
                      <li key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{req.type}</p>
                        {req.details && <p className="text-sm text-gray-600">{req.details}</p>}
                        {req.period && <p className="text-sm text-gray-500">期間: {req.period}</p>}
                        {req.scale && <p className="text-sm text-gray-500">規模: {req.scale}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.qualification_requirements.financial_requirements && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">財務要件</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    {data.qualification_requirements.financial_requirements.capital && (
                      <p>資本金: {data.qualification_requirements.financial_requirements.capital}</p>
                    )}
                    {data.qualification_requirements.financial_requirements.annual_revenue && (
                      <p>年間売上高: {data.qualification_requirements.financial_requirements.annual_revenue}</p>
                    )}
                    {data.qualification_requirements.financial_requirements.financial_soundness && (
                      <p>財務健全性: {data.qualification_requirements.financial_requirements.financial_soundness}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Risk Analysis */}
      {data.risk_analysis && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="リスク分析" section="risk" />
          {expandedSections.risk && (
            <div className="p-4 space-y-4">
              {data.risk_analysis.key_points && data.risk_analysis.key_points.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">重要ポイント</h4>
                  <ul className="space-y-2">
                    {data.risk_analysis.key_points.map((point, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className={`inline-block px-2 py-1 text-xs font-semibold rounded mr-2 ${
                          point.importance === '高' ? 'bg-red-100 text-red-800' :
                          point.importance === '中' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {point.importance}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium">{point.point}</p>
                          {point.reason && <p className="text-sm text-gray-600">{point.reason}</p>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.risk_analysis.red_flags && data.risk_analysis.red_flags.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">懸念事項</h4>
                  <ul className="space-y-2">
                    {data.risk_analysis.red_flags.map((flag, idx) => (
                      <li key={idx} className="border-l-4 border-red-400 pl-3 py-2">
                        <div className="flex items-start">
                          <span className={`inline-block px-2 py-1 text-xs font-semibold rounded mr-2 ${
                            flag.severity === '高' ? 'bg-red-100 text-red-800' :
                            flag.severity === '中' ? 'bg-orange-100 text-orange-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            深刻度: {flag.severity}
                          </span>
                          <div className="flex-1">
                            <p className="font-medium text-red-700">{flag.issue}</p>
                            {flag.description && <p className="text-sm text-gray-600 mt-1">{flag.description}</p>}
                            {flag.mitigation && (
                              <p className="text-sm text-green-600 mt-1">
                                <span className="font-medium">対策:</span> {flag.mitigation}
                              </p>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.risk_analysis.unclear_points && data.risk_analysis.unclear_points.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">不明確な点</h4>
                  <ul className="space-y-2">
                    {data.risk_analysis.unclear_points.map((point, idx) => (
                      <li key={idx} className="bg-yellow-50 p-3 rounded">
                        <p className="font-medium">{point.item}</p>
                        {point.impact && <p className="text-sm text-gray-600">影響: {point.impact}</p>}
                        {point.action_required && <p className="text-sm text-blue-600">必要なアクション: {point.action_required}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Bid Feasibility */}
      {data.bid_feasibility && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="入札可否判断" section="feasibility" />
          {expandedSections.feasibility && (
            <div className="p-4 space-y-4">
              {data.bid_feasibility.recommendation && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-semibold text-lg mb-2">推奨度: {data.bid_feasibility.recommendation.participate}</h4>
                  {data.bid_feasibility.recommendation.reasoning && (
                    <p className="text-gray-700 mb-2">{data.bid_feasibility.recommendation.reasoning}</p>
                  )}
                  {data.bid_feasibility.recommendation.conditions && data.bid_feasibility.recommendation.conditions.length > 0 && (
                    <div>
                      <p className="font-medium mb-1">前提条件:</p>
                      <ul className="list-disc list-inside text-sm text-gray-600">
                        {data.bid_feasibility.recommendation.conditions.map((condition, idx) => (
                          <li key={idx}>{condition}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.bid_feasibility.strengths && data.bid_feasibility.strengths.length > 0 && (
                  <div>
                    <h4 className="font-medium text-green-700 mb-2">強み・有利な点</h4>
                    <ul className="list-disc list-inside text-sm space-y-1">
                      {data.bid_feasibility.strengths.map((strength, idx) => (
                        <li key={idx} className="text-gray-700">{strength}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.bid_feasibility.weaknesses && data.bid_feasibility.weaknesses.length > 0 && (
                  <div>
                    <h4 className="font-medium text-red-700 mb-2">弱み・不利な点</h4>
                    <ul className="list-disc list-inside text-sm space-y-1">
                      {data.bid_feasibility.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="text-gray-700">{weakness}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                {data.bid_feasibility.preparation_time && (
                  <div className="bg-gray-50 p-3 rounded">
                    <p className="text-sm font-medium text-gray-500">準備期間</p>
                    <p className="text-lg font-semibold">{data.bid_feasibility.preparation_time}</p>
                  </div>
                )}
                {data.bid_feasibility.resource_requirements && (
                  <div className="bg-gray-50 p-3 rounded">
                    <p className="text-sm font-medium text-gray-500">必要リソース</p>
                    <p className="text-lg font-semibold">{data.bid_feasibility.resource_requirements}</p>
                  </div>
                )}
                {data.bid_feasibility.competition_level && (
                  <div className="bg-gray-50 p-3 rounded">
                    <p className="text-sm font-medium text-gray-500">競争レベル</p>
                    <p className="text-lg font-semibold">{data.bid_feasibility.competition_level}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Business Content */}
      {data.business_content && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="業務内容" section="business" />
          {expandedSections.business && (
            <div className="p-4 space-y-4">
              {data.business_content.overview && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">業務概要</h4>
                  <p className="text-sm text-gray-900">{data.business_content.overview}</p>
                </div>
              )}
              
              {data.business_content.detailed_content && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">詳細内容</h4>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{data.business_content.detailed_content}</p>
                </div>
              )}
              
              {data.business_content.scope_of_work && data.business_content.scope_of_work.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">作業範囲</h4>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    {data.business_content.scope_of_work.map((scope, idx) => (
                      <li key={idx}>{scope}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {data.business_content.deliverables && data.business_content.deliverables.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">成果物</h4>
                  <div className="space-y-2">
                    {data.business_content.deliverables.map((deliverable, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{deliverable.item}</p>
                        {deliverable.deadline && <p className="text-sm text-gray-600">納期: {deliverable.deadline}</p>}
                        {deliverable.format && <p className="text-sm text-gray-600">形式: {deliverable.format}</p>}
                        {deliverable.quantity && <p className="text-sm text-gray-600">数量: {deliverable.quantity}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {data.business_content.technical_requirements && data.business_content.technical_requirements.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">技術要件</h4>
                  <div className="space-y-2">
                    {data.business_content.technical_requirements.map((req, idx) => (
                      <div key={idx} className="border-l-4 border-blue-400 pl-3 py-1">
                        <p className="font-medium">{req.category}</p>
                        <p className="text-sm text-gray-600">{req.requirement}</p>
                        {req.priority && (
                          <span className={`inline-block mt-1 px-2 py-1 text-xs font-semibold rounded ${
                            req.priority === '必須' ? 'bg-red-100 text-red-800' :
                            req.priority === '推奨' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {req.priority}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {data.business_content.performance_location && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">履行場所</h4>
                  <p className="text-sm text-gray-900">{data.business_content.performance_location}</p>
                </div>
              )}
              
              {data.business_content.work_conditions && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">作業条件・制約事項</h4>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{data.business_content.work_conditions}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Financial Info */}
      {data.financial_info && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="財務情報" section="financial" />
          {expandedSections.financial && (
            <div className="p-4 space-y-4">
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.financial_info.budget_amount && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">予定価格</dt>
                    <dd className="mt-1 text-lg font-semibold">{formatCurrency(data.financial_info.budget_amount)}</dd>
                  </div>
                )}
                {data.financial_info.budget_disclosure && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">予定価格公表</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.financial_info.budget_disclosure}</dd>
                  </div>
                )}
              </dl>

              {data.financial_info.payment_terms && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">支払条件</h4>
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    {data.financial_info.payment_terms.method && <p>方法: {data.financial_info.payment_terms.method}</p>}
                    {data.financial_info.payment_terms.timing && <p>時期: {data.financial_info.payment_terms.timing}</p>}
                    {data.financial_info.payment_terms.conditions && <p>条件: {data.financial_info.payment_terms.conditions}</p>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Submission Requirements */}
      {data.submission_requirements && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="提出要件" section="submission" />
          {expandedSections.submission && (
            <div className="p-4 space-y-4">
              {data.submission_requirements.bid_documents && data.submission_requirements.bid_documents.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">提出書類</h4>
                  <div className="space-y-2">
                    {data.submission_requirements.bid_documents.map((doc, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{doc.document_name}</p>
                        <div className="text-sm text-gray-600 mt-1">
                          {doc.format && <p>形式: {doc.format}</p>}
                          {doc.copies && <p>必要部数: {doc.copies}</p>}
                          {doc.notes && <p>注意事項: {doc.notes}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {data.submission_requirements.technical_proposal && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">技術提案書</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    <p>必要: {data.submission_requirements.technical_proposal.required ? 'はい' : 'いいえ'}</p>
                    {data.submission_requirements.technical_proposal.page_limit && (
                      <p>ページ数制限: {data.submission_requirements.technical_proposal.page_limit}</p>
                    )}
                    {data.submission_requirements.technical_proposal.evaluation_items && data.submission_requirements.technical_proposal.evaluation_items.length > 0 && (
                      <div className="mt-2">
                        <p className="font-medium">評価項目:</p>
                        <ul className="list-disc list-inside text-sm">
                          {data.submission_requirements.technical_proposal.evaluation_items.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {data.submission_requirements.submission_method && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">提出方法</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    {data.submission_requirements.submission_method.options && data.submission_requirements.submission_method.options.length > 0 && (
                      <p>方法: {data.submission_requirements.submission_method.options.join(', ')}</p>
                    )}
                    {data.submission_requirements.submission_method.electronic_system && (
                      <p>電子入札システム: {data.submission_requirements.submission_method.electronic_system}</p>
                    )}
                    {data.submission_requirements.submission_method.notes && (
                      <p className="text-sm text-gray-600 mt-1">注意事項: {data.submission_requirements.submission_method.notes}</p>
                    )}
                  </div>
                </div>
              )}
              
              {data.submission_requirements.submission_location && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">提出場所</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    {data.submission_requirements.submission_location.address && (
                      <p>住所: {data.submission_requirements.submission_location.address}</p>
                    )}
                    {data.submission_requirements.submission_location.department && (
                      <p>担当部署: {data.submission_requirements.submission_location.department}</p>
                    )}
                    {data.submission_requirements.submission_location.reception_hours && (
                      <p>受付時間: {data.submission_requirements.submission_location.reception_hours}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Evaluation Criteria */}
      {data.evaluation_criteria && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="評価基準" section="evaluation" />
          {expandedSections.evaluation && (
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.evaluation_criteria.evaluation_method && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">落札者決定方式</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.evaluation_criteria.evaluation_method}</dd>
                  </div>
                )}
                {data.evaluation_criteria.price_weight && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">価格点配分</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.evaluation_criteria.price_weight}</dd>
                  </div>
                )}
                {data.evaluation_criteria.technical_weight && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">技術点配分</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.evaluation_criteria.technical_weight}</dd>
                  </div>
                )}
                {data.evaluation_criteria.minimum_technical_score && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">技術点最低基準</dt>
                    <dd className="mt-1 text-sm text-gray-900">{data.evaluation_criteria.minimum_technical_score}</dd>
                  </div>
                )}
              </div>
              
              {data.evaluation_criteria.evaluation_items && data.evaluation_criteria.evaluation_items.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">評価項目</h4>
                  <div className="space-y-2">
                    {data.evaluation_criteria.evaluation_items.map((item, idx) => (
                      <div key={idx} className="border rounded p-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <p className="font-medium">{item.category}</p>
                            <p className="text-sm text-gray-600">{item.item}</p>
                            {item.criteria && <p className="text-sm text-gray-500 mt-1">評価基準: {item.criteria}</p>}
                          </div>
                          {item.points && (
                            <span className="ml-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                              {item.points}点
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Special Conditions */}
      {data.special_conditions && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="特別条件" section="special" />
          {expandedSections.special && (
            <div className="p-4 space-y-4">
              {data.special_conditions.joint_venture && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">共同企業体（JV）</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    <p>参加可否: {data.special_conditions.joint_venture.allowed ? '可' : '不可'}</p>
                    {data.special_conditions.joint_venture.conditions && (
                      <p className="text-sm text-gray-600 mt-1">条件: {data.special_conditions.joint_venture.conditions}</p>
                    )}
                  </div>
                </div>
              )}
              
              {data.special_conditions.subcontracting && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">再委託</h4>
                  <div className="bg-gray-50 p-3 rounded">
                    <p>可否: {data.special_conditions.subcontracting.allowed ? '可' : '不可'}</p>
                    {data.special_conditions.subcontracting.restrictions && (
                      <p className="text-sm text-gray-600 mt-1">制限事項: {data.special_conditions.subcontracting.restrictions}</p>
                    )}
                  </div>
                </div>
              )}
              
              {data.special_conditions.confidentiality && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">機密保持</h4>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{data.special_conditions.confidentiality}</p>
                </div>
              )}
              
              {data.special_conditions.intellectual_property && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">知的財産権</h4>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{data.special_conditions.intellectual_property}</p>
                </div>
              )}
              
              {data.special_conditions.penalty_clauses && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">違約金・損害賠償</h4>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{data.special_conditions.penalty_clauses}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Contact Info */}
      {data.contact_info && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <SectionHeader title="連絡先情報" section="contact" />
          {expandedSections.contact && (
            <div className="p-4 space-y-4">
              {data.contact_info.contract_department && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">契約担当部署</h4>
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    {data.contact_info.contract_department.name && <p>部署: {data.contact_info.contract_department.name}</p>}
                    {data.contact_info.contract_department.person && <p>担当者: {data.contact_info.contract_department.person}</p>}
                    {data.contact_info.contract_department.phone && <p>電話: {data.contact_info.contract_department.phone}</p>}
                    {data.contact_info.contract_department.email && <p>Email: {data.contact_info.contract_department.email}</p>}
                    {data.contact_info.contract_department.hours && <p>対応時間: {data.contact_info.contract_department.hours}</p>}
                  </div>
                </div>
              )}
              {data.contact_info.technical_department && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">技術担当部署</h4>
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    {data.contact_info.technical_department.name && <p>部署: {data.contact_info.technical_department.name}</p>}
                    {data.contact_info.technical_department.person && <p>担当者: {data.contact_info.technical_department.person}</p>}
                    {data.contact_info.technical_department.phone && <p>電話: {data.contact_info.technical_department.phone}</p>}
                    {data.contact_info.technical_department.email && <p>Email: {data.contact_info.technical_department.email}</p>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LLMExtractedDataSection;