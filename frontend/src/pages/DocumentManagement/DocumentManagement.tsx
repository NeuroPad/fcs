import './DocumentManagement.css';
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
  IonCol
} from '@ionic/react';
import React, { useEffect, useState, useRef } from 'react';
import DataTable from 'react-data-table-component';
import { trash, eye, cloudUpload, close, book, images } from 'ionicons/icons';
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
    case 'processed':
      return 'status-processed';
    case 'pending':
      return 'status-pending';
    case 'failed':
      return 'status-failed';
    default:
      return 'status-default';
  }
};


const DocumentManagement: React.FC = () => {
  const dispatch = useAppDispatch();
  const { documents, isLoading, error } = useAppSelector((state) => state.documents);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isProcessingPending, setIsProcessingPending] = useState(false);
  const [isMultimodalIndexing, setIsMultimodalIndexing] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const pondRef = useRef<any>(null);

  useEffect(() => {
    // This now correctly calls the Redux thunk
    dispatch(fetchDocuments());
  }, [dispatch]);

  const handleProcessDocuments = async (id: number) => {
    try {
      setIsProcessing(true);
      setToastMessage('Document processing started');
      setShowToast(true);
      await dispatch(processDocument(id)).unwrap();
      setToastMessage('Documents processed successfully');
      setShowToast(true);
      // This now correctly calls the Redux thunk
      await dispatch(fetchDocuments()).unwrap();
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
      await dispatch(processPendingDocuments()).unwrap();
      setToastMessage('Pending documents processed successfully');
      setShowToast(true);
      // This now correctly calls the Redux thunk
      await dispatch(fetchDocuments()).unwrap();
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
      // This now correctly calls the Redux thunk
      await dispatch(fetchDocuments()).unwrap();
    } catch (error) {
      setToastMessage('Error deleting file');
      setShowToast(true);
    }
  };

  // Helper function to format date
  const formatDate = (dateString: string): string => {
    const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  // Helper function to get indexed status class
  const getIndexedStatusClass = (isIndexed: boolean): string => {
    return isIndexed ? 'status-processed' : 'status-pending';
  };

  // Update the columns definition
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

  const handleView = (filename: string) => {
    // Use the correct endpoint path that matches the FastAPI route
    window.open(`${API_BASE_URL}/files/file/${filename}`, '_blank');
  };


  return (
    <IonPage>
      <Header title="Document Management" />
      <IonContent>
        <Container>
          <div className="document-management-container">
            <div className="document-actions">
              <IonButton onClick={() => setShowUploadModal(true)}>
                <IonIcon icon={cloudUpload} slot="start" />
                Upload Documents
              </IonButton>
              <IonButton onClick={() => handleProcessDocuments(documents[0]?.id)}>
                {isProcessing ? <IonSpinner name="crescent" /> : <IonIcon icon={book} slot="start" />}
                Process Documents
              </IonButton>
              <IonButton onClick={handleProcessPendingDocuments}>
                {isProcessingPending ? <IonSpinner name="crescent" /> : <IonIcon icon={book} slot="start" />}
                Index Pending Documents
              </IonButton>
            </div>

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
          </div>

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
                      // The FastAPI endpoint expects a list of files with parameter name 'files'
                      // We need to append the file with the correct field name
                      formData.append('files', file, file.name);
                      
                      // Set the correct Content-Type header (let the browser set it with the boundary)
                      // Create a custom axios instance without the default Content-Type header
                      // This allows the browser to set the correct multipart/form-data boundary
                      const uploadInstance = axios.create({
                        baseURL: API_BASE_URL,
                        timeout: 100000,
                        headers: {
                          'Accept': 'application/json',
                        }
                      });
                      
                      // Add authorization header if needed
                      get("token").then(token => {
                        if (token) {
                          uploadInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                        }
                        
                        // Use this instance for the upload
                         uploadInstance.post(`/documents/upload`, formData, {
                           onUploadProgress: (e:any) => {
                             progress(e.lengthComputable, e.loaded, e.total);
                           },
                         })
                         .then(response => {
                           load(JSON.stringify(response.data)); // FilePond expects a string response
                           // Handle successful upload response
                           console.log('Upload successful:', response.data);
                           // Dispatch fetchDocuments to update the list after successful upload
                           dispatch(fetchDocuments());
                         })
                         .catch(err => {
                           error(err.response?.data?.detail || 'Upload failed'); // FilePond expects an error string
                           // Handle upload error
                           console.error('Upload failed:', err);
                           setToastMessage('File upload failed');
                           setShowToast(true);
                         });
                       }).catch(err => {
                         console.error('Error getting token:', err);
                         error('Authentication error');
                       });

                      return { // Return object with abort method
                        abort: () => {
                          // Cancel the axios request if needed
                          // This requires implementing cancellation logic in axios
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

export default DocumentManagement;