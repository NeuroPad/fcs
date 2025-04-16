import './Help.css';
import {
  IonCard,
  IonCardTitle,
  IonCol,
  IonGrid,
  IonIcon,
  IonPage,
  IonRow,
} from '@ionic/react';
import React from 'react';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import {
  callOutline,
  chatbubbleEllipsesOutline,
  copyOutline,
  logoWhatsapp,
} from 'ionicons/icons';

interface DataProps {
  icon?: string;
  title: string;
  description: string;
  info: string[] | string;
}

export default function Help() {
  const data: DataProps[] = [
    {
      icon: chatbubbleEllipsesOutline,
      title: 'Chat to support',
      description: "We're here to help",
      info: 'adebisijoe@gmail.com',
    },
    {
      icon: logoWhatsapp,
      title: 'WhatsApp',
      description: 'Mon-Fri from 8am to 5pm',
      info: ['+2349057399928', '+2349057399928'],
    },
    {
      icon: callOutline,
      title: 'Call Us',
      description: 'Mon-Fri from 8am to 5pm',
      info: ['+2349057399928', '+2349057399928'],
    },
  ];

  const CopyInfo = ({ value }: { value: string }) => (
    <div onClick={() => console.log(value)}>
      <IonIcon icon={copyOutline} size='small'></IonIcon>
    </div>
  );

  return (
    <IonPage>
      <Header title='Help' />
      <Container padding>
        <div className='content'>
          <div className='header'>
            <p>Contact Us</p>
            <h2>Get in touch with our team</h2>
            <p>We have the team and know-how to help you.</p>
          </div>

          <IonGrid>
            <IonRow>
              {data.map((item, index) => (
                <IonCol
                  size='12'
                  size-md='12'
                  key={`contact-${index}`} // More descriptive key
                  className='ion-no-padding'
                >
                  <IonCard className='ion-padding ion-align-self-stretch'>
                    <div className='icon'>
                      <IonIcon icon={item.icon} size='small'></IonIcon>
                    </div>

                    <IonCardTitle>
                      <h6>{item.title}</h6>
                    </IonCardTitle>
                    <p>{item.description}</p>

                    <div className='info-container'>
                      {Array.isArray(item.info) ? (
                        item.info.map((infoItem, infoIndex) => (
                          <div
                            className='info'
                            key={`info-${index}-${infoIndex}`} // Unique key combining parent and child indices
                          >
                            {infoItem}
                            <CopyInfo value={infoItem} />
                          </div>
                        ))
                      ) : (
                        <div className='info'>
                          {item.info}
                          <CopyInfo value={item.info} />
                        </div>
                      )}
                    </div>
                  </IonCard>
                </IonCol>
              ))}
            </IonRow>
          </IonGrid>
        </div>
      </Container>
    </IonPage>
  );
}
