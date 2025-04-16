import {
  IonPage,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardTitle,
  IonItem,
  IonLabel,
  IonSelect,
  IonSelectOption,
  IonDatetime,
  IonButton,
  IonIcon,
  IonBadge,
  IonChip,
  IonGrid,
  IonRow,
  IonCol,
  IonBackButton,
  IonButtons,
} from '@ionic/react';
import React, { useEffect, useState } from 'react';
import { RouteComponentProps } from 'react-router-dom';
import DataTable from 'react-data-table-component';
import { 
  calendar, 
  filterCircle,
  downloadOutline,
  personCircle
} from 'ionicons/icons';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import './UserActivityLogs.css';

interface ActivityLog {
  id: number;
  userId: number;
  action: string;
  details: string;
  ipAddress: string;
  timestamp: string;
  status: 'success' | 'failed' | 'warning';
}

interface UserDetails {
  id: number;
  name: string;
  email: string;
  role: string;
}

interface RouteParams {
  userId: string;
}

const UserActivityLogs: React.FC<RouteComponentProps<RouteParams>> = ({ match }) => {
  const userId = match.params.userId;
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [userDetails, setUserDetails] = useState<UserDetails | null>(null);
  const [dateRange, setDateRange] = useState({
    start: '',
    end: '',
  });
  const [actionFilter, setActionFilter] = useState('all');

  const columns = [
    {
      name: 'Timestamp',
      selector: (row: ActivityLog) => row.timestamp,
      sortable: true,
    },
    {
      name: 'Action',
      selector: (row: ActivityLog) => row.action,
      cell: (row: ActivityLog) => (
        <IonChip color="primary" className="action-chip">
          {row.action}
        </IonChip>
      ),
      sortable: true,
    },
    {
      name: 'Details',
      selector: (row: ActivityLog) => row.details,
      grow: 2,
    },
    {
      name: 'IP Address',
      selector: (row: ActivityLog) => row.ipAddress,
    },
    {
      name: 'Status',
      selector: (row: ActivityLog) => row.status,
      cell: (row: ActivityLog) => (
        <IonBadge color={
          row.status === 'success' ? 'success' : 
          row.status === 'failed' ? 'danger' : 'warning'
        }>
          {row.status}
        </IonBadge>
      ),
      sortable: true,
    },
  ];

  useEffect(() => {
    if (userId) {
      fetchUserDetails();
      fetchActivityLogs();
    }
  }, [userId]);

  const fetchUserDetails = async () => {
    try {
      // Replace with actual API call
      setUserDetails({
        id: parseInt(userId),
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
      });
    } catch (error) {
      console.error('Error fetching user details:', error);
    }
  };

  const fetchActivityLogs = async () => {
    try {
      // Replace with actual API call
      const sampleLogs: ActivityLog[] = [
        {
          id: 1,
          userId: parseInt(userId),
          action: 'LOGIN',
          details: 'User logged in successfully',
          ipAddress: '192.168.1.1',
          timestamp: '2025-01-14 10:30:00',
          status: 'success',
        },
        {
          id: 2,
          userId: parseInt(userId),
          action: 'DOCUMENT_VIEW',
          details: 'Accessed document: Financial Report 2024',
          ipAddress: '192.168.1.1',
          timestamp: '2025-01-14 10:35:00',
          status: 'success',
        },
      ];
      setLogs(sampleLogs);
    } catch (error) {
      console.error('Error fetching activity logs:', error);
    }
  };

  const handleExportLogs = () => {
    // Implement CSV export functionality
    console.log('Exporting logs for user:', userId);
  };

  return (
    <IonPage>
      <Header title="User Activity Logs" />
        {/* <IonButtons slot="start">
          <IonBackButton defaultHref="/users" />
        </IonButtons> */}
      {/* </Header> */}
      
      <Container>
        <div className="user-logs-container">
          {/* User Info Card */}
          <IonCard className="user-info-card">
            <IonCardContent>
              <IonGrid>
                <IonRow className="ion-align-items-center">
                  <IonCol size="auto">
                    <IonIcon
                      icon={personCircle}
                      color="primary"
                      className="user-icon"
                    />
                  </IonCol>
                  <IonCol>
                    <h2>{userDetails?.name}</h2>
                    <p>{userDetails?.email}</p>
                    <IonBadge color="primary">{userDetails?.role}</IonBadge>
                  </IonCol>
                </IonRow>
              </IonGrid>
            </IonCardContent>
          </IonCard>

          {/* Filters Card */}
          <IonCard className="filters-card">
            <IonCardHeader>
              <IonCardTitle>Filters</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <IonGrid>
                <IonRow>
                  <IonCol size="12" sizeMd="4">
                    <IonItem>
                      <IonLabel>Action Type</IonLabel>
                      <IonSelect
                        value={actionFilter}
                        onIonChange={e => setActionFilter(e.detail.value)}
                      >
                        <IonSelectOption value="all">All Actions</IonSelectOption>
                        <IonSelectOption value="LOGIN">Login</IonSelectOption>
                        <IonSelectOption value="DOCUMENT_VIEW">Document View</IonSelectOption>
                        <IonSelectOption value="SEARCH">Search</IonSelectOption>
                        <IonSelectOption value="EXPORT">Export</IonSelectOption>
                      </IonSelect>
                    </IonItem>
                  </IonCol>
                  <IonCol size="12" sizeMd="4">
                    <IonItem>
                      <IonLabel>Start Date</IonLabel>
                      <IonDatetime
                        value={dateRange.start}
                        onIonChange={e => setDateRange({...dateRange, start: e.detail.value?.toString() || ''})}
                        max={dateRange.end || undefined}
                      />
                    </IonItem>
                  </IonCol>
                  <IonCol size="12" sizeMd="4">
                    <IonItem>
                      <IonLabel>End Date</IonLabel>
                      <IonDatetime
                        value={dateRange.end}
                        onIonChange={e => setDateRange({...dateRange, end: e.detail.value?.toString() || ''})}
                        min={dateRange.start || undefined}
                      />
                    </IonItem>
                  </IonCol>
                </IonRow>
              </IonGrid>
            </IonCardContent>
          </IonCard>

          {/* Activity Logs Table */}
          <IonCard>
            <IonCardHeader>
              <div className="table-header">
                <IonCardTitle>Activity Logs</IonCardTitle>
                <IonButton onClick={handleExportLogs}>
                  <IonIcon icon={downloadOutline} slot="start" />
                  Export Logs
                </IonButton>
              </div>
            </IonCardHeader>
            <IonCardContent>
              <DataTable
                columns={columns}
                data={logs}
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
            </IonCardContent>
          </IonCard>
        </div>
      </Container>
    </IonPage>
  );
};

export default UserActivityLogs;