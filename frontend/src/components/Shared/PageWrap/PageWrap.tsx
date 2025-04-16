import { IonPage } from '@ionic/react';
import React from 'react';

interface PageWrapProps {
  children: React.ReactNode;
  title?: string;
}

export default function PageWrap({ children, title }: PageWrapProps) {
  return (
    <IonPage>
      <title>{title || 'Memduo App'}</title>
      {children}
    </IonPage>
  );
}
