import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { IonButton } from '@ionic/react';

export default function PinCode() {
  const [loading, setLoading] = useState(false);

  const schema = yup.object({
    pincode: yup.string().required(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      pincode: '',
    },
    resolver: yupResolver(schema),
  });

  const handlePincode = async (data: any) => {
    setLoading(false);
    console.log('PIN Code Data: ', data);
  };

  return (
    <div style={{ padding: '20px 20px' }}>
      <form onSubmit={handleSubmit(handlePincode)}>
        <div className='custom-input-wrapper'>
          <input
            placeholder='PIN Code'
            {...register('pincode')}
            className='custom-input'
          />
          <p className='custom-input-error'>{errors?.pincode?.message}</p>
        </div>

        <IonButton
          className='ion-margin-top ion-button-reset'
          type='submit'
          expand='full'
          shape='round'
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Proceed'}
        </IonButton>
      </form>
    </div>
  );
}
