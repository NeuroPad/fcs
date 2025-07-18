import './KnowledgeBaseManagement.css';
import {
  IonPage,
  IonContent,
  IonButton,
  IonIcon,
  IonModal,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonButtons,
  IonToast,
  IonSpinner,
  IonGrid,
  IonRow,
  IonCol,
  IonCard,
  IonCardHeader,
  IonCardTitle,
  IonCardContent,
  IonRefresher,
  IonRefresherContent,
  IonProgressBar,
  IonSegment,
  IonSegmentButton,
  IonLabel,
} from '@ionic/react';
import React, { useEffect, useState, useRef } from 'react';
import DataTable from 'react-data-table-component';
import {
  trash, 
  eye, 
  cloudUpload, 
  close, 
  book, 
  refreshCircle,
  analyticsOutline,
  list,
  hourglassOutline,
  warningOutline,
  nuclear,
  checkmarkCircle,
  timeOutline,
  alertCircle,
  syncOutline,
  documentOutline,
  closeCircle
} from 'ionicons/icons';
import axios from 'axios';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  fetchDocuments,
  uploadDocument,
  processDocument,
  indexDocument,
  deleteDocument,
  processPendingDocuments
} from '../../features/documentSlice';
import { API_BASE_URL } from '../../api/config';
import { get } from "../../services/storage";
import { Document, DocumentState } from '../../types/document';
import GraphView from './GraphView';
import TableView from './TableView';

// Import React FilePond
import { FilePond, registerPlugin } from 'react-filepond';

// Import FilePond styles
import 'filepond/dist/filepond.min.css';

// Import the Image EXIF Orientation and Image Preview plugins
import FilePondPluginImageExifOrientation from "filepond-plugin-image-exif-orientation";
import FilePondPluginImagePreview from "filepond-plugin-image-preview";
import "filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css";
import { api } from '../../config/axiosConfig';

// Register the plugins
registerPlugin(FilePondPluginImageExifOrientation, FilePondPluginImagePreview);

// Create a wrapper component to fix TypeScript issues
const FilePondComponent = FilePond as any;

// Interfaces
interface GraphStats {
  totalNodes: number;
  totalRelationships: number;
  totalDocuments: number;
  averageRelationsPerNode: number;
  lastIndexed: string;
}

interface RelationshipData {
  id: string;
  sourceNode: string;
  relationship: string;
  targetNode: string;
  confidence: number;
  lastUpdated: string;
}

interface ProcessingStatus {
  status: string;
  message: string;
  progress: number;
  processed_documents: number;
  total_documents: number;
}

interface DocumentCount {
  total: number;
  processed: number;
  pending: number;
  indexed: number;
}

// Define utility functions inline since fileUtils module is missing
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getStatusClass = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'status-completed';
    case 'processing':
      return 'status-processing';
    case 'pending':
      return 'status-pending';
    case 'uploaded':
      return 'status-uploaded';
    case 'failed':
      return 'status-failed';
    case 'error':
      return 'status-error';
    default:
      return 'status-default';
  }
};

const getStatusIcon = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'completed':
      return checkmarkCircle;
    case 'processing':
      return syncOutline;
    case 'pending':
      return timeOutline;
    case 'uploaded':
      return documentOutline;
    case 'failed':
    case 'error':
      return closeCircle;
    default:
      return alertCircle;
  }
};

const getIndexedStatusClass = (isIndexed: boolean): string => {
  return isIndexed ? 'status-indexed' : 'status-not-indexed';
};

const getIndexedStatusIcon = (isIndexed: boolean): string => {
  return isIndexed ? checkmarkCircle : timeOutline;
};

