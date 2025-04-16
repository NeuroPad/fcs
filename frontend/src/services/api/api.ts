import axios from 'axios';

const api = axios.create({
  baseURL: 'https://app.tevoapp.com/ai',
});


export const solveQuestion = async (image: any, question: string) => {
  try {
    const response = await api.post('/solve', { image, question });
    return response.data.solution;
  } catch (error) {
    console.error('Error solving question:', error);
    throw new Error('Failed to solve the question. Please try again.');
  }
};

export const getPastQuestions = async (question: string) => {
  try {
    const response = await api.get(`/similar/${question}`);
    console.log(response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching similar questions:', error);
    throw new Error('Failed to fetch similar questions. Please try again.');
  }
};