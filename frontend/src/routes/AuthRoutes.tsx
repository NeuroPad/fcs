import React from 'react';
import { Route, Redirect, RouteProps } from 'react-router-dom';

interface ProtectedRouteProps extends RouteProps {
  isAuthenticated: boolean;
  redirectPath?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  isAuthenticated,
  redirectPath = '/login',
  ...routeProps
}) => {
  if (!isAuthenticated) {
    return <Redirect to={redirectPath} />;
  }

  return <Route {...routeProps} />;
};

export const PublicRoute: React.FC<ProtectedRouteProps> = ({
  isAuthenticated,
  redirectPath = '/',
  ...routeProps
}) => {
  if (isAuthenticated) {
    return <Redirect to={redirectPath} />;
  }

  return <Route {...routeProps} />;
};