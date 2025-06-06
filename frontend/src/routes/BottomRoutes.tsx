import {
  IonIcon,
  IonLabel,
  IonRouterOutlet,
  IonTabBar,
  IonTabButton,
  IonTabs,
} from '@ionic/react';
import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  home,
  homeOutline,
  school,
  schoolOutline,
  flower,
  flowerOutline,
  settings,
  settingsOutline,
  libraryOutline,
  library,
  document,
  documentOutline
} from 'ionicons/icons';
import AppRoutes from './AppRoutes';

interface BottomRoutesProps {
  isAuthenticated: boolean;
}

export default function BottomRoutes({ isAuthenticated }: BottomRoutesProps) {
  const location = useLocation();

  const getTabIcon = (path: string, selectedIcon: string, outlineIcon: string) => {
    return location.pathname === path ? selectedIcon : outlineIcon;
  };

  return (
    <IonTabs>
      <IonRouterOutlet id='main'>
        <AppRoutes isAuthenticated={isAuthenticated} />
      </IonRouterOutlet>

      <IonTabBar slot='bottom'>
        <IonTabButton tab='home' href='/' selected={location.pathname === '/'}>
          <IonIcon icon={getTabIcon('/', home, homeOutline)} />
          <IonLabel>Home</IonLabel>
        </IonTabButton>

        <IonTabButton 
          tab='knowledgebase'
          href='/knowledgebase' 
          selected={location.pathname.startsWith('/knowledgebase')}
        >
          <IonIcon icon={getTabIcon('/knowledgebase', library, libraryOutline)} />
          <IonLabel>Knowledge Base</IonLabel>
        </IonTabButton>

        <IonTabButton 
          tab='settings' 
          href='/settings' 
          selected={location.pathname === '/settings'}
        >
          <IonIcon icon={getTabIcon('/settings', settings, settingsOutline)} />
          <IonLabel>Settings</IonLabel>
        </IonTabButton>
      </IonTabBar>
    </IonTabs>
  );
}