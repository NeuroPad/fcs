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

// Add QueryMode type
type QueryMode = 'normal' | 'graph' | 'combined';

const Chat: React.FC = () => {
  const dispatch = useAppDispatch();
  const { selectedChat, chatId } = useAppSelector((state) => state.chat);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  // Changed default mode to 'graph' instead of 'normal'
  const [queryMode, setQueryMode] = useState<QueryMode>('graph');

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
      // Store the message before clearing the input
      const messageToSend = newMessage;
      // Clear the input immediately for better user experience
      setNewMessage('');
      
      try {
        // Add user message to the chat immediately
        dispatch(addUserMessage(messageToSend));
        
        if (chatId) {
          await dispatch(sendMessage({ 
            sessionId: chatId.toString(), // Convert number to string
            message: messageToSend,
            mode: queryMode 
          })).unwrap();
        } else {
          await dispatch(createChat({ 
            question: messageToSend,
            mode: queryMode 
          })).unwrap();
        }
      } catch (error) {
        console.error('Error sending message:', error);
      } finally {
        setIsTyping(false);
      }
    }
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
            </div>
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
    </IonPage>
  );
};

export default Chat;