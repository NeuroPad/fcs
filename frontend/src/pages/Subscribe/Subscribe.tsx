import React, { useEffect, useRef, useState } from 'react';
import EmptyPage from '../../components/Shared/EmptyPage/EmptyPage';
import {
  IonHeader,
  IonLabel,
  IonPage,
  IonSegment,
  IonSegmentButton,
  IonToolbar,
} from '@ionic/react';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { Swiper, SwiperSlide } from 'swiper/react';
import 'swiper/swiper-bundle.min.css';
import PinCode from './Tab/PinCode';
import OnlinePayment from './Tab/OnlinePayment';

const tabOptions = [
  {
    label: 'PIN Code',
    content: PinCode,
  },
  {
    label: 'Online Payment',
    content: OnlinePayment,
  },
];

export default function Subscribe() {
  const activeTab = '1';
  const swiperRef = useRef<any>(null);
  const [tabValue, setTabValue] = useState(activeTab);

  useEffect(() => {
    setTabValue(activeTab);
    if (swiperRef.current) {
      swiperRef.current.swiper.slideTo(parseInt(activeTab));
    }
  }, [activeTab]);

  const handleTabChange = (e: any) => {
    const newValue = e.detail.value;
    setTabValue(newValue);
    if (swiperRef.current) {
      swiperRef.current.swiper.slideTo(parseInt(newValue));
    }
  };

  const handleSlideChange = (swiper: any) => {
    const index = swiper.activeIndex;
    setTabValue(index.toString());
  };

  return (
    <IonPage>
      <Header title='Subscribe' />

      <Container padding={false}>
        {false && <EmptyPage text='No subscriptions' />}

        <IonHeader>
          <IonToolbar>
            <IonSegment value={tabValue} onIonChange={handleTabChange}>
              {tabOptions.map((option, index) => (
                <IonSegmentButton key={index} value={index.toString()}>
                  <IonLabel>{option.label}</IonLabel>
                </IonSegmentButton>
              ))}
            </IonSegment>
          </IonToolbar>
        </IonHeader>

        <Swiper
          ref={swiperRef}
          autoHeight={true}
          slidesPerView={1}
          onSlideChange={handleSlideChange}
        >
          {tabOptions.map((option, index) => (
            <SwiperSlide key={index.toString()}>{option.content}</SwiperSlide>
          ))}
        </Swiper>
      </Container>
    </IonPage>
  );
}
