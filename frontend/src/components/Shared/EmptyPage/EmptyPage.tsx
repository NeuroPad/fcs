import React from 'react';
import { IonCard, IonIcon, IonText } from '@ionic/react';
import { documentOutline } from 'ionicons/icons';

export default function EmptyPage({ text }: { text?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 100,
        opacity: 0.5,
      }}
    >
      <IonIcon icon={documentOutline} size='large' />
      <br />
      <IonText>{text || 'Empty Page'}</IonText>
    </div>
  );
}