const KnowledgeBaseManagement: React.FC = () => {
  const dispatch = useAppDispatch();
  const { documents, isLoading, error } = useAppSelector((state) => state.documents);
  
  // Document Management States
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isProcessingPending, setIsProcessingPending] = useState(false);
  const [isMultimodalIndexing, setIsMultimodalIndexing] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const pondRef = useRef<any>(null);
  
  // Knowledge Base States
  const [isReindexing, setIsReindexing] = useState(false);
  const [graphStats, setGraphStats] = useState<GraphStats>({
    totalNodes: 0,
    totalRelationships: 0,
    totalDocuments: 0,
    averageRelationsPerNode: 0,
    lastIndexed: '',
  });
  const [relationships, setRelationships] = useState<RelationshipData[]>([]);
  const [selectedSegment, setSelectedSegment] = useState<string>('documents');
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    status: 'idle',
    message: '',
    progress: 0,
    processed_documents: 0,
    total_documents: 0,
  });
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  // Clear Memory States
  const [isClearingMemory, setIsClearingMemory] = useState(false);
  
  // Document Count State
  const [documentCount, setDocumentCount] = useState<DocumentCount>({
    total: 0,
    processed: 0,
    pending: 0,
    indexed: 0
  });
  
  // Real-time polling state
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  // WebSocket state for real-time updates
  const [documentWs, setDocumentWs] = useState<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    // Fetch documents
    dispatch(fetchDocuments());
    
    // Fetch knowledge base data
    fetchGraphStats();
    fetchRelationships();
    fetchDocumentCount();
    
    // Establish WebSocket connection for real-time document updates
    connectDocumentWebSocket();
    
    return () => {
      if (ws) {
        ws.close();
      }
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      if (documentWs) {
        documentWs.close();
      }
    };
  }, [dispatch]);
  
  const connectDocumentWebSocket = async () => {
    try {
      const token = await get("token");
      if (!token) return;
      
      const wsUrl = `ws://${API_BASE_URL.replace('http://', '')}/documents/ws/status?token=${token}`;
      const websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log('Document WebSocket connected');
        setWsConnected(true);
        setDocumentWs(websocket);
      };
      
      websocket.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          if (update.type === 'document_status_update') {
            // Refresh documents to get the latest status
            dispatch(fetchDocuments());
            fetchDocumentCount();
            
            // Show toast notification
            setToastMessage(`${update.filename}: ${update.message || update.status}`);
            setShowToast(true);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      websocket.onclose = () => {
        console.log('Document WebSocket disconnected');
        setWsConnected(false);
        setDocumentWs(null);
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (!documentWs) {
            connectDocumentWebSocket();
          }
        }, 5000);
      };
      
      websocket.onerror = (error) => {
        console.error('Document WebSocket error:', error);
        setWsConnected(false);
      };
      
    } catch (error) {
      console.error('Error connecting to document WebSocket:', error);
    }
  };
  
  // Start polling when there are processing documents (fallback if WebSocket fails)
  useEffect(() => {
    const hasProcessingDocuments = documents.some(doc => 
      doc.status === 'processing' || doc.status === 'pending' || doc.status === 'uploaded'
    );
    
    // Only use polling as fallback if WebSocket is not connected
    if (hasProcessingDocuments && !isPolling && !wsConnected) {
      startPolling();
    } else if ((!hasProcessingDocuments || wsConnected) && isPolling) {
      stopPolling();
    }
  }, [documents, isPolling, wsConnected]);
  
  const startPolling = () => {
    if (pollingInterval) return; // Already polling
    
    setIsPolling(true);
    const interval = setInterval(() => {
      dispatch(fetchDocuments());
      fetchDocumentCount();
    }, 5000); // Poll every 5 seconds (less aggressive when used as fallback)
    
    setPollingInterval(interval);
  };
  
  const stopPolling = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    setIsPolling(false);
  };

  // Document Management Functions
  const handleProcessDocuments = async (id: number) => {
    try {
      setIsProcessing(true);
      setToastMessage('Document processing started');
      setShowToast(true);
      await dispatch(processDocument(id)).unwrap();
      setToastMessage('Documents processed successfully');
      setShowToast(true);
      await dispatch(fetchDocuments()).unwrap();
      await fetchDocumentCount();
    } catch (error) {
      setToastMessage('Error processing documents');
      setShowToast(true);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleProcessPendingDocuments = async () => {
    try {
      setIsProcessingPending(true);
      setToastMessage('Processing pending documents started');
      setShowToast(true);
      
      const token = await get("token");
      const response = await fetch(`${API_BASE_URL}/rag/process-pending`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to process pending documents');
      }

      const result = await response.json();
      setToastMessage(result.message || 'Pending documents processed successfully');
      setShowToast(true);
      
      await dispatch(fetchDocuments()).unwrap();
      await fetchDocumentCount();
    } catch (error) {
      setToastMessage('Error processing pending documents');
      setShowToast(true);
    } finally {
      setIsProcessingPending(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await dispatch(deleteDocument(id)).unwrap();
      setToastMessage('File deleted successfully');
      setShowToast(true);
      await dispatch(fetchDocuments()).unwrap();
      await fetchDocumentCount();
    } catch (error) {
      setToastMessage('Error deleting file');
      setShowToast(true);
    }
  };

  const handleView = (filename: string) => {
    window.open(`${API_BASE_URL}/files/file/${filename}`, '_blank');
  };

  // Knowledge Base Functions
  const fetchGraphStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rag/graph/stats`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await get("token")}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch graph statistics');
      }

      const data = await response.json();
      setGraphStats(data);
    } catch (error) {
      console.error('Error fetching graph stats:', error);
      setToastMessage('Failed to fetch graph statistics');
      setShowToast(true);
      setGraphStats({
        totalNodes: 0,
        totalRelationships: 0,
        totalDocuments: 0,
        averageRelationsPerNode: 0,
        lastIndexed: 'Not available',
      });
    }
  };

  const fetchRelationships = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rag/graph/relationships`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await get("token")}`
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch relationships');
      }

      const data = await response.json();
      setRelationships(data);
    } catch (error) {
      console.error('Error fetching relationships:', error);
      setToastMessage('Failed to fetch relationships');
      setShowToast(true);
      setRelationships([]);
    }
  };

  const fetchDocumentCount = async () => {
    try {
      const token = await get("token");
      const response = await fetch(`${API_BASE_URL}/documents/count`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch document count');
      }

      const data = await response.json();
      setDocumentCount(data);
    } catch (error) {
      console.error('Error fetching document count:', error);
      setDocumentCount({
        total: 0,
        processed: 0,
        pending: 0,
        indexed: 0
      });
    }
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setToastMessage('Knowledge Graph creation started...');
    setShowToast(true);

    try {
      const response = await fetch(`${API_BASE_URL}/rag/graph/process-documents`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to trigger KG creation');
      }

      const websocket = new WebSocket(`ws://${API_BASE_URL.replace('http://', '')}/rag/graph/ws/process-documents`);

      websocket.onmessage = (event) => {
        const status: ProcessingStatus = JSON.parse(event.data);
        setProcessingStatus(status);

        setToastMessage(`${status.message} (${status.progress.toFixed(0)}%)`);
        setShowToast(true);

        if (status.status === 'completed' || status.status === 'error') {
          setIsReindexing(false);
          websocket.close();
          Promise.all([fetchGraphStats(), fetchRelationships()]);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setToastMessage('Error in processing connection');
        setShowToast(true);
        setIsReindexing(false);
      };

      websocket.onclose = () => {
        setWs(null);
      };

      setWs(websocket);

    } catch (error) {
      console.error('Error during KG creation:', error);
      setToastMessage(error instanceof Error ? error.message : 'Error during KG creation');
      setShowToast(true);
      setIsReindexing(false);
    }
  };

  // Clear Memory Function
  const handleClearMemory = async () => {
    try {
      setIsClearingMemory(true);
      setToastMessage('Clearing memory...');
      setShowToast(true);
      
      const token = await get("token");
      const response = await fetch(`${API_BASE_URL}/memory/memory/clear-neo4j`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to clear memory');
      }

      const result = await response.json();
      setToastMessage(result.message || 'Memory cleared successfully');
      setShowToast(true);
      
      // Refresh stats after clearing
      await Promise.all([fetchGraphStats(), fetchRelationships()]);
      
    } catch (error) {
      console.error('Error clearing memory:', error);
      setToastMessage('Error clearing memory');
      setShowToast(true);
    } finally {
      setIsClearingMemory(false);
    }
  };

  const handleRefresh = (event: CustomEvent) => {
    Promise.all([
      dispatch(fetchDocuments()),
      fetchGraphStats(), 
      fetchRelationships(),
      fetchDocumentCount()
    ]).then(() => {
      event.detail.complete();
    });
  };

  const handleSegmentChange = (e: CustomEvent) => {
    setSelectedSegment(e.detail.value ?? 'documents');
  };

  // Document table helper functions
  const formatDate = (dateString: string): string => {
    const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  // Removed duplicate function - now defined earlier in the file

  // Document table columns
  const columns = [
    {
      name: 'Filename',
      selector: (row: Document) => row.filename,
      sortable: true,
    },
    {
      name: 'Type',
      selector: (row: Document) => row.type,
      sortable: true,
    },
    {
      name: 'Upload Date',
      selector: (row: Document) => formatDate(row.created_at),
      sortable: true,
    },
    {
      name: 'Size',
      selector: (row: Document) => formatFileSize(row.file_size),
      sortable: true,
    },
    {
      name: 'Status',
      selector: (row: Document) => row.status,
      cell: (row: Document) => (
        <div className={`status-badge ${getStatusClass(row.status)}`}>
          <IonIcon icon={getStatusIcon(row.status)} className="status-icon" />
          {row.status}
        </div>
      ),
      sortable: true,
    },
    {
      name: 'Indexed',
      selector: (row: Document) => row.is_indexed,
      cell: (row: Document) => (
        <div className={`status-badge ${getIndexedStatusClass(row.is_indexed)}`}>
          <IonIcon icon={getIndexedStatusIcon(row.is_indexed)} className="status-icon" />
          {row.is_indexed ? 'Yes' : 'No'}
        </div>
      ),
      sortable: true,
    },
    {
      name: 'Actions',
      cell: (row: Document) => (
        <div className="action-buttons">
          <IonButton
            fill="clear"
            size="small"
            onClick={() => handleView(row.filename)}
          >
            <IonIcon icon={eye} />
          </IonButton>
          <IonButton
            fill="clear"
            size="small"
            color="danger"
            onClick={() => handleDelete(row.id)}
          >
            <IonIcon icon={trash} />
          </IonButton>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

  return (
    <IonPage>
      <Header title="Knowledge Base Management" />
      <IonContent>
        <Container>
          <IonRefresher slot="fixed" onIonRefresh={handleRefresh}>
            <IonRefresherContent></IonRefresherContent>
          </IonRefresher>

          <div className="knowledge-base-container">
            {/* Stats Cards */}
            <IonGrid>
              <IonRow>
                <IonCol size="12" sizeMd="3">
                  <IonCard className="stat-card">
                    <IonCardContent>
                      <div className="stat-value">{documentCount.total}</div>
                      <div className="stat-label">Total Documents</div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="12" sizeMd="3">
                  <IonCard className="stat-card">
                    <IonCardContent>
                      <div className="stat-value">{documentCount.indexed}</div>
                      <div className="stat-label">Indexed Documents</div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="12" sizeMd="3">
                  <IonCard className="stat-card">
                    <IonCardContent>
                      <div className="stat-value">{graphStats.totalNodes}</div>
                      <div className="stat-label">Knowledge Nodes</div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="12" sizeMd="3">
                  <IonCard className="stat-card">
                    <IonCardContent>
                      <div className="stat-value">{graphStats.totalRelationships}</div>
                      <div className="stat-label">Relationships</div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
              </IonRow>
            </IonGrid>

            {/* Connection Status Indicator */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px', gap: '8px' }}>
              <IonIcon 
                icon={wsConnected ? checkmarkCircle : (isPolling ? syncOutline : alertCircle)} 
                color={wsConnected ? 'success' : (isPolling ? 'warning' : 'medium')}
              />
              <span style={{ fontSize: '0.9em', color: 'var(--ion-color-medium)' }}>
                {wsConnected ? 'Real-time updates active' : (isPolling ? 'Polling for updates' : 'Updates paused')}
              </span>
            </div>

            {/* Action Buttons */}
            <div className="document-actions">
              <IonButton onClick={() => setShowUploadModal(true)}>
                <IonIcon icon={cloudUpload} slot="start" />
                Upload Documents
              </IonButton>
              {/* Commented out manual processing buttons - now using unified upload flow */}
              {/* <IonButton onClick={() => handleProcessDocuments(documents[0]?.id)}>
                {isProcessing ? <IonSpinner name="crescent" /> : <IonIcon icon={book} slot="start" />}
                Process Documents
              </IonButton>
              <IonButton onClick={handleProcessPendingDocuments}>
                {isProcessingPending ? <IonSpinner name="crescent" /> : <IonIcon icon={book} slot="start" />}
                Index Pending Documents
              </IonButton>
              <IonButton
                color="secondary"
                onClick={handleReindex}
                disabled={isReindexing}
              >
                {isReindexing ? <IonSpinner name="crescent" /> : <IonIcon icon={refreshCircle} slot="start" />}
                Rebuild Knowledge Graph
              </IonButton> */}
              <IonButton
                color="danger"
                onClick={handleClearMemory}
                disabled={isClearingMemory}
              >
                {isClearingMemory ? <IonSpinner name="crescent" /> : <IonIcon icon={nuclear} slot="start" />}
                Clear Memory
              </IonButton>
            </div>

            {/* Indexing Progress */}
            {isReindexing && (
              <IonCard className="reindex-card">
                <IonCardContent>
                  <div className="indexing-status">
                    <IonProgressBar value={processingStatus.progress / 100}></IonProgressBar>
                    <p>
                      <IonIcon icon={hourglassOutline} />
                      {processingStatus.message || 'Processing documents...'}
                      ({processingStatus.processed_documents}/{processingStatus.total_documents})
                    </p>
                  </div>
                </IonCardContent>
              </IonCard>
            )}

            {/* Segment for switching between views */}
            <IonSegment value={selectedSegment} onIonChange={handleSegmentChange}>
              <IonSegmentButton value="documents">
                <IonLabel>Documents</IonLabel>
              </IonSegmentButton>
              <IonSegmentButton value="graph">
                <IonLabel>Graph View</IonLabel>
              </IonSegmentButton>
              <IonSegmentButton value="table">
                <IonLabel>Relations Table</IonLabel>
              </IonSegmentButton>
            </IonSegment>

            <div style={{ marginTop: 16 }}>
              {selectedSegment === 'documents' && (
                <div className="document-table">
                  <DataTable
                    columns={columns}
                    data={documents}
                    pagination
                    highlightOnHover
                    responsive
                    striped
                    noDataComponent="No documents found"
                  />
                </div>
              )}
              {selectedSegment === 'graph' && (
                <GraphView relationships={relationships} />
              )}
              {selectedSegment === 'table' && (
                <TableView relationships={relationships} />
              )}
            </div>
          </div>

          {/* Upload Modal */}
          <IonModal
            isOpen={showUploadModal}
            onDidDismiss={() => setShowUploadModal(false)}
          >
            <IonHeader>
              <IonToolbar>
                <IonTitle>Upload Document</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setShowUploadModal(false)}>
                    <IonIcon icon={close} />
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent className="ion-padding">
              <div className="upload-modal-content">
                <FilePondComponent
                  ref={pondRef}
                  files={files}
                  onupdatefiles={setFiles}
                  allowMultiple={true}
                  allowReorder={true}
                  maxFiles={10}
                  credits={false}
                  instantUpload={true}
                  labelIdle='Drag & Drop your files or <span class="filepond--label-action">Browse</span><br/><small>Accepted files: PDF, Markdown, JSON, Text, Word (.doc, .docx)</small>'
                  labelFileProcessing="Uploading"
                  labelFileProcessingComplete="Upload complete"
                  labelFileProcessingAborted="Upload cancelled"
                  labelFileProcessingError="Error during upload"
                  labelTapToCancel="tap to cancel"
                  labelTapToRetry="tap to retry"
                  labelTapToUndo="tap to undo"
                  styleProgressIndicatorPosition="right"
                  styleButtonRemoveItemPosition="right"
                  styleButtonProcessItemPosition="right"
                  styleItemPanelAspectRatio={1}
                  stylePanelAspectRatio={0.5}
                  server={{
                    process: (fieldName: any, file: any, metadata: any, load: any, error: any, progress: any, abort: any) => {
                      const formData = new FormData();
                      formData.append('files', file, file.name);
                      
                      const uploadInstance = axios.create({
                        baseURL: API_BASE_URL,
                        timeout: 100000,
                        headers: {
                          'Accept': 'application/json',
                        }
                      });
                      
                      get("token").then(token => {
                        if (token) {
                          uploadInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                        }
                        
                         uploadInstance.post(`/documents/upload`, formData, {
                           onUploadProgress: (e:any) => {
                             progress(e.lengthComputable, e.loaded, e.total);
                           },
                         })
                         .then(response => {
                           load(JSON.stringify(response.data));
                           console.log('Upload successful:', response.data);
                           dispatch(fetchDocuments());
                           fetchDocumentCount();
                         })
                         .catch(err => {
                           error(err.response?.data?.detail || 'Upload failed');
                           console.error('Upload failed:', err);
                           setToastMessage('File upload failed');
                           setShowToast(true);
                         });
                       }).catch(err => {
                         console.error('Error getting token:', err);
                         error('Authentication error');
                       });

                      return {
                        abort: () => {
                          abort();
                        }
                      };
                    },
                  }}
                  acceptedFileTypes={[
                    'application/pdf',
                    'text/markdown',
                    'application/json',
                    'text/plain',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/msword'
                  ]}
                />
              </div>
            </IonContent>
          </IonModal>
        </Container>
      </IonContent>

      <IonToast
        isOpen={showToast}
        onDidDismiss={() => setShowToast(false)}
        message={toastMessage}
        duration={3000}
        position="bottom"
      />
    </IonPage>
  );
};

export default KnowledgeBaseManagement;
