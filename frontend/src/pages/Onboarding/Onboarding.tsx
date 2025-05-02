import React from 'react';
import { IonContent, IonButton, IonPage } from '@ionic/react';
import { useHistory } from 'react-router';
import { set } from '../../services/storage';
import { Swiper, SwiperSlide, useSwiper } from 'swiper/react';
import { Pagination } from 'swiper';
import 'swiper/swiper-bundle.min.css';
import './Onboarding.css';

const Onboarding = () => {
  const history = useHistory();
  
  const finishSlide = async () => {
    await set('first_time', true);
    history.push('/login');
  };

  const slides = [
    {
      title: 'Shape Your Beliefs',
      description: 'Upload articles, books, thoughts, or documents that influence your worldview — PDFs, text, or web clips are welcome.',
      image: '/assets/images/onboarding/docs.png'
    },
    {
      title: 'Connect Your Thoughts',
      description: 'Everything you share helps us understand how your beliefs connect and grow — like a living map of your thinking.',
      image: '/assets/images/onboarding/knowledgebase.png'
    },
    {
      title: 'Explore Your Thinking',
      description: 'Ask, challenge, and explore your beliefs using intelligent retrieval and reasoning powered by the FGM engine.',
      image: '/assets/images/onboarding/chat.png'
    },
  ];

  const NextButton = () => {
    const swiper = useSwiper();
    return (
      <IonButton 
        className="next-button"
        onClick={() => swiper.slideNext()}
        fill="clear"
        color={'primary'}
      >
        Next
      </IonButton>
    );
  };

  return (
    <IonPage>
      <IonContent>
        <Swiper
          pagination={{
            clickable: true,
          }}
          modules={[Pagination]}
          className="onboarding-swiper"
        >
          {slides.map((slide, index) => (
            <SwiperSlide key={`slide-${index}`}>
              <div className="slide-content">
                <div className="image-container">
                  <img src={slide.image} alt={slide.title} />
                </div>
                
                <div className="text-content">
                  <h2>{slide.title}</h2>
                  <p>{slide.description}</p>
                </div>

                {index === slides.length - 1 ? (
                  <IonButton 
                    className="get-started-button"
                    onClick={finishSlide}
                    expand="block"
                  >
                    Get Started
                  </IonButton>
                ) : (
                  <NextButton />
                )}
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </IonContent>
    </IonPage>
  );
};

export default Onboarding;