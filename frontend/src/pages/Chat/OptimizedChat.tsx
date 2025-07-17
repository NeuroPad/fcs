import {
  IonContent,
  IonPage,
  IonButton,
  IonIcon,
  IonInput,
  IonSpinner,
  IonChip,
  IonLabel,
  IonToast,
} from '@ionic/react';
import { sendOutline, refreshOutline, alertCircleOutline } from 'ionicons/icons';
import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  sendMessageOptimistic,
  getChatByIdCached,
  createChatOptimized,
  setMessages,
  clearError,
  retryFailedMessage,
} from '../../features/optimizedChatSlice';
import MarkdownLatexRenderer from '../../components/AI/MarkdownLatexRenderer';
import './Chat.css';
import Header from '../../components/Header/Header';
import { useParams, useHistory } from 'react-router-dom';
import ContradictionBox from '../../components/AI/ContradictionBox';
import ReasoningNodes from '../../components/AI/ReasoningNodes';

// Add QueryMode type
type QueryMode = 'normal' | 'graph' | 'combined';

interface ChatMessage {
  id?: string;
  role: string;
  content: string;
  images?: string[];
  sources?: string[];
  reasoning_nodes?: Array<{
    uuid: string;
    name: string;
    salience?: number;
    confidence?: number;
    summary?: string;
    node_type?: string;
    used_in_context?: string;
  }>;
  created_at?: string;
  isOptimistic?: boolean;
  isError?: boolean;
}

// Memoized components for better performance
const MemoizedMarkdownRenderer = React.memo(MarkdownLatexRenderer);
const MemoizedReasoningNodes = React.memo(ReasoningNodes);

// Lazy loading image component
const LazyImage: React.FC<{ src: string; alt: string; className?: string }> = React.memo(({ src, alt, className }) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setLoaded(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={imgRef} className={className}>
      {loaded ? (
        <img 
          src={src} 
          alt={alt} 
          onError={() => setError(true)}
          style={{ display: error ? 'none' : 'block' }}
        />
      ) : (
        <div className="image-placeholder">Loading...</div>
      )}
    </div>
  );
});

// Memoized message component
const ChatMessageComponent: React.FC<{ 
  message: ChatMessage; 
  onRetry?: (id: string) => void;
}> = React.memo(({ message, onRetry }) => {
  const messageClass = useMemo(() => {
    let classes = `chat-message ${message.role}`;
    if (message.isOptimistic) classes += ' optimistic';
    if (message.isError) classes += ' error';
    return classes;
  }, [message.role, message.isOptimistic, message.isError]);

  return (
    <div className={messageClass}>
      <MemoizedMarkdownRenderer content={message.content} />
      
      {message.isError && (
        <div className="error-actions">
          <IonButton 
            size="small" 
            fill="clear" 
            color="danger"
            onClick={() => message.id && onRetry?.(message.id)}
          >
            <IonIcon icon={refreshOutline} slot="start" />
            Retry
          </IonButton>
        </div>
      )}

      {message.images && message.images.length > 0 && (
        <div className="chat-images">
          {message.images.map((img, idx) => (
            <LazyImage 
              key={idx} 
              src={img} 
              alt={`Chat Image ${idx}`} 
              className="chat-image" 
            />
          ))}
        </div>
      )}

      {message.sources && message.sources.length > 0 && (
        <div className="chat-sources">
          <strong>Sources:</strong>
          <ul>
            {message.sources.map((src, idx) => (
              <li key={idx} dangerouslySetInnerHTML={{ __html: src }} />
            ))}
          </ul>
        </div>
      )}

      {message.reasoning_nodes && message.reasoning_nodes.length > 0 && (
        <MemoizedReasoningNodes 
          nodes={message.reasoning_nodes} 
          title={`Reasoning Nodes Used (${message.reasoning_nodes.length})`}
        />
      )}
    </div>
  );
});

// Virtualized message list for large chat histories
const VirtualizedMessageList: React.FC<{
  messages: ChatMessage[];
  onRetry: (id: string) => void;
}> = React.memo(({ messages, onRetry }) => {
  const listRef = useRef<List>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (listRef.current && messages.length > 0) {
      listRef.current.scrollToItem(messages.length - 1, 'end');
    }
  }, [messages.length]);

  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <ChatMessageComponent 
        message={messages[index]} 
        onRetry={onRetry}
      />
    </div>
  ), [messages, onRetry]);

  // Use regular rendering for small message counts
  if (messages.length < 20) {
    return (
      <div className="messages-container">
        {messages.map((msg, index) => (
          <ChatMessageComponent 
            key={msg.id || index} 
            message={msg} 
            onRetry={onRetry}
          />
        ))}
      </div>
    );
  }

  return (
    <List
      ref={listRef}
      height={600}
      width="100%"
      itemCount={messages.length}
      itemSize={120}
      className="virtualized-messages"
    >
      {Row}
    </List>
  );
});

