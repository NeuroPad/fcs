import React, { useState } from 'react';
import {
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardTitle,
  IonBadge,
  IonButton,
  IonIcon,
  IonItem,
  IonLabel,
  IonChip,
  IonGrid,
  IonRow,
  IonCol,
  IonProgressBar,
} from '@ionic/react';
import { chevronDown, chevronUp, bulb, analytics } from 'ionicons/icons';
import './ReasoningNodes.css';

interface ReasoningNode {
  uuid: string;
  name: string;
  salience?: number;
  confidence?: number;
  summary?: string;
  node_type?: string;
  used_in_context?: string;
}

interface ReasoningNodesProps {
  nodes: ReasoningNode[];
  title?: string;
}

const ReasoningNodes: React.FC<ReasoningNodesProps> = ({ 
  nodes, 
  title = "Knowledge Nodes Used" 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!nodes || nodes.length === 0) {
    return null;
  }

  // Sort nodes by salience (highest first)
  const sortedNodes = [...nodes].sort((a, b) => (b.salience || 0) - (a.salience || 0));

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'medium';
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'danger';
  };

  const getSalienceColor = (salience?: number) => {
    if (!salience) return 'medium';
    if (salience >= 0.8) return 'primary';
    if (salience >= 0.6) return 'secondary';
    return 'tertiary';
  };

  const formatNodeType = (nodeType?: string) => {
    if (!nodeType) return 'knowledge';
    return nodeType.charAt(0).toUpperCase() + nodeType.slice(1).replace(/_/g, ' ');
  };

  const formatContextUsage = (context?: string) => {
    if (!context) return 'General context';
    return context.split(', ').map(ctx => 
      ctx.charAt(0).toUpperCase() + ctx.slice(1).replace(/_/g, ' ')
    ).join(', ');
  };

  return (
    <IonCard className="reasoning-nodes-card">
      <IonCardHeader>
        <div className="reasoning-header">
          <div className="reasoning-title">
            <IonIcon icon={bulb} className="reasoning-icon" />
            <IonCardTitle>{title}</IonCardTitle>
            <IonBadge color="primary" className="node-count">
              {nodes.length}
            </IonBadge>
          </div>
          <IonButton
            fill="clear"
            onClick={() => setIsExpanded(!isExpanded)}
            className="expand-button"
          >
            <IonIcon icon={isExpanded ? chevronUp : chevronDown} />
          </IonButton>
        </div>
      </IonCardHeader>

      {isExpanded && (
        <IonCardContent>
          <div className="nodes-summary">
            <IonGrid>
              <IonRow>
                <IonCol size="6">
                  <div className="summary-stat">
                    <IonIcon icon={analytics} />
                    <div>
                      <div className="stat-value">
                        {(sortedNodes.reduce((sum, node) => sum + (node.salience || 0), 0) / nodes.length).toFixed(2)}
                      </div>
                      <div className="stat-label">Avg Salience</div>
                    </div>
                  </div>
                </IonCol>
                <IonCol size="6">
                  <div className="summary-stat">
                    <IonIcon icon={analytics} />
                    <div>
                      <div className="stat-value">
                        {(sortedNodes.reduce((sum, node) => sum + (node.confidence || 0), 0) / nodes.length).toFixed(2)}
                      </div>
                      <div className="stat-label">Avg Confidence</div>
                    </div>
                  </div>
                </IonCol>
              </IonRow>
            </IonGrid>
          </div>

          <div className="nodes-list">
            {sortedNodes.map((node, index) => (
              <div key={node.uuid} className="reasoning-node-item">
                <IonItem 
                  button 
                  onClick={() => setSelectedNode(selectedNode === node.uuid ? null : node.uuid)}
                  className="node-header"
                >
                  <div className="node-info" slot="start">
                    <div className="node-rank">#{index + 1}</div>
                    <div className="node-details">
                      <IonLabel>
                        <h3>{node.name}</h3>
                        <p>{formatNodeType(node.node_type)}</p>
                      </IonLabel>
                    </div>
                  </div>
                  
                  <div className="node-metrics" slot="end">
                    <div className="metric-item">
                      <IonChip color={getSalienceColor(node.salience)} className="metric-chip">
                        <IonLabel>S: {(node.salience || 0).toFixed(2)}</IonLabel>
                      </IonChip>
                    </div>
                    <div className="metric-item">
                      <IonChip color={getConfidenceColor(node.confidence)} className="metric-chip">
                        <IonLabel>C: {(node.confidence || 0).toFixed(2)}</IonLabel>
                      </IonChip>
                    </div>
                  </div>
                </IonItem>

                {selectedNode === node.uuid && (
                  <div className="node-details-expanded">
                    {node.summary && (
                      <div className="detail-section">
                        <div className="detail-label">Summary</div>
                        <div className="detail-content">{node.summary}</div>
                      </div>
                    )}
                    
                    <div className="detail-section">
                      <div className="detail-label">Usage Context</div>
                      <div className="detail-content">{formatContextUsage(node.used_in_context)}</div>
                    </div>

                    <div className="detail-section">
                      <div className="detail-label">Metrics</div>
                      <div className="metrics-detailed">
                        <div className="metric-detailed">
                          <div className="metric-name">Salience</div>
                          <div className="metric-bar">
                            <IonProgressBar 
                              value={node.salience || 0} 
                              color={getSalienceColor(node.salience)}
                            />
                          </div>
                          <div className="metric-value">{((node.salience || 0) * 100).toFixed(0)}%</div>
                        </div>
                        
                        <div className="metric-detailed">
                          <div className="metric-name">Confidence</div>
                          <div className="metric-bar">
                            <IonProgressBar 
                              value={node.confidence || 0} 
                              color={getConfidenceColor(node.confidence)}
                            />
                          </div>
                          <div className="metric-value">{((node.confidence || 0) * 100).toFixed(0)}%</div>
                        </div>
                      </div>
                    </div>

                    <div className="detail-section">
                      <div className="detail-label">Node ID</div>
                      <div className="detail-content node-uuid">{node.uuid}</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </IonCardContent>
      )}
    </IonCard>
  );
};

export default ReasoningNodes; 