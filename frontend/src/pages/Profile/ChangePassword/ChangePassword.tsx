import { IonButton, IonPage } from '@ionic/react';
import React, { useState } from 'react';
import Header from '../../../components/Header/Header';
import Container from '../../../components/Container/Container';

import * as yup from 'yup';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';

export default function ChangePassword() {
  const [loading, setLoading] = useState(false);

  const schema = yup.object({
    current_password: yup.string().required(),
    new_password: yup.string().required(),
    c_new_password: yup.string().required(),
  });

  const { register, handleSubmit } = useForm({
    defaultValues: {
      current_password: '',
      new_password: '',
      c_new_password: '',
    },
    resolver: yupResolver(schema),
  });

  const handleChangePassword = async (data: any) => {
    console.log('Data: ', data);
    setLoading(true);

    setTimeout(() => {
      setLoading(false);
    }, 1000);
  };

  return (
    <IonPage>
      <Header title='Account Profile' goBack />
      <Container>
        <form onSubmit={handleSubmit(handleChangePassword)}>
          <div className='custom-input-wrapper'>
            <input
              type='text'
              placeholder='Current password'
              className='custom-input'
              {...register('current_password')}
            />
          </div>

          <div className='custom-input-wrapper'>
            <input
              type='text'
              placeholder='New password'
              className='custom-input'
              {...register('new_password')}
            />
          </div>

          <div className='custom-input-wrapper'>
            <input
              type='text'
              placeholder='Confirm new password'
              className='custom-input'
              {...register('c_new_password')}
            />
          </div>

          <IonButton
            className='ion-margin-top ion-button-reset'
            type='submit'
            expand='full'
            shape='round'
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Change password'}
          </IonButton>
        </form>
      </Container>
    </IonPage>
  );
}
