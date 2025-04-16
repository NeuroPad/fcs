import React, { useEffect, useState } from 'react';
import './Bookmarks.css';
import {
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
import { bookmark, trash, leaf } from 'ionicons/icons';
import Container from '../../components/Container/Container';
import { useAppSelector } from '../../app/hooks';
import EmptyPage from '../../components/Shared/EmptyPage/EmptyPage';
import { get, set } from '../../services/storage';

export default function Bookmarks() {
  const { user } = useAppSelector((state) => state.user);

  const [bookmarkedQuestions, setBookmarkedQuestions] = useState<any[]>([]);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [content, setContent] = useState<any>();

  const handleRemoveBookmark = async (questionNumber: any) => {
    // Get the current state of bookmarked questions
    const prevBookmarkedQuestions = bookmarkedQuestions || [];

    // Filter out the question to be removed
    const updatedBookmarks = prevBookmarkedQuestions.filter(
      (bookmarkedQuestion: any) =>
        bookmarkedQuestion?.question_no !== questionNumber
    );

    const bookmarkId = `tevo-${user?.email}-bookmarks`;

    await set(bookmarkId, updatedBookmarks);
    setBookmarkedQuestions(updatedBookmarks);
  };

  useEffect(() => {
    (async () => {
      const bookmarkId = `tevo-${user?.email}-bookmarks`;
      // Get the current state of bookmarked questions
      const prevBookmarkedQuestions = (await get(bookmarkId)) || [];
      // console.log('Here: ', prevBookmarkedQuestions, bookmarkedQuestions);
      setBookmarkedQuestions(prevBookmarkedQuestions);
    })();
  }, [user]);

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
                    <IonIcon color='primary' slot='start' icon={leaf} />

                    <IonLabel>
                      {`${item?.subject || ''} ${item?.year || ''} Question ${item.question_no
                        }`}
                      <p style={{ marginTop: 3, fontSize: 12 }}>{item.topic}</p>
                    </IonLabel>
                  </IonItem>
                  <IonItemOptions slot='end'>
                    <IonItemOption
                      color='danger'
                      expandable={true}
                      onClick={() => handleRemoveBookmark(item.question_no)}
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
          title={`${content?.subject || ''} ${content?.year || ''} Question ${content?.question_no
            }`}
          menu={false}
          onClose={() => setShowModal(false)}
        />

        <IonContent className='ion-padding'>
          {content && (
            <div>
              <IonLabel>
                <p style={{ fontSize: 12, marginBottom: 5 }}>
                  Topic: {content?.topic}
                </p>
                Question:
              </IonLabel>

              <IonText className='question-title'>
                <span dangerouslySetInnerHTML={{ __html: content?.question }} />
              </IonText>

              <IonList>
                <IonRadioGroup value={content?.answer.toLowerCase()}>
                  {content?.option_a && (
                    <QuestionOption letter='a' value={content?.option_a} />
                  )}

                  {content?.option_b && (
                    <QuestionOption letter='b' value={content?.option_b} />
                  )}

                  {content?.option_c && (
                    <QuestionOption letter='c' value={content?.option_c} />
                  )}

                  {content?.option_d && (
                    <QuestionOption letter='d' value={content?.option_d} />
                  )}

                  {content?.option_e && (
                    <QuestionOption letter='e' value={content?.option_e} />
                  )}

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

const QuestionOption = ({
  value,
  letter,
}: {
  value: string;
  letter: string;
}) => {
  return (
    <IonItem>
      <IonRadio value={letter} slot='start' disabled>
        <span>
          <div style={{ width: 30 }}>{letter}.</div>
        </span>
      </IonRadio>
      <IonLabel>
        <span
          dangerouslySetInnerHTML={{
            __html: `${value} 
          <style>span{font-family: inherit !important;}</style>
          `,
          }}
        />
      </IonLabel>
    </IonItem>
  );
};
