import { IonPage } from '@ionic/react';
import React from 'react';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import EmptyPage from '../../components/Shared/EmptyPage/EmptyPage';

export default function Coummunity() {
  return (
    <IonPage>
      <Header title='Coummunity' />
      <Container padding={false}>
        <EmptyPage text='No Coummunity' />
      </Container>
    </IonPage>
  );
}
