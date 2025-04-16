import React, { useMemo, useRef } from 'react';
import { GraphCanvas } from 'reagraph';
import './GraphView.css';

import { useSelection } from 'reagraph';

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
  // Use sample data if relationships is empty
  const { nodes, edges } = useMemo(() => {
    if (!relationships || relationships.length === 0) {
      return { nodes: SAMPLE_NODES, edges: SAMPLE_EDGES };
    }
    const nodeMap = new Map<string, any>();
    const edges: any[] = [];
    relationships.forEach(rel => {
      const isSpecial = rel.targetNode.toLowerCase().includes('ticket') || rel.targetNode.toLowerCase().includes('concert');
      if (!nodeMap.has(rel.sourceNode)) {
        nodeMap.set(rel.sourceNode, {
          id: rel.sourceNode,
          label: rel.sourceNode,
          fill: '#e91e63',
        });
      }
      if (!nodeMap.has(rel.targetNode)) {
        nodeMap.set(rel.targetNode, {
          id: rel.targetNode,
          label: rel.targetNode,
          fill: isSpecial ? '#2196f3' : '#e91e63',
        });
      }
      edges.push({
        id: rel.id,
        source: rel.sourceNode,
        target: rel.targetNode,
        label: rel.relationship,
        fill: '#aaa',
      });
    });
    return { nodes: Array.from(nodeMap.values()), edges };
  }, [relationships]);

  const graphRef = useRef(null);
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
      <div className="graph-canvas-wrapper">
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
        />
      </div>
    </div>
  );
};

export default GraphView;