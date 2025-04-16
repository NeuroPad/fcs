import {
  IonBackButton,
  IonButton,
  IonButtons,
  IonHeader,
  IonIcon,
  IonMenuButton,
  IonTitle,
  IonToolbar,
} from '@ionic/react';
import { closeOutline } from 'ionicons/icons';
import React from 'react';

interface IHeader {
  title: string;
  goBack?: boolean;
  translucent?: boolean;
  noBorder?: boolean;
  menu?: boolean;
  onClose?: () => void;
}

export default function Header({
  title,
  goBack = false,
  translucent = true,
  noBorder = false,
  menu = true,
  onClose,
}: IHeader) {
  return (
    <IonHeader
      translucent={translucent}
      className={noBorder ? 'ion-no-border' : ''}
    >
      <IonToolbar>
        <IonButtons slot='start'>
          {goBack && <IonBackButton></IonBackButton>}
          {menu && <IonMenuButton />}
        </IonButtons>
        <IonTitle>
          <small>{title}</small>
        </IonTitle>
        {onClose && (
          <IonButton slot='end' onClick={onClose} fill='clear'>
            <IonIcon icon={closeOutline} />
          </IonButton>
        )}
      </IonToolbar>
    </IonHeader>
  );
}
