import client from "./client";


const leaderboard = (token:any) => client.get("/leadersboard", {} ,{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});

const scores = (token:any,scoresInfo:any) => client.post("/scores", scoresInfo ,{
    headers: {
        Authorization: `Bearer ${token}`,
  }
});

export default {
    leaderboard,scores
};
