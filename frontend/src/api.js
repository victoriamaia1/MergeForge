import axios from "axios";
const BASE = import.meta.env.VITE_BACKEND_URL;
export const api = axios.create({ baseURL: BASE });
api.interceptors.request.use(cfg => {
  const t = localStorage.getItem("mf_token");
  if (t) cfg.headers.Authorization = "Bearer " + t;
  return cfg;
});
export const tokenStore = {
  get: () => localStorage.getItem("mf_token"),
  set: (t) => localStorage.setItem("mf_token", t),
  clear: () => localStorage.removeItem("mf_token"),
};
export const BACKEND_URL = BASE;