// Mode selector component
const ModeSelector: React.FC<{
  queryMode: QueryMode;
  onModeChange: (mode: QueryMode) => void;
}> = React.memo(({ queryMode, onModeChange }) => (
  <div className="mode-selector">
    <IonChip 
      color={queryMode === 'normal' ? 'primary' : 'medium'}
      onClick={() => onModeChange('normal')}
    >
      <IonLabel>Normal RAG</IonLabel>
    </IonChip>
    <IonChip 
      color={queryMode === 'graph' ? 'primary' : 'medium'}
      onClick={() => onModeChange('graph')}
    >
      <IonLabel>Graph RAG</IonLabel>
    </IonChip>
    <IonChip 
      color={queryMode === 'combined' ? 'primary' : 'medium'}
      onClick={() => onModeChange('combined')}
    >
      <IonLabel>Combined Mode</IonLabel>
    </IonChip>
  </div>
));

const OptimizedChat: React.FC = () => {
  const dispatch = useAppDispatch();
  const history = useHistory();
  const { selectedChat, chatId, isTyping, isLoading, error } = useAppSelector((state) => state.optimizedChat);
  
  // Get sessionId from URL if present
  const { sessionId } = useParams<{ sessionId?: string }>();

  const [newMessage, setNewMessage] = useState('');
  const [queryMode, setQueryMode] = useState<QueryMode>('normal');
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  
  // Debounced input to prevent excessive re-renders
  const [debouncedMessage, setDebouncedMessage] = useState('');
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMessage(newMessage);
    }, 300);
    
    return () => clearTimeout(timer);
  }, [newMessage]);

  // Fetch chat by sessionId on mount or when sessionId changes
  useEffect(() => {
    if (sessionId) {
      dispatch(getChatByIdCached(Number(sessionId)));
    }
  }, [dispatch, sessionId]);

  // Navigate to new chat route when a new chat is created
  useEffect(() => {
    if (chatId && !sessionId) {
      history.push(`/chat/session/${chatId}`);
    }
  }, [chatId, sessionId, history]);

  // Handle errors with toast notifications
  useEffect(() => {
    if (error) {
      setToastMessage(error);
      setShowToast(true);
      dispatch(clearError());
    }
  }, [error, dispatch]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendNewMessage();
    }
  }, [newMessage, isLoading, chatId, queryMode]);

  const sendNewMessage = useCallback(async () => {
    if (newMessage.trim() !== '' && !isLoading) {
      const messageToSend = newMessage;
      setNewMessage('');
      
      try {
        if (chatId) {
          await dispatch(sendMessageOptimistic({ 
            sessionId: chatId.toString(),
            message: messageToSend,
            mode: queryMode 
          })).unwrap();
        } else {
          await dispatch(createChatOptimized({ 
            question: messageToSend,
            mode: queryMode 
          })).unwrap();
        }
      } catch (error) {
        console.error('Error sending message:', error);
      }
    }
  }, [newMessage, isLoading, chatId, queryMode, dispatch]);

  const handleRetryMessage = useCallback((messageId: string) => {
    dispatch(retryFailedMessage(messageId));
    // Re-send the message
    const failedMessage = selectedChat.find((msg: any) => msg.id === messageId);
    if (failedMessage) {
      dispatch(sendMessageOptimistic({
        sessionId: chatId?.toString() || '',
        message: failedMessage.content,
        mode: queryMode
      }));
    }
  }, [dispatch, selectedChat, chatId, queryMode]);

  const handleModeChange = useCallback((mode: QueryMode) => {
    setQueryMode(mode);
  }, []);

  // Memoize expensive computations
  const messageCount = useMemo(() => selectedChat?.length || 0, [selectedChat]);
  const hasMessages = useMemo(() => messageCount > 0, [messageCount]);
  
  return (
    <IonPage>
      <Header title="FCS Chat (Optimized)" />
      <div className="chat-layout">
        <div className="chat-interface-container">
          <ModeSelector queryMode={queryMode} onModeChange={handleModeChange} />
          
          <IonContent className="chat-content">
            {hasMessages ? (
              <VirtualizedMessageList 
                messages={selectedChat} 
                onRetry={handleRetryMessage}
              />
            ) : (
              <div className="empty-chat">
                <p>Start a conversation...</p>
              </div>
            )}
            
            {isTyping && (
              <div className="typing-indicator">
                <IonSpinner name="dots" />
                <span>AI is thinking...</span>
              </div>
            )}
          </IonContent>

          <div className="chat-input-container">
            <div className="input-wrapper">
              <img src="/assets/brain-icon.png" alt="AI" className="brain-icon" />
              <IonInput
                value={newMessage}
                onIonInput={(e) => setNewMessage(String(e.detail.value!))}
                onKeyDown={handleKeyPress}
                placeholder="What's on your mind?..."
                className="chat-input"
                disabled={isLoading}
              />
              <IonButton 
                className="send-button" 
                onClick={sendNewMessage} 
                disabled={isLoading || !newMessage.trim()}
              >
                {isLoading ? (
                  <IonSpinner name="dots" />
                ) : (
                  <IonIcon icon={sendOutline} />
                )}
              </IonButton>
            </div>
            
            {debouncedMessage && (
              <div className="message-preview">
                Preview: {debouncedMessage.slice(0, 50)}...
              </div>
            )}
          </div>
        </div>
      </div>
      
      <IonToast
        isOpen={showToast}
        onDidDismiss={() => setShowToast(false)}
        message={toastMessage}
        duration={3000}
        color="danger"
        icon={alertCircleOutline}
      />
    </IonPage>
  );
};

export default OptimizedChat;