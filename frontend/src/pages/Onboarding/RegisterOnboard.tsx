import React, { useState } from 'react';
import {
  IonPage, IonContent, IonButton, IonInput, IonIcon, IonLoading, IonImg
} from '@ionic/react';
import { useForm } from 'react-hook-form';
import { eyeOutline, eyeOffOutline, arrowForwardOutline, arrowBackOutline  } from 'ionicons/icons';
import { Swiper, SwiperSlide, useSwiper } from 'swiper/react';
import { Pagination } from 'swiper';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { useAppDispatch } from '../../app/hooks';
import { registerUser } from '../../features/authSlice';
import { useHistory } from 'react-router';
import 'swiper/css';
import 'swiper/css/pagination';
import './regonboarding.css';
import './animations.css';
import { Link } from 'react-router-dom';

// Define the option type with optional belief property
interface QuestionOption {
  text: string;
  score: number;
  belief?: string;
}

const questions = [
  {
    q: "🧠 You're reading two articles with totally different views. What's your instinct?",
    options: [
      { text: 'Pick the one that feels most right and move on', score: 0.2 },
      { text: 'Compare their facts and side with the stronger case', score: 0.4 },
      { text: 'Consider both valid until more is known', score: 0.6 },
      { text: 'See value in both, even if they conflict', score: 0.8 },
    ],
  },
  {
    q: '🧠 When someone changes their opinion frequently, how do you feel?',
    options: [
      { text: 'I find it unreliable', score: 0.2 },
      { text: 'I question their reasoning', score: 0.4 },
      { text: "I think they're learning", score: 0.6 },
      { text: 'I admire their flexibility', score: 0.8 },
    ],
  },
  {
    q: '🧠 Which statement sounds most like you?',
    options: [
      { text: "There's usually a right and wrong", score: 0.1 },
      { text: 'Truth is often in the middle', score: 0.4 },
      { text: 'It depends on the lens you use', score: 0.7 },
      { text: 'Truth shifts depending on who sees it', score: 0.9 },
    ],
  },
  {
    q: '🧠 When two people disagree passionately, you...',
    options: [
      { text: 'Want to calm things and find one answer', score: 0.2 },
      { text: 'Try to find common ground', score: 0.4 },
      { text: 'Let both express their truth freely', score: 0.6 },
      { text: 'Think the disagreement itself has value', score: 0.8 },
    ],
  },
  {
    q: '🧠 When someone challenges a belief you hold, what happens?',
    options: [
      { text: 'I feel it deeply and defend it', score: 0.2, belief: 'high' },
      { text: 'I feel a little shaken but open to change', score: 0.5, belief: 'moderate' },
      { text: 'I get curious and reconsider', score: 0.8, belief: 'low' },
    ],
  },
];

interface Profile {
  name: string;
  email: string;
  password: string;
  machine_name: string;
  contradiction_tolerance: number;
  belief_sensitivity: string;
}



