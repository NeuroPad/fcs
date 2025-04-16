import React from 'react';
import DataTable from 'react-data-table-component';
import { IonBadge } from '@ionic/react';

interface RelationshipData {
  id: string;
  sourceNode: string;
  relationship: string;
  targetNode: string;
  confidence: number;
  lastUpdated: string;
}

interface TableViewProps {
  relationships: RelationshipData[];
}

const columns = [
  {
    name: 'Source Node',
    selector: (row: RelationshipData) => row.sourceNode,
    sortable: true,
  },
  {
    name: 'Relationship',
    selector: (row: RelationshipData) => row.relationship,
    sortable: true,
  },
  {
    name: 'Target Node',
    selector: (row: RelationshipData) => row.targetNode,
    sortable: true,
  },
  {
    name: 'Confidence',
    selector: (row: RelationshipData) => row.confidence,
    cell: (row: RelationshipData) => (
      <IonBadge
        color={row.confidence > 0.7 ? 'success' : row.confidence > 0.4 ? 'warning' : 'danger'}
      >
        {(row.confidence * 100).toFixed(1)}%
      </IonBadge>
    ),
    sortable: true,
  },
  {
    name: 'Last Updated',
    selector: (row: RelationshipData) => row.lastUpdated,
    sortable: true,
  },
];

const TableView: React.FC<TableViewProps> = ({ relationships }) => (
  <div style={{ background: '#fff', borderRadius: 12, padding: 8 }}>
    <DataTable
      columns={columns}
      data={relationships}
      pagination
      highlightOnHover
      responsive
      striped
      noHeader
    />
  </div>
);

export default TableView;