import 'reflect-metadata';
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// import * as serviceWorkerRegistration from './serviceWorkerRegistration';
// import reportWebVitals from './reportWebVitals';
import { Provider } from 'react-redux';
import { store } from './app/store';
import { getTokenFromStorage } from './features/authSlice';
import { getUserDataFromStorage } from './features/userSlice';
import { loadDarkMode } from './features/themeSlice';

store.dispatch(getTokenFromStorage());
store.dispatch(getUserDataFromStorage());
store.dispatch(loadDarkMode());

const container = document.getElementById('root');
const root = createRoot(container!);
root.render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>
);
