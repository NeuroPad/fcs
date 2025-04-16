import { IonContent } from '@ionic/react';
import React, { useEffect, useRef, useState } from 'react';

interface IContainer {
  width?: string;
  children: any;
  padding?: boolean;
}

export default function Container({
  width = '100%',
  padding = true,
  children,
}: IContainer) {
  const [hasScrollbar, setHasScrollbar] = useState(false);
  const contentRef = useRef<HTMLIonContentElement>(null); // Use ref for IonContent

  useEffect(() => {
    const checkScrollbar = async () => {
      if (contentRef.current) {
        const scrollElement = await contentRef.current.getScrollElement(); // Get the scroll element
        const scrollHeight = scrollElement.scrollHeight;
        const clientHeight = scrollElement.clientHeight;

        setHasScrollbar(scrollHeight > clientHeight);
      }
    };

    // Check scrollbar on mount
    checkScrollbar();
    window.addEventListener('resize', checkScrollbar);

    // Cleanup event listener on unmount
    return () => window.removeEventListener('resize', checkScrollbar);
  }, []);

  return (
    <IonContent
      ref={contentRef}
      className={padding ? 'ion-padding' : 'ion-no-padding'}
    >
      <div
        style={{
          width: width,
          maxWidth: '100%',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {children}
      </div>
      <img
        src='assets/images/ragbackground.png'
        style={{
          maxHeight: '40%',
          position: 'fixed',
          bottom: 0,
          // right: hasScrollbar ? 20 : 0,
          right: 0,
          zIndex: -1,
          opacity: 0.2,
        }}
        alt='app-background-pattern'
      />
    </IonContent>
  );
}
