// src/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://fantasyfim.com/api', // Adjust this to your Flask API URL
});

export default api;
