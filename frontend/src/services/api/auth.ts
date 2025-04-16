import client from "./client";

const login = (phone:any, password:any) => client.post("/login", { phone, password });


const logout = (token:any) => client.post("/logout",{},{
  headers: {
      Authorization: `Bearer ${token}`,
 }
});

export default {
  login,logout
};
