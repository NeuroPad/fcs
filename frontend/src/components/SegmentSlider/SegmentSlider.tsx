import React, { useState, useRef, useEffect } from 'react';
import {
  IonSegment,
  IonSegmentButton,
  IonHeader,
  IonToolbar,
  IonButtons,
  IonMenuButton,
  IonLabel,
  IonTitle,
} from '@ionic/react';
import { Swiper, SwiperSlide } from 'swiper/react';
import 'swiper/swiper-bundle.min.css';

interface SegmentSliderProps {
  segments: { label: string; content: React.ReactNode }[];
  title: string;
  headerShown?: boolean;
  activeTab?: string;
  onActiveTabChange?: (index: number) => void; // Callback for active tab change
}

const SegmentSlider: React.FC<SegmentSliderProps> = ({
  segments,
  title,
  headerShown = false,
  activeTab = '0',
  onActiveTabChange,
}) => {
  const swiperRef = useRef<any>(null);
  const [segmentValue, setSegmentValue] = useState(activeTab);

  useEffect(() => {
    setSegmentValue(activeTab);
    if (swiperRef.current) {
      swiperRef.current.swiper.slideTo(parseInt(activeTab));
    }
  }, [activeTab]);

  const handleSegmentChange = (e: any) => {
    const newValue = e.detail.value;
    setSegmentValue(newValue);
    if (swiperRef.current) {
      swiperRef.current.swiper.slideTo(parseInt(newValue));
    }
    if (onActiveTabChange) {
      onActiveTabChange(parseInt(newValue));
    }
  };

  const handleSlideChange = (swiper: any) => {
    const index = swiper.activeIndex;
    setSegmentValue(index.toString());
    if (onActiveTabChange) {
      onActiveTabChange(index);
    }
  };

  return (
    <>
      {headerShown && (
        <IonHeader>
          <IonToolbar>
            <IonButtons slot='start'>
              <IonMenuButton />
            </IonButtons>
            <IonTitle>{title}</IonTitle>
          </IonToolbar>
        </IonHeader>
      )}

      <IonHeader>
        <IonToolbar>
          <IonSegment value={segmentValue} onIonChange={handleSegmentChange}>
            {segments.map((segment, index) => (
              <IonSegmentButton key={index} value={index.toString()}>
                <IonLabel>{segment.label}</IonLabel>
              </IonSegmentButton>
            ))}
          </IonSegment>
        </IonToolbar>
      </IonHeader>

      <Swiper
        onSlideChange={handleSlideChange}
        ref={swiperRef}
        slidesPerView={1}
        pagination={{ clickable: true }}
      >
        {segments.map((segment, index) => (
          <SwiperSlide key={index.toString()}>{segment.content}</SwiperSlide>
        ))}
      </Swiper>
    </>
  );
};

export default SegmentSlider;
