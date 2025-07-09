import React from 'react';
import { 
  DocumentTextIcon, 
  DocumentIcon,
  FolderIcon,
  ArrowDownTrayIcon 
} from '@heroicons/react/24/outline';

interface Document {
  name: string;
  type: string;
  url: string;
  index: number;
}

interface DocumentsSectionProps {
  documents?: Document[];
  documentCount?: number;
  downloadedCount?: number;
  documentDirectory?: string;
}

const DocumentsSection: React.FC<DocumentsSectionProps> = ({ 
  documents = [], 
  documentCount = 0,
  downloadedCount = 0,
  documentDirectory 
}) => {
  if (documentCount === 0) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center text-gray-500">
          <FolderIcon className="h-5 w-5 mr-2" />
          <span>文書情報なし</span>
        </div>
      </div>
    );
  }

  const getDocumentIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <DocumentTextIcon className="h-5 w-5 text-red-500" />;
      case 'doc':
      case 'docx':
        return <DocumentIcon className="h-5 w-5 text-blue-500" />;
      case 'xls':
      case 'xlsx':
        return <DocumentIcon className="h-5 w-5 text-green-500" />;
      case 'html':
        return <DocumentIcon className="h-5 w-5 text-purple-500" />;
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const isExternalUrl = (url: string) => {
    return url.includes('tokyo.lg.jp') || 
           url.includes('e-gunma.lg.jp') || 
           url.includes('e-kanagawa.jp');
  };

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <FolderIcon className="h-5 w-5 mr-2" />
          文書情報
        </h3>
        <div className="text-sm text-gray-500">
          {downloadedCount} / {documentCount} ダウンロード済み
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        {/* Document stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-white rounded p-3 text-center">
            <div className="text-2xl font-semibold text-blue-600">
              {documentCount}
            </div>
            <div className="text-xs text-gray-500">文書数</div>
          </div>
          <div className="bg-white rounded p-3 text-center">
            <div className="text-2xl font-semibold text-green-600">
              {downloadedCount}
            </div>
            <div className="text-xs text-gray-500">ダウンロード済み</div>
          </div>
          <div className="bg-white rounded p-3 text-center">
            <div className="text-2xl font-semibold text-gray-600">
              {Math.round((downloadedCount / documentCount) * 100)}%
            </div>
            <div className="text-xs text-gray-500">完了率</div>
          </div>
        </div>

        {/* Document list */}
        {documents.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 mb-2">文書一覧</h4>
            {documents.map((doc, idx) => (
              <div 
                key={idx} 
                className="flex items-center justify-between bg-white rounded p-2 hover:bg-gray-50"
              >
                <div className="flex items-center flex-1">
                  {getDocumentIcon(doc.type)}
                  <span className="ml-2 text-sm text-gray-700 truncate">
                    {doc.name}
                  </span>
                  {isExternalUrl(doc.url) && (
                    <span className="ml-2 text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
                      外部システム
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500 uppercase">
                    {doc.type}
                  </span>
                  {!isExternalUrl(doc.url) && (
                    <ArrowDownTrayIcon className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Directory info */}
        {documentDirectory && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="text-xs text-gray-500">
              保存先: {documentDirectory}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentsSection;