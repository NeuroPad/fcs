import {
  IonPage,
  IonButton,
  IonIcon,
  IonModal,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonButtons,
  IonContent,
  IonItem,
  IonLabel,
  IonInput,
  IonSelect,
  IonSelectOption,
  IonToast,
  IonBadge,
  IonSegment,
  IonSegmentButton,
  IonSearchbar,
} from '@ionic/react';
import React, { useEffect, useState } from 'react';
import DataTable from 'react-data-table-component';
import { 
  personAdd, 
  close, 
  create, 
  trash, 
  key,
  documentText
} from 'ionicons/icons';
import { useHistory } from 'react-router';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import './UserManagement.css';

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
  lastLogin: string;
}

const UserManagement: React.FC = () => {
  const history = useHistory();
  const [users, setUsers] = useState<User[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    role: 'user',
    status: 'active',
  });

  const columns = [
    {
      name: 'Name',
      selector: (row: User) => row.name,
      sortable: true,
    },
    {
      name: 'Email',
      selector: (row: User) => row.email,
      sortable: true,
    },
    {
      name: 'Role',
      selector: (row: User) => row.role,
      cell: (row: User) => (
        <IonBadge color={row.role === 'admin' ? 'primary' : 'medium'}>
          {row.role}
        </IonBadge>
      ),
      sortable: true,
    },
    {
      name: 'Status',
      selector: (row: User) => row.status,
      cell: (row: User) => (
        <IonBadge color={row.status === 'active' ? 'success' : 'warning'}>
          {row.status}
        </IonBadge>
      ),
      sortable: true,
    },
    {
      name: 'Last Login',
      selector: (row: User) => row.lastLogin,
      sortable: true,
    },
    {
      name: 'Actions',
      cell: (row: User) => (
        <div className="action-buttons">
          <IonButton 
            fill="clear" 
            size="small"
            onClick={() => handleEditRole(row)}
          >
            <IonIcon icon={key} />
          </IonButton>
          <IonButton 
            fill="clear" 
            size="small"
            onClick={() => history.push(`/user-logs/${row.id}`)}
          >
            <IonIcon icon={documentText} />
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
    },
  ];

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = () => {
    // Replace with actual API call
    const sampleUsers: User[] = [
      {
        id: 1,
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        status: 'active',
        lastLogin: '2025-01-14 10:30:00',
      },
      {
        id: 2,
        name: 'Jane Smith',
        email: 'jane@example.com',
        role: 'user',
        status: 'active',
        lastLogin: '2025-01-14 09:15:00',
      },
    ];
    setUsers(sampleUsers);
  };

  const handleAddUser = () => {
    // Replace with actual API call
    console.log('Adding user:', formData);
    setShowAddModal(false);
    setToastMessage('User added successfully');
    setShowToast(true);
    fetchUsers();
  };

  const handleEditRole = (user: User) => {
    setSelectedUser(user);
    setShowRoleModal(true);
  };

  const handleUpdateRole = () => {
    // Replace with actual API call
    setShowRoleModal(false);
    setToastMessage('User role updated successfully');
    setShowToast(true);
    fetchUsers();
  };

  const handleDelete = (userId: number) => {
    // Replace with actual API call
    console.log('Deleting user:', userId);
    setToastMessage('User deleted successfully');
    setShowToast(true);
    fetchUsers();
  };

  const filteredUsers = users.filter(user => 
    user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <IonPage>
      <Header title="User Management" />
      
      <Container>
        <div className="user-management-container">
          <div className="table-header">
            <IonSearchbar
              value={searchQuery}
              onIonChange={e => setSearchQuery(e.detail.value!)}
              placeholder="Search users..."
            />
            <IonButton
              onClick={() => setShowAddModal(true)}
              className="add-button"
            >
              <IonIcon icon={personAdd} slot="start" />
              Add User
            </IonButton>
          </div>

          <DataTable
            columns={columns}
            data={filteredUsers}
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

        {/* Add User Modal */}
        <IonModal isOpen={showAddModal} onDidDismiss={() => setShowAddModal(false)}>
          <IonHeader>
            <IonToolbar>
              <IonTitle>Add New User</IonTitle>
              <IonButtons slot="end">
                <IonButton onClick={() => setShowAddModal(false)}>
                  <IonIcon icon={close} />
                </IonButton>
              </IonButtons>
            </IonToolbar>
          </IonHeader>
          <IonContent>
            <div className="form-container">
              <IonItem>
                <IonLabel position="stacked">Name</IonLabel>
                <IonInput
                  value={formData.name}
                  onIonChange={e => setFormData({...formData, name: e.detail.value?.toString() || ''})}
                />
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">Email</IonLabel>
                <IonInput
                  type="email"
                  value={formData.email}
                  onIonChange={e => setFormData({...formData, email: e.detail.value?.toString() || ''})}
                />
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">Role</IonLabel>
                <IonSelect
                  value={formData.role}
                  onIonChange={e => setFormData({...formData, role: e.detail.value})}
                >
                  <IonSelectOption value="admin">Admin</IonSelectOption>
                  <IonSelectOption value="user">User</IonSelectOption>
                </IonSelect>
              </IonItem>
              <IonButton expand="block" onClick={handleAddUser}>
                Add User
              </IonButton>
            </div>
          </IonContent>
        </IonModal>

        {/* Edit Role Modal */}
        <IonModal isOpen={showRoleModal} onDidDismiss={() => setShowRoleModal(false)}>
          <IonHeader>
            <IonToolbar>
              <IonTitle>Edit User Role</IonTitle>
              <IonButtons slot="end">
                <IonButton onClick={() => setShowRoleModal(false)}>
                  <IonIcon icon={close} />
                </IonButton>
              </IonButtons>
            </IonToolbar>
          </IonHeader>
          <IonContent>
            <div className="form-container">
              <IonItem>
                <IonLabel>User: {selectedUser?.name}</IonLabel>
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">Role</IonLabel>
                <IonSelect
                  value={selectedUser?.role}
                  onIonChange={e => setSelectedUser({...selectedUser!, role: e.detail.value})}
                >
                  <IonSelectOption value="admin">Admin</IonSelectOption>
                  <IonSelectOption value="user">User</IonSelectOption>
                </IonSelect>
              </IonItem>
              <IonButton expand="block" onClick={handleUpdateRole}>
                Update Role
              </IonButton>
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

export default UserManagement;