import { IonButton, IonPage } from '@ionic/react';
import React, { useState } from 'react';
import Header from '../../../components/Header/Header';
import Container from '../../../components/Container/Container';

import * as yup from 'yup';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { useAppSelector } from '../../../app/hooks';

export default function EditProfile() {
  const [loading, setLoading] = useState(false);
  const { user } = useAppSelector((state) => state.user);

  const schema = yup.object({
    name: yup.string().required(),
    phone_no: yup.string().required(),
  });

  const { register, handleSubmit } = useForm({
    defaultValues: {
      name: user?.name || '',
      phone_no: '',
    },
    resolver: yupResolver(schema),
  });

  const handleUpdateProfile = async (data: any) => {
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
        <form onSubmit={handleSubmit(handleUpdateProfile)}>
          <div className='custom-input-wrapper'>
            <input
              type='text'
              placeholder='Full Name'
              className='custom-input'
              {...register('name')}
            />
          </div>

          <div className='custom-input-wrapper'>
            <input
              type='email'
              placeholder='Phone Number'
              className='custom-input'
              value={user?.email}
              disabled
            />
          </div>

          <div className='custom-input-wrapper'>
            <input
              type='text'
              placeholder='Phone Number'
              className='custom-input'
              {...register('phone_no')}
            />
          </div>

          <IonButton
            className='ion-margin-top ion-button-reset'
            type='submit'
            expand='full'
            shape='round'
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Update'}
          </IonButton>
        </form>
      </Container>
    </IonPage>
  );
}