const RegisterOnboard = () => {
  const [slideIndex, setSlideIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [beliefSensitivity, setBeliefSensitivity] = useState('');
  const [machineName, setMachineName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [swiperInstance, setSwiperInstance] = useState<any>(null);

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

  const { register, watch, formState: { errors }, handleSubmit } = useForm({
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirm_password: '',
    },
    resolver: yupResolver(schema)
  });

  const dispatch = useAppDispatch();
  const history = useHistory();

  const handleAnswer = async (score: number, belief?: string) => {
    setAnswers([...answers, score]);

    // If this option has a belief value, set it and submit
    if (belief) {
      // Set belief sensitivity immediately
      setBeliefSensitivity(belief);

      // Use the belief value directly in the profile calculation
      // rather than relying on the state update which might not be reflected immediately
      setLoading(true);
      try {
        const profile = {
          name: watch('name'),
          email: watch('email'),
          password: watch('password'),
          machine_name: machineName,
          contradiction_tolerance: parseFloat((answers.reduce((a, b) => a + b, 0) / answers.length).toFixed(2)),
          belief_sensitivity: belief,
        };

        const result = await dispatch(registerUser(profile)).unwrap();
        if (result) {
          history.push('/login');
        }
      } catch (error) {
        console.error('Registration failed:', error);
      } finally {
        setLoading(false);
      }
    } else {
      // Otherwise, advance to the next slide
      if (swiperInstance) {
        swiperInstance.slideNext();
      }
    }
  };

  // Keep the calculateProfile function for other uses if needed
  const calculateProfile = () => {
    const avgTolerance = answers.reduce((a, b) => a + b, 0) / answers.length;
    return {
      name: watch('name'),
      email: watch('email'),
      password: watch('password'),
      machine_name: machineName,
      contradiction_tolerance: parseFloat(avgTolerance.toFixed(2)),
      belief_sensitivity: beliefSensitivity,
    };
  };

  const handleContinue = () => {
    // Validate the form before proceeding
    handleSubmit(() => {
      if (swiperInstance) {
        swiperInstance.slideNext();
      }
    })();
  };

  const renderProgress = () => (
    <div className="question-progress">
      <span>Question {slideIndex - 1} of {questions.length}</span>
      <progress value={slideIndex - 1} max={questions.length}></progress>
    </div>
  );

  const NextButton = () => {
    const swiper = useSwiper();
    return (
      <IonButton
        
        onClick={() => swiper.slideNext()}
        fill="solid"
        color="primary"
        size="small" // Use Ionic's small button size
        disabled={slideIndex === 0 || slideIndex === questions.length + 1 || !answers[slideIndex - 1]}
      >
        <IonIcon icon={arrowForwardOutline} slot="end" /> Next
      </IonButton>
    );
  };

  const BackButton = () => {
    const swiper = useSwiper();
    return (
      <IonButton
       
        onClick={() => swiper.slidePrev()}
        fill="solid"
        color="primary"
        size="small" 
      >
        <IonIcon icon={arrowBackOutline} slot="start" /> Back
      </IonButton>
    );
  };

  const handleMachineNameContinue = () => {
    if (!machineName) {
      alert('Machine name is required');
      return;
    }
    if (swiperInstance) {
      swiperInstance.slideNext();
    }
  };

  return (

    <div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          maxWidth: '100%',
          width: '600px',
          justifyContent: 'center',
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
      </div>
      <Swiper
        onSwiper={(swiper) => setSwiperInstance(swiper)}
        onSlideChange={(swiper) => setSlideIndex(swiper.activeIndex)}
        // pagination={{ clickable: true }}
        modules={[Pagination]}
        allowTouchMove={false}
      >
        <SwiperSlide>
          <div className="slide-content fade-in">
            <h3 className="slide-title">Register</h3>
            <input className="styled-input" placeholder="Name" {...register('name')} />
            {errors.name && <p className="error-message">{errors.name.message}</p>}

            <input className="styled-input" placeholder="Email" type="email" {...register('email')} />
            {errors.email && <p className="error-message">{errors.email.message}</p>}

            <div className="password-wrapper">
              <input
                className="styled-input"
                placeholder="Password"
                type={showPassword ? 'text' : 'password'}
                {...register('password')}
              />
              <IonIcon
                icon={showPassword ? eyeOffOutline : eyeOutline}
                className="eye-icon"
                onClick={() => setShowPassword(!showPassword)}
              />
            </div>
            {errors.password && <p className="error-message">{errors.password.message}</p>}

            <div className="password-wrapper">
              <input
                className="styled-input"
                placeholder="Confirm Password"
                type={showConfirmPassword ? 'text' : 'password'}
                {...register('confirm_password')}
              />
              <IonIcon
                icon={showConfirmPassword ? eyeOffOutline : eyeOutline}
                className="eye-icon"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              />
            </div>
            {errors.confirm_password && <p className="error-message">{errors.confirm_password.message}</p>}

            <IonButton
              expand="block"
              className="ion-button-primary"
              onClick={handleContinue}
            >
              Continue
            </IonButton>
            <p style={{ marginTop: 20 }}>
              Already have an account? <Link to='/login'>Login</Link>
            </p>
          </div>
        </SwiperSlide>

        <SwiperSlide>
          <div className="slide-content fade-in">
            <h3 className="slide-title">Hello {watch('name')},</h3>
            <div className="subtitle-container">
              <p className="subtitle">
                I'm here to grow with you—understanding how you think and what matters most to you.
              </p>
              <p className="subtitle">
                Let's begin by getting a feel for your unique way of thinking.
              </p>
              <p className="subtitle">
                Before we begin, give me a name I'll carry it with me as we grow <span role="img" aria-label="brain">🧠</span> together
              </p>
            </div>
            <IonInput
              value={machineName}
              className={`styled-input ${!machineName ? 'input-error' : ''}`} // Add error class
              onIonChange={(e) => setMachineName(String(e.detail.value || ''))}
              placeholder="Name me..."
            />
            <IonButton
              expand="block"
              className="ion-button-primary"
              onClick={handleMachineNameContinue}
            >
              Next
            </IonButton>
          </div>
        </SwiperSlide>

        {questions.map((question, qIndex) => (
          <SwiperSlide key={`question-${qIndex}`}>
            <div className="slide-content fade-in">
              {renderProgress()}
              <h4 className="question-text">{question.q}</h4>
              <div className="card-options">
                {question.options.map((opt: QuestionOption, idx) => (
                  <div
                    key={idx}
                    className={`answer-card ${answers[slideIndex - 1] === opt.score ? 'selected' : ''}`}
                    onClick={() => handleAnswer(opt.score, opt.belief)}
                  >
                    {opt.text}
                  </div>
                ))}
              </div>
              <div className="navigation-buttons">
                <BackButton />
                <NextButton />
              </div>
            </div>
          </SwiperSlide>
        ))}


      </Swiper>
      <IonLoading isOpen={loading} message="Finalizing your profile..." />
    </div>

  );
};

// Add CSS for selected state and button styling
// .answer-card.selected { background-color: #e0e0e0; }
// .navigation-buttons { display: flex; justify-content: space-between; }
// .input-error { border-color: red; }
export default RegisterOnboard;
