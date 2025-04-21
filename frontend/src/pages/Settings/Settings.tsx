import {
  IonAvatar,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonPage,
  IonToggle,
  IonBadge,
} from '@ionic/react';
import React from 'react';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { logout } from '../../features/authSlice';
import { toggleDarkMode } from '../../features/themeSlice';
import {
  logInOutline,
  moonOutline,
  personOutline,
  settingsOutline,
  documentTextOutline,
  peopleOutline,
  analyticsOutline,
  serverOutline,
  keyOutline,
  notificationsOutline,
  cloudUploadOutline,
  lockClosedOutline,
} from 'ionicons/icons';
import './settings.css';

const getInitials = (name: string): string => {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase();
};

const Settings: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.user);
  const { isDarkMode } = useAppSelector((state) => state.theme);

  const adminSettings = [
    { name: 'Account Profile', url: 'profile', icon: personOutline },
    { name: 'Dark Mode', icon: moonOutline },
    { name: 'System Settings', url: 'system-settings', icon: settingsOutline },
  ];

  const contentManagement = [
    { name: 'Document Management', url: 'documents', icon: documentTextOutline },
    { name: 'User Management', url: 'users', icon: peopleOutline },
    { name: 'Knowledge Base', url: 'knowledgebase', icon: analyticsOutline },
  ];

  const systemSettings = [
    { name: 'Database Settings', url: 'database', icon: serverOutline },
    { name: 'API Configuration', url: 'api-config', icon: keyOutline },
    { name: 'Notifications', url: 'notifications', icon: notificationsOutline },
    { name: 'Backup & Storage', url: 'backup', icon: cloudUploadOutline },
    { name: 'Security Settings', url: 'security', icon: lockClosedOutline },
    {
      name: 'Log out',
      icon: logInOutline,
      onClick: () => {
        dispatch(logout());
      },
    },
  ];

  const handleToggleChange = (event: CustomEvent) => {
    const shouldEnable = event.detail.checked;
    dispatch(toggleDarkMode(shouldEnable));
  };

  return (
    <IonPage>
      <Header title='Settings' noBorder translucent />
      <Container padding={false} width='100%'>
        <div className="profile-section">
          <IonAvatar className="profile-avatar">
            <IonLabel className="initials-label">
              {getInitials(user?.name!)}
            </IonLabel>
          </IonAvatar>
          <div className="profile-info">
            <IonLabel>{user?.name}</IonLabel>
            <IonBadge color="primary">{ 'Admin'}</IonBadge>
          </div>
        </div>

        <IonList inset={true} mode='ios'>
          {adminSettings.map((item) => (
            <IonItem
              detail={item.url ? true : false}
              routerLink={item.url}
              key={item.name}
              className="settings-item"
            >
              <IonIcon
                aria-hidden='true'
                icon={item.icon}
                slot='start'
                size='small'
              />
              {item.name.toLowerCase() === 'dark mode' ? (
                <IonToggle
                  checked={isDarkMode}
                  onIonChange={handleToggleChange}
                >
                  {item.name}
                </IonToggle>
              ) : (
                <IonLabel>{item.name}</IonLabel>
              )}
            </IonItem>
          ))}
        </IonList>

        <IonList inset={true} mode='ios'>
          {contentManagement.map((item) => (
            <IonItem
              button
              detail={item.url ? true : false}
              routerLink={item.url}
              key={item.name}
              className="settings-item"
            >
              <IonIcon
                aria-hidden='true'
                icon={item.icon}
                slot='start'
                size='small'
              />
              <IonLabel>{item.name}</IonLabel>
            </IonItem>
          ))}
        </IonList>

        <IonList inset={true} mode='ios'>
          {systemSettings.map((item) => (
            <IonItem
              button
              detail={item.url ? true : false}
              routerLink={item.url}
              key={item.name}
              className="settings-item"
              onClick={item.onClick}
            >
              <IonIcon
                aria-hidden='true'
                icon={item.icon}
                slot='start'
                size='small'
              />
              <IonLabel color={item.name === 'Log out' ? 'danger' : ''}>
                {item.name}
              </IonLabel>
            </IonItem>
          ))}
        </IonList>
      </Container>
    </IonPage>
  );
};

export default Settings;