import React from 'react';
import { IonModal, IonButton, IonHeader, IonToolbar, IonTitle, IonContent } from '@ionic/react';
import MarkdownLatexRenderer from './MarkdownLatexRenderer';

interface QuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  question: string;
  solution: string;
}

const QuestionModal: React.FC<QuestionModalProps> = ({ isOpen, onClose, question, solution }) => {
  return (
    <IonModal isOpen={isOpen}>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Question and Solution</IonTitle>
          <IonButton slot="end" onClick={onClose}>Close</IonButton>
        </IonToolbar>
      </IonHeader>
      <IonContent className="ion-padding">
        <h2>Question</h2>
          <MarkdownLatexRenderer content={question} />
        <h2>Solution</h2>
        <MarkdownLatexRenderer content={solution} />
      </IonContent>
    </IonModal>
  );
};

export default QuestionModal;
