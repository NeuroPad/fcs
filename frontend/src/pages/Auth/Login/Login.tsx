import React, { useState } from 'react';
import { IonButton, IonIcon, IonImg, IonPage, IonToast } from '@ionic/react';
import { useAppDispatch } from '../../../app/hooks';
import { loginUser } from '../../../features/authSlice';
import { useForm } from 'react-hook-form';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { Link } from 'react-router-dom';
import Container from '../../../components/Container/Container';
import { eyeOutline, eyeOffOutline } from 'ionicons/icons';

export default function Login() {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const schema = yup.object({
    email: yup.string().email().required(),
    password: yup.string().required(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
    resolver: yupResolver(schema),
  });

  const handleLogin = async (data: any) => {
    setLoading(true);

    await dispatch(loginUser(data))
      .unwrap()
      .then((res) => {
        setLoading(false);
        setShowToast(true); // Show success toast
        console.log('Res: ', res);
      })
      .catch((error) => {
        setLoading(false);
        console.log('Error: ', error);
      });

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
            src={`/assets/graphraglogo.png`}
          />

          <h5>Welcome, login!</h5>

          <form onSubmit={handleSubmit(handleLogin)} style={{ width: '100%' }}>
            <div className='custom-input-wrapper'>
              <input
                placeholder='Email'
                {...register('email')}
                className='custom-input'
              />
              <p className='custom-input-error'>{errors.email?.message}</p>
            </div>

            <div className='custom-input-wrapper'>
              <input
                placeholder='Password'
                type={showPassword ? 'text' : 'password'}
                {...register('password')}
                className='custom-input'
              />
              <IonIcon
                icon={showPassword ? eyeOffOutline : eyeOutline} // Toggle icon
                style={{
                  position: 'absolute',
                  right: 20,
                  top: 10,
                  cursor: 'pointer',
                  fontSize: '20px',
                }}
                onClick={() => setShowPassword(!showPassword)} // Toggle show/hide state
              />
              <p className='custom-input-error'>{errors.password?.message}</p>
            </div>

            <Link to='/forgot-password'>Forgot Password? </Link>

            <IonButton
              className='ion-margin-top ion-button-reset'
              type='submit'
              expand='full'
              shape='round'
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Login'}
            </IonButton>
          </form>

          <div>
            <p>
              New to FCS? <Link to='/register'>Create an account</Link>
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
