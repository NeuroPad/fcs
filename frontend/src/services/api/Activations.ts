import client from './client';


const PaystackActivation = (token:any,ActivationInfo:any) => client.post("/activation",ActivationInfo ,{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});

const CodeActivation = (token:any,ActivationInfo:any) => client.post("/activation",ActivationInfo ,{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});

export default {
    PaystackActivation,CodeActivation
};
