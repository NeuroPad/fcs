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
import { API_BASE_URL } from '../../api/config';

// Import React FilePond
import { FilePond, registerPlugin } from 'react-filepond';

// Import FilePond styles
import 'filepond/dist/filepond.min.css';

// Import the Image EXIF Orientation and Image Preview plugins
import FilePondPluginImageExifOrientation from "filepond-plugin-image-exif-orientation";
import FilePondPluginImagePreview from "filepond-plugin-image-preview";
import "filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css";

// Register the plugins
registerPlugin(FilePondPluginImageExifOrientation, FilePondPluginImagePreview);

// Create a wrapper component to fix TypeScript issues
const FilePondComponent = FilePond as any;

interface Document {
  filename: string;
  uploadDate: string;
  size: number;
  isProcessed: boolean;
  imagesIndexed: boolean;
  knowledgeBaseIndexed: boolean;
  status: string;
  path: string;
  type: string;
}

const DocumentManagement: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [isMultimodalIndexing, setIsMultimodalIndexing] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const pondRef = useRef<any>(null);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/files/files`);
      if (response.data.status === 'success') {
        setDocuments(response.data.files);
      }
    } catch (error) {
      showError('Error fetching documents');
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleProcessDocuments = async () => {
    try {
      setIsProcessing(true);
      showSuccess('Document processing started');
      await axios.post(`${API_BASE_URL}/files/process-pdfs-to-markdown`);
      showSuccess('Documents processed successfully');
      fetchDocuments();
    } catch (error) {
      showError('Error processing documents');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleIndexImages = async () => {
    try {
      setIsIndexing(true);
      showSuccess('Image indexing started');
      await axios.post(`${API_BASE_URL}/graph-rag/index-markdown-images`);
      showSuccess('Images indexed successfully');
      fetchDocuments();
    } catch (error) {
      showError('Error indexing images');
    } finally {
      setIsIndexing(false);
    }
  };

  const handleMultimodalIndex = async () => {
    try {
      setIsMultimodalIndexing(true);
      showSuccess('Multimodal indexing started');
      await axios.post(`${API_BASE_URL}/multimodal-rag/index-documents`);
      showSuccess('Multimodal indexing completed successfully');
      fetchDocuments();
    } catch (error) {
      showError('Error during multimodal indexing');
    } finally {
      setIsMultimodalIndexing(false);
    }
  };

  const showSuccess = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
  };

  const showError = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusClass = (status: string): string => {
    console.log("status: ", status);
    switch (status.toLowerCase()) {
      case 'image indexed':
        return 'imageindexed';
      case 'processed':
        return 'processed';
      default:
        return 'pending';
    }
  };

  const columns = [
    {
      name: 'Filename',
      selector: (row: Document) => row.filename,
      sortable: true,
    },
    {
      name: 'Upload Date',
      selector: (row: Document) => row.uploadDate,
      sortable: true,
    },
    {
      name: 'Size',
      selector: (row: Document) => formatFileSize(row.size),
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
            onClick={() => handleDelete(row.filename)}
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

  const handleDelete = async (filename: string) => {
    try {
      await axios.delete(`${API_BASE_URL}/files/file/${filename}`);
      showSuccess('File deleted successfully');
      fetchDocuments();
    } catch (error) {
      showError('Error deleting file');
    }
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
              <IonButton onClick={handleProcessDocuments} disabled={isProcessing}>
                {isProcessing ? <IonSpinner name="crescent" /> : <IonIcon icon={book} slot="start" />}
                Process Documents
              </IonButton>
              <IonButton onClick={handleIndexImages} disabled={isIndexing}>
                {isIndexing ? <IonSpinner name="crescent" /> : <IonIcon icon={images} slot="start" />}
                Index Images
              </IonButton>
              <IonButton onClick={handleMultimodalIndex} disabled={isMultimodalIndexing}>
                {isMultimodalIndexing ? <IonSpinner name="crescent" /> : <IonIcon icon={images} slot="start" />}
                Multimodal Index
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
                    process: (
                      fieldName: string,
                      file: File,
                      metadata: any,
                      load: (responseText: string) => void,
                      error: (errorText: string) => void,
                      progress: (isComputable: boolean, loaded: number, total: number) => void,
                      abort: () => void,
                      transfer: (transferredFile: any) => void,
                      options: any
                    ) => {
                      // Create FormData
                      const formData = new FormData();
                      formData.append('files', file, file.name);
                      
                      // Create request
                      const request = new XMLHttpRequest();
                      request.open('POST', `${API_BASE_URL}/files/upload-files`);
                      
                      // Handle response
                      request.onload = function() {
                        if (request.status >= 200 && request.status < 300) {
                          // Success
                          load(request.responseText);
                          fetchDocuments();
                          showSuccess('Files uploaded successfully');
                          setTimeout(() => {
                            setShowUploadModal(false);
                            setFiles([]);
                          }, 1000);
                        } else {
                          // Error
                          console.error('Upload error:', request.responseText);
                          error('Upload failed');
                          showError('Error uploading files');
                        }
                      };
                      
                      // Handle errors
                      request.onerror = function() {
                        console.error('Upload error:', request.responseText);
                        error('Upload failed');
                        showError('Error uploading files');
                      };
                      
                      // Handle progress
                      request.upload.onprogress = function(e) {
                        progress(e.lengthComputable, e.loaded, e.total);
                      };
                      
                      // Send request
                      request.send(formData);
                      
                      // Return abort function
                      return {
                        abort: () => {
                          request.abort();
                          abort();
                        }
                      };
                    }
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