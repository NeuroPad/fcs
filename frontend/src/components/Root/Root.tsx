import React, { useEffect } from 'react';
import { IonRouterOutlet, IonSplitPane } from '@ionic/react';
import Drawer from '../Drawer/Drawer';

import { Route, Switch, useLocation } from 'react-router-dom';
import Home from '../../pages/Home/Home';
import Settings from '../../pages/Settings/Settings';

import { useAppDispatch } from '../../app/hooks';

import Bookmarks from '../../pages/Bookmarks/Bookmarks';
import Subscribe from '../../pages/Subscribe/Subscribe';
import Help from '../../pages/Help/Help';
import Terms from '../../pages/Terms/Terms';

import Coummunity from '../../pages/Community/Community';
import Profile from '../../pages/Profile/Profile';

import CareTips from '../../pages/CareTips/CareTips';
import Browse from '../../pages/Browse/Browse';

import KnowledgeBaseManagement from '../../pages/KnowledgeBaseManagement/KnowledgeBaseManagement';
import UserManagement from '../../pages/UserManagement/UserManagement';
import UserActivityLogs from '../../pages/UserActivityLogs/UserActivityLogs';

import EditProfile from '../../pages/Profile/EditProfile/EditProfile';
import ChangePassword from '../../pages/Profile/ChangePassword/ChangePassword';
import Chat from '../../pages/Chat/Chat';

export default function Root() {
  const dispatch = useAppDispatch();
  const location = useLocation();

  return (
    <IonSplitPane contentId='main2'>
       <Drawer />

      <IonRouterOutlet id='main2'>
        <Switch>
          <Route exact path='/' render={() => <Home />} />

          <Route path='/bookmarks' render={() => <Bookmarks />} />
          <Route path='/subscribe' render={() => <Subscribe />} />
          <Route path='/help' render={() => <Help />} />

          <Route path='/community' render={() => <Coummunity />} />
          <Route path='/profile' render={() => <Profile />} />
          <Route path='/terms' render={() => <Terms />} />

          <Route path='/browse' render={() => <Browse />} />
          <Route path='/care-tips' render={() => <CareTips />} />
          <Route path='/settings' render={() => <Settings />} />

          <Route path='/edit-profile' render={() => <EditProfile />} />
          <Route path='/change-password' render={() => <ChangePassword />} />

          <Route path='/knowledgebase' render={() => <KnowledgeBaseManagement />} />
          <Route path='/users' render={() => <UserManagement />} />
          <Route path='/chat' exact render={() => <Chat />} />
          <Route path='/chat/session/:sessionId' render={() => <Chat />} />
          
          <Route exact path='/user-logs/:userId' render={(props) => <UserActivityLogs {...props} />} />
        </Switch>
      </IonRouterOutlet>
    </IonSplitPane>
  );
}
