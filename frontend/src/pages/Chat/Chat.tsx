import {
  IonContent,
  IonPage,
  IonButton,
  IonIcon,
  IonInput,
  IonSpinner,
} from '@ionic/react';
import { sendOutline } from 'ionicons/icons';
import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  createChat,
  getChatById,
  sendMessage,
  setMessages,
  addUserMessage,
} from '../../features/chatSlice';
import MarkdownLatexRenderer from '../../components/AI/MarkdownLatexRenderer';
import './Chat.css';
import { color } from 'html2canvas/dist/types/css/types/color';
import Header from '../../components/Header/Header';
import { IonChip, IonLabel } from '@ionic/react';
import { useParams, useHistory } from 'react-router-dom';
import ContradictionBox from '../../components/AI/ContradictionBox';

// Add QueryMode type
type QueryMode = 'normal' | 'graph' | 'combined';

type ExpressionType = 'contradiction' | 'reinforcement' | 'reflection' | 'track';

const expressionScenarios = [
  {
    previous: 'Plants need lots of sunlight.',
    current: 'Plants should be kept in shade.',
    mode: 'contradiction' as ExpressionType,
    header: 'Contradiction Detected!',
    primary: 'Change my view to the new idea',
    secondary: 'Track this as a new idea',
  },
  {
    previous: 'Exercise is important for health.',
    current: 'Regular exercise has improved my mood.',
    mode: 'reinforcement' as ExpressionType,
    header: 'Reinforcement Detected!',
    primary: 'Acknowledge reinforcement',
    secondary: 'Track as repeated idea',
  },
  {
    previous: 'I used to dislike reading.',
    current: 'Now I enjoy reading every day.',
    mode: 'reflection' as ExpressionType,
    header: 'Reflection Opportunity!',
    primary: 'Reflect on this change',
    secondary: 'Track as new perspective',
  },
  {
    previous: 'I have never tried meditation.',
    current: 'I want to start meditating.',
    mode: 'track' as ExpressionType,
    header: 'New Idea Detected!',
    primary: 'Adopt this new idea',
    secondary: 'Just track, don\'t change view',
  },
];

function getRandomScenario() {
  const idx = Math.floor(Math.random() * expressionScenarios.length);
  return expressionScenarios[idx];
}

const Chat: React.FC = () => {
  const dispatch = useAppDispatch();
  const history = useHistory();
  const { selectedChat, chatId } = useAppSelector((state) => state.chat);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  // Get sessionId from URL if present
  const { sessionId } = useParams<{ sessionId?: string }>();

  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  // Changed default mode to 'graph' instead of 'normal'
  const [queryMode, setQueryMode] = useState<QueryMode>('normal');

  // Expression state for demo: randomly pick a scenario on load
  const [expression, setExpression] = useState(() => {
    const scenario = getRandomScenario();
    return {
      ...scenario,
      visible: true,
    };
  });

  // Fetch chat by sessionId on mount or when sessionId changes
  useEffect(() => {
    if (sessionId) {
      dispatch(getChatById(Number(sessionId)));
    }
  }, [dispatch, sessionId]);

  // Navigate to new chat route when a new chat is created
  useEffect(() => {
    if (chatId && !sessionId) {
      history.push(`/chat/session/${chatId}`);
    }
  }, [chatId, sessionId, history]);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [selectedChat]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendNewMessage();
    }
  };

  const sendNewMessage = async () => {
    if (newMessage.trim() !== '' && !isTyping) {
      setIsTyping(true);
      const messageToSend = newMessage;
      setNewMessage('');
      try {
        dispatch(addUserMessage(messageToSend));
        if (chatId) {
          await dispatch(sendMessage({ 
            sessionId: chatId.toString(),
            message: messageToSend,
            mode: queryMode 
          })).unwrap();
        } else {
          await dispatch(createChat({ 
            question: messageToSend,
            mode: queryMode 
          })).unwrap();
        }
        // Simulate contradiction or new idea event (alternate for demo)
        setExpression((prev) => ({
          ...prev,
          visible: true,
        }));
      } catch (error) {
        console.error('Error sending message:', error);
      } finally {
        setIsTyping(false);
      }
    }
  };

  // Handlers for ContradictionBox actions
  const handleChangeView = () => {
    setExpression((c) => ({ ...c, visible: false }));
    // Optionally, show a toast or feedback
  };
  const handleTrackNewIdea = () => {
    setExpression((c) => ({ ...c, visible: false }));
    // Optionally, show a toast or feedback
  };

  // Add mode selector component
  // Mode selector component is commented out but preserved for future use
  /*
  const ModeSelector = () => (
    <div style={{ 
      display: 'flex', 
      gap: '8px', 
      padding: '8px 16px',
      overflowX: 'auto',
      backgroundColor: 'var(--ion-background-color)'
    }}>
      <IonChip 
        color={queryMode === 'normal' ? 'primary' : 'medium'}
        onClick={() => setQueryMode('normal')}
      >
        <IonLabel>Normal RAG</IonLabel>
      </IonChip>
      <IonChip 
        color={queryMode === 'graph' ? 'primary' : 'medium'}
        onClick={() => setQueryMode('graph')}
      >
        <IonLabel>Graph RAG</IonLabel>
      </IonChip>
      <IonChip 
        color={queryMode === 'combined' ? 'primary' : 'medium'}
        onClick={() => setQueryMode('combined')}
      >
        <IonLabel>Combined Mode</IonLabel>
      </IonChip>
    </div>
  );
  */

  return (
    <IonPage>
      <Header title="FCS Chat" />
      <div className="chat-layout">
        <div className="chat-interface-container">
          {/* ExpressionBox appears above chat input when triggered */}
          <ContradictionBox
            previousStatement={expression.previous}
            currentStatement={expression.current}
            mode={expression.mode === 'track' ? 'track' : 'contradiction'}
            visible={expression.visible}
            header={expression.header}
            onChangeView={handleChangeView}
            onTrackNewIdea={handleTrackNewIdea}
          />
          {/* Commented out ModeSelector component */}
          {/* <ModeSelector /> */}
          <IonContent className="chat-content">
            <div className="messages-container">
              {selectedChat?.map((msg, index) => (
                <div key={index} className={`chat-message ${msg.role}`}>
                  <MarkdownLatexRenderer content={msg.content} />

                  {msg.images && msg.images.length > 0 && (
                    <div className="chat-images">
                      {msg.images.map((img, idx) => (
                        <img key={idx} src={img} alt={`Chat Image ${idx}`} className="chat-image" />
                      ))}
                    </div>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="chat-sources">
                      <strong>Sources:</strong>
                      <ul>
                        {msg.sources.map((src, idx) => (
                          <li key={idx} dangerouslySetInnerHTML={{ __html: src }} />
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
              {isTyping && (
                <div className="typing-indicator">
                  <p>Typing...</p>
                </div>
              )}
            </div>
            <div ref={bottomRef} />
          </IonContent>

          <div className="chat-input-container">
            <div className="input-wrapper">
              <img src="/assets/brain-icon.png" alt="AI" className="brain-icon" />
              <IonInput
                value={newMessage}
                onIonInput={(e) => setNewMessage(String(e.detail.value!))}
                onKeyDown={handleKeyPress}
                placeholder="What's on your mind ?..."
                className="chat-input"
              />
              <IonButton 
                className="send-button" 
                onClick={sendNewMessage} 
                disabled={isTyping}
              >
                {isTyping ? <IonSpinner name="dots" /> : <IonIcon  icon={sendOutline} />}
              </IonButton>
            </div>
          </div>
        </div>
      </div>
    </IonPage>
  );
};

export default Chat;