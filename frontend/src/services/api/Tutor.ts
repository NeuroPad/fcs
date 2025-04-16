import client from "./client";


const getTutors = (token:any) => client.get("/tutors", {},{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});

const findTutor = (subject:any,token:any) => client.post("/tutors/subject", { subject },{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});


const bookTutor = (phone:any, password:any,token:any) => client.post("/leadersboard", { phone, password },{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});


export default {
    getTutors,findTutor,bookTutor
};
