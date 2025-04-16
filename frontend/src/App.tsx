import React, { useEffect, useState } from 'react';
import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';
import '@ionic/react/css/padding.css';
import '@ionic/react/css/float-elements.css';
import '@ionic/react/css/text-alignment.css';
import '@ionic/react/css/text-transformation.css';
import '@ionic/react/css/flex-utils.css';
import '@ionic/react/css/display.css';
import './theme/variables.css';

import { IonApp, setupIonicReact, IonSpinner } from '@ionic/react';
import { IonReactRouter } from '@ionic/react-router';
import { useAppSelector, useAppDispatch } from './app/hooks';
import { SQLiteHook } from 'react-sqlite-hook';
import AppRoutes from './routes/AppRoutes';
import BottomRoutes from './routes/BottomRoutes';
import { checkAuthStatus } from './features/authSlice'; // Assume this action exists in your auth slice

interface JsonListenerInterface {
  jsonListeners: boolean;
  setJsonListeners: React.Dispatch<React.SetStateAction<boolean>>;
}
interface existingConnInterface {
  existConn: boolean;
  setExistConn: React.Dispatch<React.SetStateAction<boolean>>;
}

export let sqlite: SQLiteHook;
export let existingConn: existingConnInterface;
export let isJsonListeners: JsonListenerInterface;

setupIonicReact();

const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    dispatch(checkAuthStatus()).then(() => setIsInitialized(true));
  }, [dispatch]);

  if (!isInitialized) {
    return (
      <IonApp>
        <div className='ion-text-center' style={{ marginTop: '50vh' }}>
          <IonSpinner color={'primary'} />
        </div>
      </IonApp>
    );
  }

  return (
    <IonApp>
      <IonReactRouter>
        {!isAuthenticated ? (
          <AppRoutes isAuthenticated={isAuthenticated} />
        ) : (
          <BottomRoutes isAuthenticated={isAuthenticated} />
        )}
      </IonReactRouter>
    </IonApp>
  );
};

export default App;
