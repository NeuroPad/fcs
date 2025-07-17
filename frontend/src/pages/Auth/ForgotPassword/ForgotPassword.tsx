import React, { useState } from 'react';
import { IonButton, IonImg, IonPage, IonToast } from '@ionic/react';
import { useForm } from 'react-hook-form';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { Link } from 'react-router-dom';
import Container from '../../../components/Container/Container';


export default function ForgotPassword() {
  const [loading, setLoading] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const schema = yup.object({
    email: yup.string().email().required(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: '',
    },
    resolver: yupResolver(schema),
  });

  const handleLogin = async (data: any) => {
    setLoading(false);
  };

  return (
    <IonPage>
      <Container width='100%'>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            maxWidth: '100%',
            width: '600px',
            justifyContent: 'center',
            height: 'calc(100vh -  40px)',
            margin: '0 auto',
            padding: '0 20px',
          }}
        >
          <IonImg
            style={{
              width: 100,
              marginBottom: 20,
            }}
            src={`/assets/Tevo.png`}
          />

          <h5>Forgot password?</h5>

          <p
            style={{
              textAlign: 'center',
              opacity: 0.7,
            }}
          >
            No worries, we'll send your reset instructions.
          </p>

          <form onSubmit={handleSubmit(handleLogin)} style={{ width: '100%' }}>
            <div className='custom-input-wrapper'>
              <input
                placeholder='Enter your email'
                {...register('email')}
                className='custom-input'
              />
              <p className='custom-input-error'>{errors.email?.message}</p>
            </div>

            <IonButton
              className='ion-margin-top ion-button-reset'
              type='submit'
              expand='full'
              shape='round'
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Reset password'}
            </IonButton>
          </form>

          <div>
            <p>
              <Link to='/login'>Back to Login</Link>
            </p>
          </div>
        </div>

        <IonToast
          isOpen={showToast}
          onDidDismiss={() => setShowToast(false)}
          message='User logged in successfully'
          duration={2000}
        />
      </Container>
    </IonPage>
  );
}
