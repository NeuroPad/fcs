import React from 'react';
import { IonRouterOutlet } from '@ionic/react';
import { Route, Switch, Redirect } from 'react-router-dom';
import Login from '../pages/Auth/Login/Login';
import Register from '../pages/Auth/Register/Register';
import Root from '../components/Root/Root';
import Onboarding from '../pages/Onboarding/Onboarding';
import ForgotPassword from '../pages/Auth/ForgotPassword/ForgotPassword';

interface AppRoutesProps {
  isAuthenticated: boolean;
}

export default function AppRoutes({ isAuthenticated }: AppRoutesProps) {
  return (
    <IonRouterOutlet>
      <Switch>
        <Route exact path='/onboarding'>
          {isAuthenticated ? <Redirect to='/' /> : <Onboarding />}
        </Route>
        <Route exact path='/login'>
          {isAuthenticated ? <Redirect to='/' /> : <Login />}
        </Route>
        <Route exact path='/register'>
          {isAuthenticated ? <Redirect to='/' /> : <Register />}
        </Route>
        <Route exact path='/forgot-password'>
          {isAuthenticated ? <Redirect to='/' /> : <ForgotPassword />}
        </Route>
        <Route path='/'>
          {isAuthenticated ? <Root /> : <Redirect to='/onboarding' />}
        </Route>
      </Switch>
    </IonRouterOutlet>
  );
}
