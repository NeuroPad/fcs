import client from "./client";

const register = (userInfo:any) => client.post("/register", userInfo);

export default { register };
