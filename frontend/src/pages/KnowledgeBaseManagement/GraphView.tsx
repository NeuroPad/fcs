import React, { useMemo, useRef, useState, useEffect } from 'react';
import { GraphCanvas, useSelection } from 'reagraph';
import { IonIcon } from '@ionic/react';
import { reloadCircleOutline, pauseCircleOutline, playCircleOutline } from 'ionicons/icons';
import './GraphView.css';

interface RelationshipData {
  id: string;
  sourceNode: string;
  relationship: string;
  targetNode: string;
  confidence: number;
  lastUpdated: string;
}

interface GraphViewProps {
  relationships: RelationshipData[];
}

const SAMPLE_NODES = [
  { id: "n-1", label: "1", fill: "#e91e63" },
  { id: "n-2", label: "2", fill: "#e91e63" },
  { id: "n-3", label: "3", fill: "#2196f3" },
  { id: "n-4", label: "4", fill: "#e91e63" }
];

const SAMPLE_EDGES = [
  { id: "1->2", source: "n-1", target: "n-2", label: "Edge 1-2", fill: "#aaa" },
  { id: "1->3", source: "n-1", target: "n-3", label: "Edge 1-3", fill: "#aaa" },
  { id: "1->4", source: "n-1", target: "n-4", label: "Edge 1-4", fill: "#aaa" }
];

const GraphView: React.FC<GraphViewProps> = ({ relationships }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isOrbiting, setIsOrbiting] = useState(true);
  const graphRef = useRef(null);
  
  const { nodes, edges } = useMemo(() => {
    if (!relationships || relationships.length === 0) {
      return { nodes: [], edges: [] };  // Return empty instead of sample data
    }

    const nodeMap = new Map<string, any>();
    const edges: any[] = [];

    relationships.forEach(rel => {
      // Skip invalid relationships
      if (!rel.sourceNode || !rel.targetNode) {
        console.warn('Invalid relationship found:', rel);
        return;
      }

      const targetNodeStr = String(rel.targetNode);
      const sourceNodeStr = String(rel.sourceNode);
      
      const isSpecial = targetNodeStr.toLowerCase().includes('ticket') || 
                       targetNodeStr.toLowerCase().includes('concert');

      if (!nodeMap.has(sourceNodeStr)) {
        nodeMap.set(sourceNodeStr, {
          id: sourceNodeStr,
          label: sourceNodeStr,
          fill: '#e91e63',
        });
      }

      if (!nodeMap.has(targetNodeStr)) {
        nodeMap.set(targetNodeStr, {
          id: targetNodeStr,
          label: targetNodeStr,
          fill: isSpecial ? '#2196f3' : '#e91e63',
        });
      }

      edges.push({
        id: rel.id || `${sourceNodeStr}->${targetNodeStr}`,
        source: sourceNodeStr,
        target: targetNodeStr,
        label: rel.relationship || '',
        fill: '#aaa',
      });
    });

    return { 
      nodes: Array.from(nodeMap.values()), 
      edges 
    };
  }, [relationships]);

  // Simulate loading state
  useEffect(() => {
    setIsLoading(true);
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, [relationships]);

  const toggleOrbit = () => {
    setIsOrbiting(!isOrbiting);
  };

  const {
    selections,
    actives,
    onNodeClick,
    onCanvasClick,
    onNodePointerOver,
    onNodePointerOut
  } = useSelection({
    ref: graphRef,
    nodes,
    edges,
    pathSelectionType: 'out'
  });

  return (
    <div className="graph-view-container">
      <div className="entity-types-legend">
        <h4>Entity Types</h4>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#e91e63' }}></span>
          <span>Entity</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#2196f3' }}></span>
          <span>Special Entity</span>
        </div>
      </div>
      
      {/* Remove the controls div as the buttons are removed */}
      {/* <div className="graph-controls"> ... </div> */}

      <div className="orbit-controls">
        <button onClick={toggleOrbit} title={isOrbiting ? 'Pause Orbit' : 'Start Orbit'}>
          <IonIcon icon={isOrbiting ? pauseCircleOutline : playCircleOutline} />
        </button>
      </div>

      <div className="graph-canvas-wrapper">
        <div className="brain-background"></div>
        
        {isLoading && (
          <div className="graph-message loading">
            <IonIcon icon={reloadCircleOutline} className="spin-icon" />
            <p>Loading your memory graph...</p>
          </div>
        )}
        
        {!isLoading && nodes.length === 0 && (
          <div className="graph-message">
            <h3>Memory Empty</h3>
            <p>No connections found in your knowledge graph.</p>
            <p>Start adding relationships to visualize your neural network.</p>
          </div>
        )}
        
        {!isLoading && nodes.length > 0 && (
          <GraphCanvas
            ref={graphRef}
            nodes={nodes}
            edges={edges}
            labelType="all"
            draggable
            selections={selections}
            actives={actives}
            onNodeClick={onNodeClick}
            onCanvasClick={onCanvasClick}
            onNodePointerOver={onNodePointerOver}
            onNodePointerOut={onNodePointerOut}
            layoutType="treeTd3d"
            layoutOverrides={{
              nodeStrength: -600,
              linkDistance: 180,
            }}
            edgeArrowPosition="none"
            cameraMode={isOrbiting ? "orbit" : "pan"}
            animated={true}
          />
        )}
      </div>
    </div>
  );
};

export default GraphView;