import React, { useState } from 'react';
import { IonButton, IonIcon, IonImg, IonPage } from '@ionic/react';
import { useAppDispatch } from '../../../app/hooks';
import { registerUser } from '../../../features/authSlice';
import { useForm } from 'react-hook-form';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { Link, useHistory } from 'react-router-dom';
import Container from '../../../components/Container/Container';
import { eyeOffOutline, eyeOutline } from 'ionicons/icons';
import RegisterOnboard  from '../../Onboarding/RegisterOnboard';

export default function Register() {
  const history = useHistory();
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');

  const schema = yup.object({
    name: yup.string().required('Name is required'),
    email: yup
      .string()
      .email('Invalid email format')
      .required('Email is required'),
    password: yup
      .string()
      .required('Password is required')
      .min(6, 'Password must be at least 6 characters long'),
    confirm_password: yup
      .string()
      .oneOf([yup.ref('password')], 'Passwords must match')
      .required('Confirm Password is required'),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirm_password: '',
    },
    resolver: yupResolver(schema),
  });

  // Removed handleRegister as it's handled by RegisterOnboard



  const handleComplete = async (profile: {
    name: string;
    email: string;
    password: string;
    machine_name: string;
    contradiction_tolerance: number;
    belief_sensitivity: string;
  }) => {
    try {
      await dispatch(registerUser(profile)).unwrap();
      history.push('/dashboard');
    } catch (error) {
      setError(error as string);
    }
  };
  return (
    // <IonPage>
    //   <Container width='100%' padding={false}>
    //     <div
    //       style={{
    //         display: 'flex',
    //         flexDirection: 'column',
    //         alignItems: 'center',
    //         maxWidth: '100%',
    //         width: '600px',
    //         justifyContent: 'center',
    //         height: 'calc(100vh -  40px)',
    //         margin: '0 auto',
    //         padding: '0 20px',
    //       }}
    //     >
    //       <IonImg
    //         style={{
    //           width: 100,
    //           marginBottom: 20,
    //         }}
    //         src={`/assets/graphraglogo.png`}
    //       />

    //       <h5>Create your account!</h5>
    //       {error && <p style={{ color: 'red' }}>{error}</p>}
    //       <form
    //         onSubmit={handleSubmit(handleRegister)}
    //         style={{ width: '100%' }}
    //       >
    //         <div className='custom-input-wrapper'>
    //           <input
    //             placeholder='Full name'
    //             {...register('name')}
    //             className='custom-input'
    //           />
    //           <p className='custom-input-error'>{errors.name?.message}</p>
    //         </div>
    //         <div className='custom-input-wrapper'>
    //           <input
    //             placeholder='Email'
    //             {...register('email')}
    //             className='custom-input'
    //           />
    //           <p className='custom-input-error'>{errors.email?.message}</p>
    //         </div>
    //         <div className='custom-input-wrapper'>
    //           <input
    //             placeholder='Password'
    //             type={showPassword ? 'text' : 'password'}
    //             {...register('password')}
    //             className='custom-input'
    //           />
    //           <IonIcon
    //             icon={showPassword ? eyeOffOutline : eyeOutline}
    //             style={{ position: 'absolute', right: 20, top: 18, cursor: 'pointer' }}
    //             onClick={() => setShowPassword((v) => !v)}
    //           />
    //           <p className='custom-input-error'>{errors.password?.message}</p>
    //         </div>
    //         <div className='custom-input-wrapper'>
    //           <input
    //             placeholder='Confirm Password'
    //             type={showConfirmPassword ? 'text' : 'password'}
    //             {...register('confirm_password')}
    //             className='custom-input'
    //           />
    //           <IonIcon
    //             icon={showConfirmPassword ? eyeOffOutline : eyeOutline}
    //             style={{ position: 'absolute', right: 20, top: 18, cursor: 'pointer' }}
    //             onClick={() => setShowConfirmPassword((v) => !v)}
    //           />
    //           <p className='custom-input-error'>{errors.confirm_password?.message}</p>
    //         </div>
    //         <IonButton
    //           expand='block'
    //           type='submit'
    //           disabled={loading}
    //           style={{ marginTop: 20 }}
    //         >
    //           {loading ? 'Registering...' : 'Register'}
    //         </IonButton>
    //       </form>
    //       <p style={{ marginTop: 20 }}>
    //         Already have an account? <Link to='/login'>Login</Link>
    //       </p>
    //     </div>
    //   </Container>
    // </IonPage>
    <Container width='100%'>
      <RegisterOnboard  />
    </Container>
    
  );
}
