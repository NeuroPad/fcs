import { create } from 'apisauce';

// define the api
const apiClient = create({
  baseURL: 'https://skygemsacademy.net/api/v1',
});

export default apiClient;