import {
  IonButton,
  IonCard,
  IonCol,
  IonGrid,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonRow,
  IonText,
} from '@ionic/react';
import { arrowForwardOutline, checkmarkOutline } from 'ionicons/icons';
import React from 'react';

const options = [
  {
    name: 'Monthly',
    color: '#16CB88',
    amount: '4,000',
  },
  {
    name: 'Quarterly',
    color: '#FE875C',
    amount: '24,000',
  },
  {
    name: 'Yearly',
    color: '#3936EB',
    amount: '48,000',
  },
];

export default function OnlinePayment() {
  return (
    <IonGrid>
      <IonRow>
        {options.map((item, index) => (
          <IonCol size='12' sizeMd='6' sizeLg='4' key={index.toString()}>
            <IonCard className='ion-padding'>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 20,
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    width: 50,
                    height: 50,
                    backgroundColor: item.color,
                    borderRadius: 10,
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      backgroundColor: '#ffffff',
                      opacity: 0.3,
                      position: 'absolute',
                      left: 20,
                      top: -10,
                    }}
                  />
                </div>
                <div
                  style={{
                    // border: '1px solid red',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <IonLabel style={{ fontWeight: 'bold' }}>
                    {item.name}
                  </IonLabel>
                  <IonText>
                    <sup>₦</sup> {item.amount}
                  </IonText>
                </div>
              </div>

              <IonList lines='none' className='ion-no-padding'>
                <IonItem className='ion-no-padding'>
                  <IonIcon icon={checkmarkOutline} slot='start' size='small' />
                  <IonLabel>All features</IonLabel>
                </IonItem>
                <IonItem className='ion-no-padding'>
                  <IonIcon icon={checkmarkOutline} slot='start' size='small' />
                  <IonLabel>Get access to Ai</IonLabel>
                </IonItem>
              </IonList>

              <IonButton
                size='small'
                expand='block'
                className='ion-button-reset'
                shape='round'
              >
                <IonIcon slot='end' icon={arrowForwardOutline} size='small' />
                Choose Plan
              </IonButton>
            </IonCard>
          </IonCol>
        ))}
      </IonRow>
    </IonGrid>
  );
}
