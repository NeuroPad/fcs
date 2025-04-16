import {
  IonPage,
  IonCard,
  IonCardHeader,
  IonCardTitle,
  IonCardContent,
  IonButton,
  IonIcon,
  IonGrid,
  IonRow,
  IonCol,
  // IonBadge, // Removed unused import
  IonToast,
  IonRefresher,
  IonRefresherContent,
  // IonText, // Removed unused import
  IonProgressBar,
  IonSegment,
  IonSegmentButton,
  IonLabel,
} from '@ionic/react';
import React, { useEffect, useState } from 'react';
import {
  refreshCircle,
  analyticsOutline,
  list,
  // checkmarkCircle, // Removed unused import
  hourglassOutline,
  // warningOutline, // Removed unused import
} from 'ionicons/icons';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import './KnowledgeBaseManagement.css';
import { API_BASE_URL } from '../../api/config';
import GraphView from './GraphView';
import TableView from './TableView';

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

const KnowledgeBaseManagement: React.FC = () => {
  const [isReindexing, setIsReindexing] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [graphStats, setGraphStats] = useState<GraphStats>({
    totalNodes: 0,
    totalRelationships: 0,
    totalDocuments: 0,
    averageRelationsPerNode: 0,
    lastIndexed: '',
  });
  const [relationships, setRelationships] = useState<RelationshipData[]>([]);
  // Add state for segment selection
  const [selectedSegment, setSelectedSegment] = useState<string>('graph');

  // Add these interfaces near the top with other interfaces
  interface ProcessingStatus {
    status: string;
    message: string;
    progress: number;
    processed_documents: number;
    total_documents: number;
  }

  // Add these state variables in the component
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    status: 'idle',
    message: '',
    progress: 0,
    processed_documents: 0,
    total_documents: 0,
  });
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    fetchGraphStats();
    fetchRelationships();
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [ws]);

  const fetchGraphStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/graph-rag/stats`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
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
      // Set default values if API fails
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
      const response = await fetch(`${API_BASE_URL}/graph-rag/relationships`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
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
      setRelationships([]); // Clear relationships on error
    }
  };

  // Add new handler for Relik KG creation
  const handleRelikIndex = async () => {
    setIsReindexing(true);
    setToastMessage('Knowledge Graph creation using Relik started...');
    setShowToast(true);

    try {
      // Trigger the Relik processing
      const response = await fetch(`${API_BASE_URL}/relik/process-documents`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to trigger Relik KG creation');
      }

      // Show success message
      setToastMessage('Knowledge Graph creation using Relik completed');
      setShowToast(true);

      // Refresh the stats and relationships
      await Promise.all([fetchGraphStats(), fetchRelationships()]);
    } catch (error) {
      console.error('Error during Relik KG creation:', error);
      setToastMessage(error instanceof Error ? error.message : 'Error during Relik KG creation');
      setShowToast(true);
    } finally {
      setIsReindexing(false);
    }
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setToastMessage('Knowledge Graph creation started...');
    setShowToast(true);

    try {
      // First, trigger the processing
      const response = await fetch(`${API_BASE_URL}/graph-rag/process-documents`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to trigger KG creation');
      }

      // Then establish WebSocket connection
      const websocket = new WebSocket(`ws://${API_BASE_URL.replace('http://', '')}/graph-rag/ws/process-documents`);

      websocket.onmessage = (event) => {
        const status: ProcessingStatus = JSON.parse(event.data);
        setProcessingStatus(status);

        // Update toast with progress
        setToastMessage(`${status.message} (${status.progress.toFixed(0)}%)`);
        setShowToast(true);

        // When processing is complete or has errored
        if (status.status === 'completed' || status.status === 'error') {
          setIsReindexing(false);
          websocket.close();
          // Refresh the stats and relationships
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

  const handleRefresh = (event: CustomEvent) => {
    Promise.all([fetchGraphStats(), fetchRelationships()]).then(() => {
      event.detail.complete();
    });
  };

  // Handle segment change
  const handleSegmentChange = (e: CustomEvent) => {
    setSelectedSegment(e.detail.value ?? 'graph');
  };


  return (
    <IonPage>
      <Header title="Knowledge Base Management" />
      <Container>
        <IonRefresher slot="fixed" onIonRefresh={handleRefresh}>
          <IonRefresherContent></IonRefresherContent>
        </IonRefresher>

        <div className="knowledge-base-container">
          {/* Reindex Card */}
          <IonCard className="reindex-card">
            <IonCardHeader>
              <IonCardTitle>Knowledge Graph Management</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <p>Last indexed: {graphStats.lastIndexed || 'Not available'}</p>
              
              {isReindexing && (
                <div className="indexing-status">
                  <IonProgressBar value={processingStatus.progress / 100}></IonProgressBar>
                  <p>
                    <IonIcon icon={hourglassOutline} />
                    {processingStatus.message || 'Processing documents...'}
                    ({processingStatus.processed_documents}/{processingStatus.total_documents})
                  </p>
                </div>
              )}
              
              <IonButton
                expand="block"
                onClick={handleReindex}
                disabled={isReindexing}
              >
                <IonIcon slot="start" icon={refreshCircle} />
                Rebuild Knowledge Graph
              </IonButton>
              
              <IonButton
                expand="block"
                color="secondary"
                onClick={handleRelikIndex}
                disabled={isReindexing}
                style={{ marginTop: '8px' }}
              >
                <IonIcon slot="start" icon={refreshCircle} />
                Rebuild with Relik
              </IonButton>
            </IonCardContent>
          </IonCard>

          {/* Stats Cards */}
          <IonGrid>
            <IonRow>
              <IonCol size="12" sizeMd="3">
                <IonCard className="stat-card">
                  <IonCardContent>
                    <div className="stat-value">{graphStats.totalNodes}</div>
                    <div className="stat-label">Total Nodes</div>
                  </IonCardContent>
                </IonCard>
              </IonCol>
              <IonCol size="12" sizeMd="3">
                <IonCard className="stat-card">
                  <IonCardContent>
                    <div className="stat-value">{graphStats.totalRelationships}</div>
                    <div className="stat-label">Total Relationships</div>
                  </IonCardContent>
                </IonCard>
              </IonCol>
              <IonCol size="12" sizeMd="3">
                <IonCard className="stat-card">
                  <IonCardContent>
                    <div className="stat-value">{graphStats.totalDocuments}</div>
                    <div className="stat-label">Total Documents</div>
                  </IonCardContent>
                </IonCard>
              </IonCol>
              <IonCol size="12" sizeMd="3">
                <IonCard className="stat-card">
                  <IonCardContent>
                    <div className="stat-value">{graphStats.averageRelationsPerNode.toFixed(1)}</div>
                    <div className="stat-label">Avg. Relations per Node</div>
                  </IonCardContent>
                </IonCard>
              </IonCol>
            </IonRow>
          </IonGrid>

          {/* Segment for switching between Graph and Table views */}
          <IonSegment value={selectedSegment} onIonChange={handleSegmentChange}>
            <IonSegmentButton value="graph">
              <IonLabel>Graph View</IonLabel>
            </IonSegmentButton>
            <IonSegmentButton value="table">
              <IonLabel>Table View</IonLabel>
            </IonSegmentButton>
          </IonSegment>
          <div style={{ marginTop: 16 }}>
            {selectedSegment === 'graph' && (
              <GraphView relationships={relationships} />
            )}
            {selectedSegment === 'table' && (
              <TableView relationships={relationships} />
            )}
          </div>
        </div>

        <IonToast
          isOpen={showToast}
          onDidDismiss={() => setShowToast(false)}
          message={toastMessage}
          duration={3000}
          position="bottom"
        />
      </Container>
    </IonPage>
  );
};

export default KnowledgeBaseManagement;
