/**
 * Document viewer components for different file types
 *
 * Separated into individual components for better maintainability and testability
 */

import { FileText, Download, ExternalLink } from 'lucide-react';

interface DocumentViewerProps {
  fileHash: string;
  mimeType: string;
}

/**
 * Get human-readable document type name from MIME type
 */
const getDocumentTypeName = (mimeType: string): string => {
  if (mimeType.includes('word')) return 'Word Document';
  if (mimeType.includes('rtf')) return 'RTF Document';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'Spreadsheet';
  return 'Document';
};

/**
 * Viewer for files that cannot be displayed inline (Word, Excel, RTF)
 * Shows download prompt instead
 */
export const DownloadOnlyViewer: React.FC<DocumentViewerProps> = ({ fileHash, mimeType }) => {
  const documentType = getDocumentTypeName(mimeType);

  return (
    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
      <FileText className="h-12 w-12 mb-4 opacity-50" />
      <p className="text-lg font-medium mb-2">{documentType}</p>
      <p className="text-sm mb-4">This file type cannot be displayed in the browser</p>
      <a
        href={`http://localhost:8000/api/vault/file/${fileHash}`}
        download
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center"
      >
        <Download className="h-4 w-4 mr-2" />
        Download Original File
      </a>
    </div>
  );
};

/**
 * PDF viewer using object tag with fallback
 */
export const PDFViewer: React.FC<DocumentViewerProps & { timestamp: number }> = ({
  fileHash,
  timestamp,
}) => {
  const fileUrl = `http://localhost:8000/api/vault/file/${fileHash}?t=${timestamp}`;

  return (
    <object
      data={fileUrl}
      type="application/pdf"
      className="w-full h-full"
      aria-label="PDF Document"
    >
      {/* Fallback content if PDF cannot be displayed */}
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <FileText className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-lg font-medium mb-2">PDF Preview Not Available</p>
        <p className="text-sm mb-4">Your browser may not support inline PDF viewing</p>
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline flex items-center"
        >
          Open PDF in new tab
          <ExternalLink className="h-3 w-3 ml-1" />
        </a>
      </div>
    </object>
  );
};

/**
 * Generic iframe viewer for images and text files
 */
export const IFrameViewer: React.FC<DocumentViewerProps> = ({ fileHash }) => {
  return (
    <iframe
      src={`http://localhost:8000/api/vault/file/${fileHash}`}
      className="w-full h-full border-0"
      title="Original Document"
    />
  );
};

/**
 * Main document viewer that selects appropriate viewer based on file type
 */
export const DocumentViewer: React.FC<
  DocumentViewerProps & {
    willDownload: boolean;
    pdfTimestamp: number;
  }
> = ({ fileHash, mimeType, willDownload, pdfTimestamp }) => {
  // Select appropriate viewer based on file type
  if (willDownload) {
    return <DownloadOnlyViewer fileHash={fileHash} mimeType={mimeType} />;
  }

  if (mimeType.includes('pdf')) {
    return <PDFViewer fileHash={fileHash} mimeType={mimeType} timestamp={pdfTimestamp} />;
  }

  // Default: iframe for images and text files
  return <IFrameViewer fileHash={fileHash} mimeType={mimeType} />;
};
