import React from 'react';
import { IonIcon, IonItem, IonLabel, IonList, IonPage } from '@ionic/react';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { closeOutline, lockClosedOutline, pencilOutline } from 'ionicons/icons';

export default function Profile() {
  const data = [
    { name: 'Edit Profile', url: 'edit-profile', icon: pencilOutline },
    {
      name: 'Change Password',
      url: 'change-password',
      icon: lockClosedOutline,
    },
    {
      name: 'Delete Account',
      icon: closeOutline,
    },
  ];

  return (
    <IonPage>
      <Header title='Account Profile' goBack />

      <Container width='600px' padding={false}>
        <IonList inset lines='full' mode='ios'>
          {data.map((option, index) => (
            <IonItem
              button
              detail={option.url ? true : false}
              routerLink={option.url}
              key={option.name}
              style={{
                borderRadius: 5,
                marginBottom: 5,
                color: index === 2 ? '#ff0f0f' : undefined,
              }}
            >
              <IonIcon
                aria-hidden='true'
                icon={option.icon}
                slot='start'
                size='small'
              ></IonIcon>
              <IonLabel>{option.name}</IonLabel>
            </IonItem>
          ))}
        </IonList>
      </Container>
    </IonPage>
  );
}
