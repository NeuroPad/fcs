import React, { useState, useEffect } from 'react';
import {
  IonContent,
  IonHeader,
  IonIcon,
  IonImg,
  IonItem,
  IonLabel,
  IonList,
  IonMenu,
  IonMenuToggle,
  IonToolbar,
  IonButton,
  IonPopover
} from '@ionic/react';
import { addOutline } from 'ionicons/icons';
import { useLocation, useHistory } from 'react-router';
import { libraryOutline, documentOutline, settingsOutline, medkitOutline } from 'ionicons/icons';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { logout } from '../../features/authSlice';
import { getChatById, setMessages, getUserChats } from '../../features/chatSlice';
import './Drawer.css';
import { chatbubbleOutline, chatboxEllipses } from 'ionicons/icons';
import { color } from 'html2canvas/dist/types/css/types/color';

import { ellipsisVertical, trash } from 'ionicons/icons';
import { deleteChat } from '../../features/chatSlice';



export default function Drawer() {
  const location = useLocation();
  const history = useHistory();
  const dispatch = useAppDispatch();

  const { chats, chatId } = useAppSelector((state) => state.chat);
  const isChatRoute = location.pathname.startsWith('/chat');

  // Refresh chat list when component mounts or when on chat route
  useEffect(() => {
    if (isChatRoute) {
      dispatch(getUserChats());
    }
  }, [dispatch, isChatRoute]);


  // Regular navigation items
  const appPages = [
    {
      title: 'Home',
      url: '/',
      icon: 'assets/svg/home.svg',
    },
    {
      title: 'Knowledge Base',
      url: '/knowledgebase',
      icon: libraryOutline,
    },
    // {
    //   title: 'User Management',
    //   url: '/users',
    //   icon: peopleOutline,
    // },
    {
      title: 'System Settings',
      url: '/settings',
      icon: settingsOutline,
    },
    // {
    //   title: 'Analytics',
    //   url: '/care-tips',
    //   icon: medkitOutline,
    // },
    {
      title: 'Help Desk',
      url: '/help',
      icon: 'assets/svg/device-message.svg',
    },
    {
      title: 'Chat',
      url: '/chat',
      icon: 'assets/svg/device-message.svg',
    },
    {
      title: 'Log Out',
      icon: 'assets/svg/logout-1.svg',
      onClick: () => {
        dispatch(logout());
      }
    }
  ];


  // Add state for popover
  const [popoverState, setPopoverState] = useState<{
    showPopover: boolean;
    event: Event | undefined;
    chatId: number | undefined;
  }>({
    showPopover: false,
    event: undefined,
    chatId: undefined,
  });


  const handleNewChat = () => {
    dispatch(setMessages([]));
    history.push('/chat');
  };

  // Add handler for delete
  const handleDelete = async (chatId: number) => {
    await dispatch(deleteChat(chatId));
    setPopoverState({ showPopover: false, event: undefined, chatId: undefined });
    // Refresh chat list after deletion
    dispatch(getUserChats());
  };

  const handleChatClick = (chat: any) => {
    history.push(`/chat/session/${chat.id}`);
  };

  return (
    <IonMenu contentId='main2' type='overlay'>
      <IonHeader collapse='fade' className='ion-no-border'>
        <IonToolbar>
          <IonImg
            style={{
              width: 80,
              paddingLeft: 20,
              paddingTop: 20,
            }}
            src={`/assets/graphraglogo.png`}
          />
        </IonToolbar>
      </IonHeader>
      <IonContent>
        {isChatRoute ? (
          <>
            <IonButton
              expand="block"
              fill="solid"
              color="primary"
              className="ion-margin-horizontal"
              onClick={handleNewChat}
            >
              <IonIcon style={{color:"#fff"}} icon={chatboxEllipses} slot="start" />
              New Chat
            </IonButton>
            <IonList lines='none'>
              {chats?.map((chat) => (
                <IonMenuToggle key={chat.id} autoHide={false}>
                  <IonItem
                    button
                    detail={false}
                    onClick={() => handleChatClick(chat)}
                    className={chatId === chat.id ? 'selected' : ''}
                  >
                    <IonIcon
                      icon={chatbubbleOutline}
                      slot="start"
                      color={chatId === chat.id ? 'primary' : 'medium'}
                    />
                    <IonLabel>
                      {chat.messages && chat.messages.length > 0
                        ? `${chat.messages[0].content.substring(0, 30)}...`
                        : 'New Chat'}
                      <p className="chat-date">
                        {new Date(chat.created_at).toLocaleDateString()}
                      </p>
                    </IonLabel>
                    <IonButton
                      fill="clear"
                      slot="end"
                      onClick={(e: any) => {
                        e.stopPropagation();
                        setPopoverState({
                          showPopover: true,
                          event: e,
                          chatId: chat.id,
                        });
                      }}
                    >
                      <IonIcon icon={ellipsisVertical} />
                    </IonButton>
                  </IonItem>
                </IonMenuToggle>
              ))}
            </IonList>

            <IonPopover
              isOpen={popoverState.showPopover}
              event={popoverState.event}
              onDidDismiss={() =>
                setPopoverState({
                  showPopover: false,
                  event: undefined,
                  chatId: undefined,
                })
              }
            >
              <IonList>
                <IonItem
                  button
                  onClick={() => {
                    if (popoverState.chatId) {
                      handleDelete(popoverState.chatId);
                    }
                  }}
                >
                  <IonIcon slot="start" icon={trash} color="danger" />
                  <IonLabel color="danger">Delete Chat</IonLabel>
                </IonItem>
              </IonList>
            </IonPopover>
          </>
        ) : (
          // Regular Navigation List
          <IonList lines='none'>
            {appPages.map((appPage, index) => (
              <IonMenuToggle key={index} autoHide={false}>
                <IonItem
                  routerDirection='none'
                  detail={false}
                  routerLink={appPage.url}
                  onClick={appPage.onClick}
                  className={location.pathname === appPage.url ? 'selected' : ''}
                >
                  <IonIcon
                    src={appPage.icon}
                    slot='start'
                    color={location.pathname === appPage.url ? 'primary' : 'medium'}
                  />
                  <IonLabel>{appPage.title}</IonLabel>
                </IonItem>
              </IonMenuToggle>
            ))}
          </IonList>
        )}
      </IonContent>
    </IonMenu>
  );
}
