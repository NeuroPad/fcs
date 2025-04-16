import React, { useEffect, useState } from 'react';
import './Bookmarks.css';
import {
  IonAvatar,
  IonCard,
  IonContent,
  IonIcon,
  IonItem,
  IonItemOption,
  IonItemOptions,
  IonItemSliding,
  IonLabel,
  IonList,
  IonModal,
  IonPage,
  IonRadio,
  IonRadioGroup,
  IonText,
} from '@ionic/react';
import Header from '../../components/Header/Header';
import { bookmark, bookmarkOutline, trash } from 'ionicons/icons';
import Container from '../../components/Container/Container';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import EmptyPage from '../../components/Shared/EmptyPage/EmptyPage';
import { setBookmark } from '../../features/controlSlice';

export default function Bookmarks() {
  const dispatch = useAppDispatch();
  const { bookmarkedQuestions } = useAppSelector((state) => state.control);

  const [showModal, setShowModal] = useState<boolean>(false);
  const [content, setContent] = useState<any>();

  const handleRemoveBookmark = (name: any) => {
    // Get the current state of bookmarked questions
    const prevBookmarkedQuestions = bookmarkedQuestions || [];

    // Filter out the question to be removed
    const updatedBookmarks = prevBookmarkedQuestions.filter(
      (bookmarkedQuestion: any) => bookmarkedQuestion?.name !== name
    );

    // Dispatch the updated array to the Redux store
    dispatch(setBookmark(updatedBookmarks));
  };

  useEffect(() => {
    console.log('bmq:', bookmarkedQuestions);
  }, []);

  return (
    <IonPage>
      <Header title='Bookmarks' noBorder />
      <Container padding={false}>
        <>
          {!bookmarkedQuestions?.length ? (
            <EmptyPage text={`You haven't bookmarked any question yet!`} />
          ) : (
            <IonList inset={true}>
              {bookmarkedQuestions?.map((item, index) => (
                <IonItemSliding key={index.toString()}>
                  <IonItem
                    button={true}
                    onClick={() => {
                      setShowModal(true);
                      // console.log(item);
                      setContent(item);
                    }}
                  >
                    <IonIcon color='primary' slot='start' icon={bookmark} />

                    <IonLabel>
                      {`${item.subject.name} ${item.year} Question ${item.question_number}`}
                      <p style={{ marginTop: 3, fontSize: 12 }}>
                        {item.topic.name}
                      </p>
                    </IonLabel>
                  </IonItem>
                  <IonItemOptions slot='end'>
                    <IonItemOption
                      color='danger'
                      expandable={true}
                      onClick={() => handleRemoveBookmark(item.name)}
                    >
                      <IonIcon slot='icon-only' icon={trash}></IonIcon>
                    </IonItemOption>
                  </IonItemOptions>
                </IonItemSliding>
              ))}
            </IonList>
          )}
        </>
      </Container>

      <IonModal isOpen={showModal} onDidDismiss={() => setShowModal(false)}>
        <Header
          title={`${content?.subject?.name} ${content?.year} Question ${content?.question_number}`}
          menu={false}
          onClose={() => setShowModal(false)}
        />

        <IonContent className='ion-padding'>
          {content && (
            <div>
              <IonLabel>
                <p style={{ fontSize: 12, marginBottom: 5 }}>
                  Topic: {content?.topic?.name}
                </p>
                Question:
              </IonLabel>

              <IonText className='question-title'>
                <span dangerouslySetInnerHTML={{ __html: content?.question }} />
              </IonText>

              <IonList>
                <IonRadioGroup value={content?.answer.toLowerCase()}>
                  {content?.options?.map((option: any, ansIndex: number) => (
                    <IonItem key={ansIndex}>
                      <IonRadio
                        key={ansIndex.toString()}
                        value={option.option_letter}
                        slot='start'
                        disabled
                      >
                        <span>
                          <div style={{ width: 30 }}>
                            {option.option_letter}.
                          </div>
                        </span>
                      </IonRadio>
                      <IonLabel>
                        <span
                          dangerouslySetInnerHTML={{
                            __html: option.option_text,
                          }}
                        />
                      </IonLabel>
                    </IonItem>
                  ))}
                </IonRadioGroup>
              </IonList>

              <IonCard className='explanation' color={'medium'}>
                <IonText className='explanation-title'>
                  Question Explanation:
                </IonText>
                <span
                  dangerouslySetInnerHTML={{ __html: content?.explanation }}
                />
              </IonCard>
            </div>
          )}
        </IonContent>
      </IonModal>
    </IonPage>
  );
}
