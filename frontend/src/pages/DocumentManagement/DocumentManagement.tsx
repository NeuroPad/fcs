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
import React, { useEffect, useState, useCallback } from 'react';
import DataTable from 'react-data-table-component';
import { trash, eye, cloudUpload, close, book, images } from 'ionicons/icons';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { API_BASE_URL } from '../../api/config';


interface Document {
  filename: string;
  uploadDate: string;
  size: number;
  isProcessed: boolean;
  imagesIndexed: boolean;
  knowledgeBaseIndexed: boolean;
  status: string;
  path: string;
  type: string;  // Add this line
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

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    try {
      setIsUploading(true);
      const formData = new FormData();
      acceptedFiles.forEach((file) => {
        formData.append('files', file);
      });

      await axios.post(`${API_BASE_URL}/files/upload-files`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      showSuccess('Files uploaded successfully');
      fetchDocuments();
      setShowUploadModal(false);
    } catch (error) {
      showError('Error uploading files');
    } finally {
      setIsUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/markdown': ['.md'],
      'application/json': ['.json'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']  // Add support for .doc files
    }
  });

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

  return (
    <IonPage>
      <Header title="Document Management" />

      
        <Container>
          <div className="document-management-container">
            <div className="table-header">
              <div className="action-buttons-group">

                <IonGrid>
                  <IonRow>

                   <IonCol>
                      <IonButton
                        onClick={() => setShowUploadModal(true)}
                        disabled={isUploading}
                      >
                        <IonIcon className="icon" icon={cloudUpload} slot="start" />
                        <span className="button-text">Upload Document</span>
                      </IonButton>
                    </IonCol>

                    <IonCol>
                      <IonButton
                        onClick={handleProcessDocuments}
                        disabled={isProcessing}
                        color="primary"
                      >
                        {isProcessing ? (
                          <>
                            <IonSpinner className="icon" name="crescent" />
                            <span className="button-text">Processing...</span>
                          </>
                        ) : (
                          <>
                            <IonIcon className="icon" icon={book} slot="start" />
                            <span className="button-text">Process Documents</span>
                          </>
                        )}
                      </IonButton>
                    </IonCol>
                    {/* <IonCol>
                      <IonButton
                        onClick={handleIndexImages}
                        disabled={isIndexing}
                        color="primary"
                      >
                        {isIndexing ? (
                          <>
                            <IonSpinner name="crescent" />
                            <span className="button-text">Indexing...</span>
                          </>
                        ) : (
                          <>
                            <IonIcon className="icon" icon={images} slot="start" />
                            <span className="button-text">Index Images</span>
                          </>
                        )}
                      </IonButton>
                    </IonCol> */}
                   
                    <IonCol>
                    <IonButton
                      onClick={handleMultimodalIndex}
                      disabled={isMultimodalIndexing}
                      color="primary"
                    >
                      {isMultimodalIndexing ? (
                        <>
                          <IonSpinner name="crescent" />
                          <span className="button-text">Indexing Multimodal...</span>
                        </>
                      ) : (
                        <>
                          <IonIcon className="icon" icon={book} slot="start" />
                          <span className="button-text">Index Multimodal</span>
                        </>
                      )}
                    </IonButton>
                  </IonCol>

                  </IonRow>
                </IonGrid>


              </div>
            </div>

            <DataTable
              columns={columns}
              data={documents}
              pagination
              responsive
              highlightOnHover
              striped
              customStyles={{
                headRow: {
                  style: {
                    backgroundColor: '#f4f5f8',
                    fontWeight: 'bold',
                  },
                },
              }}
            />
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
                <div {...getRootProps()} className="dropzone-container">
                  <input {...getInputProps()} />
                  <div className="dropzone-content">
                    <IonIcon
                      icon={cloudUpload}
                      style={{ fontSize: '48px', marginBottom: '16px' }}
                    />
                    {isDragActive ? (
                      <p>Drop your files here...</p>
                    ) : (
                      <div>
                        <p>Drag 'n' drop files here</p>
                        <p>or click to select files</p>
                        <p className="supported-files">
                          Supported files: PDF
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </IonContent>
          </IonModal>

          <IonToast
            isOpen={showToast}
            onDidDismiss={() => setShowToast(false)}
            message={toastMessage}
            duration={2000}
            position="bottom"
          />
        </Container>
     
    </IonPage>
  );
};

export default DocumentManagement;